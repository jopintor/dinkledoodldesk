"""Knowledge-base parsing and chunking (docs/ai-design.md §2).

Pure functions, no I/O beyond reading the Markdown files, so they are easy to test.
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from langchain_text_splitters import RecursiveCharacterTextSplitter

ROLES = ("member", "staff", "agent", "admin")
REQUIRED_FIELDS = ("id", "title", "category", "audience_roles", "last_updated", "owner")
# Bump when the chunking rules change so the next ingestion re-embeds every document.
CHUNKER_VERSION = "1"

MAX_CHUNK_TOKENS = 450
MIN_CHUNK_TOKENS = 60
SPLIT_CHUNK_CHARS = 1600
SPLIT_OVERLAP_CHARS = 200

_FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_DOC_ID = re.compile(r"^KB-\d{3}$")
_HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")


class KBValidationError(ValueError):
    pass


def estimate_tokens(text: str) -> int:
    """Rough token count (≈ 4 characters per token); good enough for size rules."""
    return len(text) // 4


@dataclass(frozen=True)
class KBDocument:
    doc_id: str
    title: str
    category: str
    audience_roles: tuple[str, ...]
    last_updated: str
    owner: str
    status: str
    superseded_by: str
    body: str
    content_hash: str
    path: str

    @property
    def is_current(self) -> bool:
        return self.status != "superseded"


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    section: str
    text: str
    category: str
    roles: tuple[str, ...]
    is_current: bool = True
    superseded_by: str = ""
    content_hash: str = ""

    @property
    def header(self) -> str:
        return f"{self.doc_id} · {self.title} › {self.section}"

    @property
    def embed_text(self) -> str:
        """What gets embedded and indexed: contextual header + section text."""
        return f"{self.header}\n{self.text}"

    def metadata(self) -> dict:
        meta = {
            "doc_id": self.doc_id,
            "title": self.title,
            "section_path": self.section,
            "category": self.category,
            "is_current": self.is_current,
            "superseded_by": self.superseded_by,
            "content_hash": self.content_hash,
        }
        meta.update({f"role_{role}": role in self.roles for role in ROLES})
        return meta

    @classmethod
    def from_record(cls, chunk_id: str, text: str, meta: dict) -> "Chunk":
        return cls(
            chunk_id=chunk_id,
            doc_id=meta["doc_id"],
            title=meta["title"],
            section=meta["section_path"],
            text=text,
            category=meta.get("category", ""),
            roles=tuple(r for r in ROLES if meta.get(f"role_{r}")),
            is_current=bool(meta.get("is_current", True)),
            superseded_by=meta.get("superseded_by", ""),
            content_hash=meta.get("content_hash", ""),
        )


def parse_document(path: Path) -> KBDocument:
    raw = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    match = _FRONT_MATTER.match(raw)
    if match is None:
        raise KBValidationError("missing YAML front matter")
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise KBValidationError(f"invalid YAML front matter: {exc}") from exc
    if not isinstance(meta, dict):
        raise KBValidationError("front matter is not a mapping")

    missing = [f for f in REQUIRED_FIELDS if not meta.get(f)]
    if missing:
        raise KBValidationError(f"missing front matter fields: {', '.join(missing)}")
    doc_id = str(meta["id"])
    if not _DOC_ID.match(doc_id):
        raise KBValidationError(f"id {doc_id!r} does not look like KB-000")
    roles = meta["audience_roles"]
    if not isinstance(roles, list) or not roles or not set(roles) <= set(ROLES):
        raise KBValidationError(f"audience_roles must be a non-empty subset of {ROLES}")
    status = str(meta.get("status") or "current")
    if status not in ("current", "superseded"):
        raise KBValidationError(f"unknown status {status!r}")
    superseded_by = str(meta.get("superseded_by") or "")
    if status == "superseded" and not _DOC_ID.match(superseded_by):
        raise KBValidationError("a superseded document needs superseded_by: KB-xxx")

    digest = hashlib.sha256(f"{CHUNKER_VERSION}\n{raw}".encode()).hexdigest()
    return KBDocument(
        doc_id=doc_id,
        title=str(meta["title"]),
        category=str(meta["category"]),
        audience_roles=tuple(r for r in ROLES if r in roles),
        last_updated=str(meta["last_updated"]),
        owner=str(meta["owner"]),
        status=status,
        superseded_by=superseded_by,
        body=raw[match.end() :],
        content_hash=digest,
        path=str(path),
    )


def load_knowledge_base(kb_dir: Path) -> tuple[list[KBDocument], list[str]]:
    """Parse every `kb-*.md` file. Invalid files are skipped and reported, not fatal."""
    docs: list[KBDocument] = []
    errors: list[str] = []
    seen: dict[str, str] = {}
    for path in sorted(Path(kb_dir).glob("kb-*.md")):
        try:
            doc = parse_document(path)
        except (KBValidationError, OSError, UnicodeDecodeError) as exc:
            errors.append(f"{path.name}: {exc}")
            continue
        if doc.doc_id in seen:
            errors.append(f"{path.name}: duplicate id {doc.doc_id} (also in {seen[doc.doc_id]})")
            continue
        seen[doc.doc_id] = path.name
        docs.append(doc)
    return docs, errors


@dataclass
class _Section:
    path: str
    name: str
    text: str


def _split_sections(body: str) -> list[_Section]:
    """Split on #, ## and ### headings, ignoring headings inside code fences.

    LangChain's MarkdownHeaderTextSplitter is not used because it drops blank lines and
    indentation, which would merge paragraphs and break tables and numbered procedures.
    """
    sections: list[_Section] = []
    stack: list[str] = []  # heading names for levels 2 and 3
    current_lines: list[str] = []
    current_path, current_name = "Overview", "Overview"
    in_fence = False

    def flush() -> None:
        text = "\n".join(current_lines).strip()
        if text:
            sections.append(_Section(current_path, current_name, text))
        current_lines.clear()

    for line in body.split("\n"):
        if _FENCE.match(line):
            in_fence = not in_fence
        heading = None if in_fence else _HEADING.match(line)
        if heading is None:
            current_lines.append(line)
            continue
        flush()
        level, name = len(heading.group(1)), heading.group(2).strip()
        if level == 1:
            stack = []
            current_path, current_name = "Overview", "Overview"
            continue
        stack = stack[: level - 2] + [name]
        current_path, current_name = " › ".join(stack), name
    flush()
    return sections


def _combine(first: _Section, second: _Section) -> _Section:
    return _Section(
        path=f"{first.path} + {second.path}",
        name=first.name,
        text=f"{first.text}\n\n{second.name}\n{second.text}",
    )


def chunk_document(doc: KBDocument) -> list[Chunk]:
    """One chunk per section; merge sections under 60 tokens, split those over 450."""
    merged: list[_Section] = []
    pending: _Section | None = None
    for section in _split_sections(doc.body):
        if pending is not None:
            section, pending = _combine(pending, section), None
        if estimate_tokens(section.text) < MIN_CHUNK_TOKENS:
            pending = section
            continue
        merged.append(section)
    if pending is not None:
        if merged:
            merged[-1] = _combine(merged[-1], pending)
        else:
            merged.append(pending)

    # Only blank-line separators: a table or a list without blank lines is never cut.
    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n"],
        chunk_size=SPLIT_CHUNK_CHARS,
        chunk_overlap=SPLIT_OVERLAP_CHARS,
    )
    pieces: list[tuple[str, str]] = []
    for section in merged:
        if estimate_tokens(section.text) <= MAX_CHUNK_TOKENS:
            pieces.append((section.path, section.text))
            continue
        parts = splitter.split_text(section.text)
        for i, part in enumerate(parts, start=1):
            pieces.append((f"{section.path} (part {i}/{len(parts)})", part))

    return [
        Chunk(
            chunk_id=f"{doc.doc_id}-c{i:02d}",
            doc_id=doc.doc_id,
            title=doc.title,
            section=path,
            text=text,
            category=doc.category,
            roles=doc.audience_roles,
            is_current=doc.is_current,
            superseded_by=doc.superseded_by,
            content_hash=doc.content_hash,
        )
        for i, (path, text) in enumerate(pieces, start=1)
    ]
