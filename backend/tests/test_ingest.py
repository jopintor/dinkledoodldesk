from pathlib import Path

from app.llm.fake import HashEmbeddings
from app.rag.ingest import ingest_knowledge_base
from app.rag.store import collection_name

DOC = """---
id: {doc_id}
title: Doc {doc_id}
category: network
audience_roles: [staff]
last_updated: 2026-01-01
owner: IT
---
# Doc

## Only section

{body}
"""


class CountingEmbedder:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self._inner = HashEmbeddings(768)

    def __call__(self, texts: list[str]) -> list[list[float]]:
        self.texts += texts
        return self._inner.embed_documents(texts)


def write_doc(kb: Path, doc_id: str, body: str = "word " * 80) -> Path:
    path = kb / f"{doc_id.lower()}.md"
    path.write_text(DOC.format(doc_id=doc_id, body=body), encoding="utf-8")
    return path


def test_collection_name_includes_model_and_dimension(settings):
    name = collection_name(settings, "models/gemini-embedding-001")
    assert name == f"{settings.chroma_collection}__gemini-embedding-001__768"


def test_reingest_skips_unchanged_documents(store, tmp_path):
    write_doc(tmp_path, "KB-001")
    write_doc(tmp_path, "KB-002")
    embed = CountingEmbedder()

    first = ingest_knowledge_base(tmp_path, store, embed)
    assert (first.docs_indexed, first.chunks_embedded) == (2, 2)
    second = ingest_knowledge_base(tmp_path, store, embed)
    assert (second.docs_indexed, second.docs_unchanged) == (0, 2)
    assert len(embed.texts) == 2  # nothing re-embedded
    assert store.chunk_ids() == {"KB-001-c01", "KB-002-c01"}


def test_changed_document_is_replaced_and_stale_chunks_deleted(store, tmp_path):
    long_body = "\n\n".join(f"## Part {i}\n\n" + "word " * 80 for i in range(3))
    path = write_doc(tmp_path, "KB-001", long_body)
    embed = CountingEmbedder()
    ingest_knowledge_base(tmp_path, store, embed)
    assert len(store.chunk_ids("KB-001")) == 3

    path.write_text(DOC.format(doc_id="KB-001", body="changed " * 80), encoding="utf-8")
    report = ingest_knowledge_base(tmp_path, store, embed)
    assert (report.docs_indexed, report.chunks_deleted) == (1, 2)
    assert store.chunk_ids("KB-001") == {"KB-001-c01"}
    assert "changed changed" in store.all_chunks()[0].text


def test_deleted_document_is_pruned_but_not_when_a_file_is_invalid(store, tmp_path):
    write_doc(tmp_path, "KB-001")
    gone = write_doc(tmp_path, "KB-002")
    embed = CountingEmbedder()
    ingest_knowledge_base(tmp_path, store, embed)

    gone.unlink()
    bad = tmp_path / "kb-003.md"
    bad.write_text("no front matter\n", encoding="utf-8")
    report = ingest_knowledge_base(tmp_path, store, embed)
    assert not report.ok and report.docs_removed == 0
    assert "KB-002-c01" in store.chunk_ids()

    bad.unlink()
    report = ingest_knowledge_base(tmp_path, store, embed)
    assert report.ok and report.docs_removed == 1
    assert store.chunk_ids() == {"KB-001-c01"}


def test_embedding_failure_aborts_and_rerun_continues(store, tmp_path):
    for doc_id in ("KB-001", "KB-002", "KB-003"):
        write_doc(tmp_path, doc_id)
    good = CountingEmbedder()
    calls = {"n": 0}

    def flaky(texts):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
        return good(texts)

    report = ingest_knowledge_base(tmp_path, store, flaky)
    assert report.aborted and report.docs_indexed == 1
    report = ingest_knowledge_base(tmp_path, store, good)
    assert report.ok and (report.docs_indexed, report.docs_unchanged) == (2, 1)
