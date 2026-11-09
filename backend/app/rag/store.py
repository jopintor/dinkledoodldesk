"""ChromaDB access: one collection per embedding model and dimension (docs/ai-design.md §2)."""

import re
from dataclasses import dataclass

from app.config import Settings
from app.rag.kb import Chunk


def collection_name(settings: Settings, embedding_model: str) -> str:
    """`picklehub-kb__gemini-embedding-001__768`: a model or dimension change is a new index."""
    model = re.sub(r"[^A-Za-z0-9._-]+", "-", embedding_model.split("/")[-1]).strip("-.")
    return f"{settings.chroma_collection}__{model}__{settings.embedding_dim}"


def make_client(settings: Settings):
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    chroma_settings = ChromaSettings(anonymized_telemetry=False)
    if settings.chroma_mode == "persistent":
        return chromadb.PersistentClient(path=settings.chroma_persist_dir, settings=chroma_settings)
    if settings.chroma_mode == "ephemeral":
        return chromadb.EphemeralClient(settings=chroma_settings)
    return chromadb.HttpClient(
        host=settings.chroma_host, port=settings.chroma_port, settings=chroma_settings
    )


@dataclass(frozen=True)
class VectorHit:
    chunk: Chunk
    similarity: float


class KBStore:
    """`client` is a Chroma client or a zero-argument factory for one.

    With a factory, nothing connects until first use, so the API starts (and degrades to
    "knowledge base unavailable") even when the Chroma server is down.
    """

    def __init__(self, client, name: str) -> None:
        self.name = name
        self._client = client
        self._col = None

    @property
    def _collection(self):
        if self._col is None:
            client = self._client() if callable(self._client) else self._client
            self._col = client.get_or_create_collection(
                self.name,
                configuration={"hnsw": {"space": "cosine"}},
                embedding_function=None,  # we always pass our own vectors
            )
        return self._col

    def doc_hashes(self) -> dict[str, str]:
        """doc_id -> content_hash of what is indexed now."""
        result = self._collection.get(include=["metadatas"])
        return {m["doc_id"]: m.get("content_hash", "") for m in result["metadatas"]}

    def chunk_ids(self, doc_id: str | None = None) -> set[str]:
        where = {"doc_id": doc_id} if doc_id else None
        return set(self._collection.get(where=where, include=[])["ids"])

    def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        self._collection.upsert(
            ids=[c.chunk_id for c in chunks],
            embeddings=embeddings,
            documents=[c.text for c in chunks],
            metadatas=[c.metadata() for c in chunks],
        )

    def delete(self, ids: list[str]) -> None:
        if ids:
            self._collection.delete(ids=ids)

    def all_chunks(self) -> list[Chunk]:
        result = self._collection.get(include=["documents", "metadatas"])
        return [
            Chunk.from_record(cid, text, meta)
            for cid, text, meta in zip(
                result["ids"], result["documents"], result["metadatas"], strict=True
            )
        ]

    def query(self, embedding: list[float], role: str, n: int) -> list[VectorHit]:
        if self._collection.count() == 0:
            return []
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=n,
            where={f"role_{role}": True},
            include=["documents", "metadatas", "distances"],
        )
        return [
            VectorHit(Chunk.from_record(cid, text, meta), 1.0 - dist)
            for cid, text, meta, dist in zip(
                result["ids"][0],
                result["documents"][0],
                result["metadatas"][0],
                result["distances"][0],
                strict=True,
            )
        ]
