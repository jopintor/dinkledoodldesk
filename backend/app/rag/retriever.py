"""Hybrid retrieval with role filtering and a confidence score (docs/ai-design.md §3).

Vector top 10 (Chroma, cosine) + BM25 top 10, both filtered by the caller's role, fused
with Reciprocal Rank Fusion. Superseded documents (KB-014) are down-ranked. The BM25 index
is built in memory from the Chroma collection and refreshed when the collection changes.
"""

import hashlib
import logging
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from rank_bm25 import BM25Okapi

from app.config import Settings
from app.rag.kb import ROLES, Chunk, estimate_tokens
from app.rag.store import KBStore

log = logging.getLogger(__name__)

Mode = Literal["hybrid", "vector", "bm25"]
Band = Literal["high", "medium", "low"]

CANDIDATES = 10
RRF_K = 60
SUPERSEDED_FACTOR = 0.5
CONTEXT_CHUNKS = 5
MAX_PER_DOC = 2
CONTEXT_TOKEN_BUDGET = 2000
AGREE_TOP_N = 5
# Without a query vector (embedding quota hit, Chroma down) we can't measure similarity,
# so BM25-only results land in the medium band: answer carefully, offer a ticket.
BM25_ONLY_CONFIDENCE = 0.5
REFRESH_S = 60.0

# Keeps kb-003, 0x51, picklehub-staff and 6-digit codes as single tokens.
_TOKEN = re.compile(r"[a-z0-9]+(?:[-_./][a-z0-9]+)*")
_TOKEN_PARTS = re.compile(r"[-_./]")
_ALIASES = {"wifi": "wi-fi", "e-mail": "email", "login": "log", "signin": "sign"}
_STOPWORDS = frozenset(
    "a an and are as at be but by can do does for from how i if in is it its me my of on "
    "or our so the their them then there this to was we what when where which who why "
    "will with you your".split()
)


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for token in _TOKEN.findall(text.lower()):
        token = _ALIASES.get(token, token)
        if token in _STOPWORDS:
            continue
        tokens.append(token)
        if _TOKEN_PARTS.search(token):
            tokens.extend(p for p in _TOKEN_PARTS.split(token) if p and p not in _STOPWORDS)
    return tokens


@dataclass
class ScoredChunk:
    chunk: Chunk
    rrf_score: float = 0.0
    vector_score: float | None = None
    bm25_score: float | None = None

    @property
    def context_header(self) -> str:
        if self.chunk.is_current:
            return self.chunk.header
        return f"[SUPERSEDED — replaced by {self.chunk.superseded_by}] {self.chunk.header}"


@dataclass
class RetrievalResult:
    chunks: list[ScoredChunk]
    retrieval_confidence: float
    band: Band
    vector_ok: bool
    agree: bool
    best_cosine: float
    vector_ids: list[str] = field(default_factory=list)
    bm25_ids: list[str] = field(default_factory=list)

    @property
    def doc_ids(self) -> list[str]:
        """Document ids in rank order, without duplicates."""
        return list(dict.fromkeys(c.chunk.doc_id for c in self.chunks))


def band_for(confidence: float, settings: Settings) -> Band:
    if confidence >= settings.rag_high_threshold:
        return "high"
    if confidence >= settings.rag_medium_threshold:
        return "medium"
    return "low"


def retrieval_confidence(best_cosine: float, agree: bool, settings: Settings) -> float:
    """0.8 × cosine scaled from [floor, ceiling] to [0, 1] + 0.2 × agreement."""
    lo, hi = settings.rag_cosine_floor, settings.rag_cosine_ceiling
    scaled = min(1.0, max(0.0, (best_cosine - lo) / (hi - lo)))
    return round(0.8 * scaled + 0.2 * (1.0 if agree else 0.0), 4)


