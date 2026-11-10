"""Knowledge-base ingestion: Markdown -> chunks -> embeddings -> Chroma.

Re-runnable. A document whose content hash is unchanged is skipped; a changed document's
new chunks are written before its stale ones are deleted, so it is never missing from the
index. Documents deleted from `/knowledge-base` are pruned, but only when every file
parsed, so a typo in one file can't wipe part of the index.

Run from `backend/`:  python -m app.rag.ingest [--full]
"""

import argparse
import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from app.rag.kb import chunk_document, load_knowledge_base
from app.rag.store import KBStore

log = logging.getLogger(__name__)

EMBED_BATCH = 100  # Gemini batch limit


@dataclass
class IngestReport:
    collection: str
    docs_total: int = 0
    docs_indexed: int = 0
    docs_unchanged: int = 0
    docs_removed: int = 0
    chunks_embedded: int = 0
    chunks_deleted: int = 0
    errors: list[str] = field(default_factory=list)
    aborted: str = ""

    @property
    def ok(self) -> bool:
        return not self.errors and not self.aborted

    def summary(self) -> str:
        lines = [
            f"collection        {self.collection}",
            f"documents         {self.docs_total} valid, {self.docs_indexed} indexed, "
            f"{self.docs_unchanged} unchanged, {self.docs_removed} removed",
            f"chunks            {self.chunks_embedded} embedded, {self.chunks_deleted} deleted",
        ]
        lines += [f"skipped           {e}" for e in self.errors]
        if self.aborted:
            lines.append(f"ABORTED           {self.aborted} (re-run to continue)")
        return "\n".join(lines)


def ingest_knowledge_base(
    kb_dir: Path,
    store: KBStore,
    embed_documents: Callable[[list[str]], list[list[float]]],
    *,
    full: bool = False,
) -> IngestReport:
    report = IngestReport(collection=store.name)
    docs, report.errors = load_knowledge_base(kb_dir)
    report.docs_total = len(docs)
    indexed = store.doc_hashes()

    for doc in docs:
        if not full and indexed.get(doc.doc_id) == doc.content_hash:
            report.docs_unchanged += 1
            continue
        chunks = chunk_document(doc)
        try:
            vectors: list[list[float]] = []
            for start in range(0, len(chunks), EMBED_BATCH):
                batch = chunks[start : start + EMBED_BATCH]
                vectors += embed_documents([c.embed_text for c in batch])
        except Exception as exc:  # quota or network: keep what is done, re-run continues
            report.aborted = f"embedding {doc.doc_id} failed: {exc}"
            log.error(report.aborted)
            return report
        old_ids = store.chunk_ids(doc.doc_id)
        store.upsert(chunks, vectors)
        stale = sorted(old_ids - {c.chunk_id for c in chunks})
        store.delete(stale)
        report.docs_indexed += 1
        report.chunks_embedded += len(chunks)
        report.chunks_deleted += len(stale)
        log.info("indexed %s: %d chunks", doc.doc_id, len(chunks))

    if not report.errors:
        valid = {d.doc_id for d in docs}
        for doc_id in sorted(set(indexed) - valid):
            ids = sorted(store.chunk_ids(doc_id))
            store.delete(ids)
            report.docs_removed += 1
            report.chunks_deleted += len(ids)
    return report


def main(argv: list[str] | None = None) -> int:
    from app.config import get_settings
    from app.llm import LLMGateway, get_llm_provider
    from app.rag.store import collection_name, make_client

    parser = argparse.ArgumentParser(description="Index /knowledge-base into ChromaDB.")
    parser.add_argument("--full", action="store_true", help="re-embed every document")
    parser.add_argument("--kb-dir", type=Path, help="default: KB_DIR setting")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    settings = get_settings()
    provider = get_llm_provider(settings)
    gateway = LLMGateway(provider, settings)
    store = KBStore(
        make_client(settings), collection_name(settings, provider.embedding_model_name())
    )
    report = ingest_knowledge_base(
        args.kb_dir or settings.kb_dir, store, gateway.embed_documents, full=args.full
    )
    print(report.summary())
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
