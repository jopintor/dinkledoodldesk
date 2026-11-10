from pathlib import Path

import pytest

from app.rag.kb import (
    KBValidationError,
    chunk_document,
    estimate_tokens,
    load_knowledge_base,
    parse_document,
)

FRONT = """---
id: KB-900
title: Test Doc
category: network
audience_roles: [staff, admin]
last_updated: 2026-01-01
owner: IT
---
"""


def write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_real_knowledge_base_parses_and_chunks(settings):
    docs, errors = load_knowledge_base(settings.kb_dir)
    assert errors == []
    assert len(docs) == 28
    for doc in docs:
        chunks = chunk_document(doc)
        assert chunks, doc.doc_id
        assert all(c.chunk_id.startswith(f"{doc.doc_id}-c") for c in chunks)
        assert all(estimate_tokens(c.text) >= 60 for c in chunks), doc.doc_id


def test_kb014_is_superseded_and_agent_admin_only(settings):
    docs, _ = load_knowledge_base(settings.kb_dir)
    kb014 = next(d for d in docs if d.doc_id == "KB-014")
    assert not kb014.is_current
    assert kb014.superseded_by == "KB-013"
    chunk = chunk_document(kb014)[0]
    meta = chunk.metadata()
    assert meta["is_current"] is False
    assert (meta["role_member"], meta["role_staff"], meta["role_agent"]) == (False, False, True)


def test_chunk_ids_and_header_are_stable(tmp_path):
    body = "# Test Doc\n\n## Section A\n\n" + "word " * 100 + "\n\n## Section B\n\n" + "x " * 200
    doc = parse_document(write(tmp_path, "kb-900.md", FRONT + body))
    first, second = chunk_document(doc), chunk_document(doc)
    assert [c.chunk_id for c in first] == ["KB-900-c01", "KB-900-c02"]
    assert first == second
    assert first[0].header == "KB-900 · Test Doc › Section A"
    assert first[0].embed_text.startswith("KB-900 · Test Doc › Section A\n")


def test_small_sections_merge_with_the_next(tmp_path):
    body = "# T\n\n## Tiny\n\nShort.\n\n## Big\n\n" + "word " * 120
    doc = parse_document(write(tmp_path, "kb-900.md", FRONT + body))
    chunks = chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].section == "Tiny + Big"
    assert "Short." in chunks[0].text and "Big\nword" in chunks[0].text


def test_nested_headings_build_a_path_and_fenced_hashes_are_ignored(tmp_path):
    body = "# T\n\n## Parent\n\n### Child\n\n" + "word " * 80 + "\n\n```\n## not a heading\n```\n"
    doc = parse_document(write(tmp_path, "kb-900.md", FRONT + body))
    chunks = chunk_document(doc)
    assert [c.section for c in chunks] == ["Parent › Child"]
    assert "## not a heading" in chunks[0].text


def test_oversized_section_splits_between_paragraphs_never_inside_a_table(tmp_path):
    table = "| col a | col b |\n|---|---|\n" + "".join(
        f"| row {i} | value {i} |\n" for i in range(60)
    )
    paragraphs = "\n\n".join("para " * 60 for _ in range(4))
    body = f"# T\n\n## Long\n\n{paragraphs}\n\n{table}"
    doc = parse_document(write(tmp_path, "kb-900.md", FRONT + body))
    chunks = chunk_document(doc)
    assert len(chunks) > 1
    assert all("(part " in c.section for c in chunks)
    with_table = [c for c in chunks if "| row 0 |" in c.text]
    assert len(with_table) == 1 and "| row 59 |" in with_table[0].text


@pytest.mark.parametrize(
    ("front", "message"),
    [
        ("---\nid: KB-900\n---\n", "missing front matter fields"),
        (FRONT.replace("KB-900", "DOC-1"), "does not look like"),
        (FRONT.replace("[staff, admin]", "[staff, guest]"), "audience_roles"),
        (FRONT.replace("owner: IT", "owner: IT\nstatus: superseded"), "superseded_by"),
        ("no front matter at all\n", "missing YAML front matter"),
    ],
)
def test_invalid_front_matter_is_rejected(tmp_path, front, message):
    with pytest.raises(KBValidationError, match=message):
        parse_document(write(tmp_path, "kb-900.md", front + "# T\n\nbody\n"))


def test_invalid_and_duplicate_files_are_reported_not_fatal(tmp_path):
    write(tmp_path, "kb-900-a.md", FRONT + "# T\n\nbody\n")
    write(tmp_path, "kb-900-b.md", FRONT + "# T\n\nbody\n")
    write(tmp_path, "kb-901.md", "no front matter\n")
    write(tmp_path, "README.md", "ignored\n")
    docs, errors = load_knowledge_base(tmp_path)
    assert [d.doc_id for d in docs] == ["KB-900"]
    assert len(errors) == 2
    assert any("duplicate id KB-900" in e for e in errors)