class Retriever:
    def __init__(
        self,
        store: KBStore,
        embed_query: Callable[[str], list[float]],
        settings: Settings,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._store = store
        self._embed_query = embed_query
        self._settings = settings
        self._clock = clock
        self._lock = threading.Lock()
        self._loaded_at: float | None = None
        self._chunks: dict[str, Chunk] = {}
        self._bm25: dict[str, tuple[BM25Okapi, list[str]] | None] = {}
        self._kb_version = "empty"

    @property
    def kb_version(self) -> str:
        """Changes whenever any indexed document changes; part of the response-cache key."""
        self._ensure_loaded()
        return self._kb_version

    @property
    def chunk_count(self) -> int:
        self._ensure_loaded()
        return len(self._chunks)

    def refresh(self) -> None:
        """Rebuild the BM25 index from Chroma (call after a re-index)."""
        chunks = self._store.all_chunks()
        by_id = {c.chunk_id: c for c in chunks}
        bm25: dict[str, tuple[BM25Okapi, list[str]] | None] = {}
        for role in ROLES:
            ids = sorted(cid for cid, c in by_id.items() if role in c.roles)
            corpus = [tokenize(by_id[cid].embed_text) for cid in ids]
            bm25[role] = (BM25Okapi(corpus), ids) if ids else None
        hashes = sorted({f"{c.doc_id}:{c.content_hash}" for c in chunks})
        version = hashlib.sha256("\n".join(hashes).encode()).hexdigest()[:12] if hashes else "empty"
        with self._lock:
            self._chunks, self._bm25, self._kb_version = by_id, bm25, version
            self._loaded_at = self._clock()

    def _ensure_loaded(self) -> None:
        if self._loaded_at is not None and self._clock() - self._loaded_at < REFRESH_S:
            return
        try:
            self.refresh()
        except Exception:
            if self._loaded_at is None:
                log.exception("could not load the knowledge base from Chroma")
            else:
                log.warning("Chroma unavailable; keeping the previous BM25 index", exc_info=True)
            self._loaded_at = self._clock()  # don't hammer a down Chroma on every request

    def _bm25_search(self, query: str, role: str) -> list[tuple[Chunk, float]]:
        index = self._bm25.get(role)
        terms = tokenize(query)
        if index is None or not terms:
            return []
        bm25, ids = index
        scores = bm25.get_scores(terms)
        ranked = sorted(
            (pair for pair in zip(ids, scores, strict=True) if pair[1] > 0),
            key=lambda pair: pair[1],
            reverse=True,
        )
        return [(self._chunks[cid], float(score)) for cid, score in ranked[:CANDIDATES]]

    def search(self, query: str, role: str, *, mode: Mode = "hybrid") -> RetrievalResult:
        if role not in ROLES:
            raise ValueError(f"unknown role {role!r}")
        self._ensure_loaded()
        s = self._settings

        vector_hits = []
        vector_ok = mode != "bm25"
        if vector_ok:
            try:
                vector_hits = self._store.query(self._embed_query(query), role, CANDIDATES)
            except Exception:
                log.warning("vector search failed; falling back to BM25 only", exc_info=True)
                vector_ok = False
        bm25_hits = self._bm25_search(query, role) if mode != "vector" else []

        scored: dict[str, ScoredChunk] = {}
        for rank, hit in enumerate(vector_hits, start=1):
            item = scored.setdefault(hit.chunk.chunk_id, ScoredChunk(hit.chunk))
            item.vector_score = round(hit.similarity, 4)
            item.rrf_score += 1 / (RRF_K + rank)
        for rank, (chunk, score) in enumerate(bm25_hits, start=1):
            item = scored.setdefault(chunk.chunk_id, ScoredChunk(chunk))
            item.bm25_score = round(score, 3)
            item.rrf_score += 1 / (RRF_K + rank)
        for item in scored.values():
            if not item.chunk.is_current:
                item.rrf_score *= SUPERSEDED_FACTOR
            item.rrf_score = round(item.rrf_score, 5)

        packed: list[ScoredChunk] = []
        per_doc: dict[str, int] = {}
        tokens = 0
        for item in sorted(scored.values(), key=lambda i: i.rrf_score, reverse=True):
            if len(packed) == CONTEXT_CHUNKS:
                break
            doc = item.chunk.doc_id
            cost = estimate_tokens(item.chunk.embed_text)
            if per_doc.get(doc, 0) >= MAX_PER_DOC or (
                packed and tokens + cost > CONTEXT_TOKEN_BUDGET
            ):
                continue
            packed.append(item)
            per_doc[doc] = per_doc.get(doc, 0) + 1
            tokens += cost

        vector_ids = [h.chunk.chunk_id for h in vector_hits]
        bm25_ids = [c.chunk_id for c, _ in bm25_hits]
        agree = bool(packed) and (
            packed[0].chunk.chunk_id in vector_ids[:AGREE_TOP_N]
            and packed[0].chunk.chunk_id in bm25_ids[:AGREE_TOP_N]
        )
        best_cosine = max(
            (i.vector_score for i in packed if i.vector_score is not None), default=0.0
        )
        if not packed:
            confidence = 0.0
        elif vector_ok:
            confidence = retrieval_confidence(best_cosine, agree, s)
        else:
            confidence = BM25_ONLY_CONFIDENCE
        return RetrievalResult(
            chunks=packed,
            retrieval_confidence=confidence,
            band=band_for(confidence, s),
            vector_ok=vector_ok,
            agree=agree,
            best_cosine=best_cosine,
            vector_ids=vector_ids,
            bm25_ids=bm25_ids,
        )
