import json

import pytest

from app.rag.retriever import (
    BM25_ONLY_CONFIDENCE,
    Retriever,
    band_for,
    retrieval_confidence,
    tokenize,
)

GOLDEN_ROLES = ("member", "staff", "agent", "admin")


def test_tokenizer_keeps_ids_codes_and_network_names():
    tokens = tokenize("KB-003 error 0x51 on PickleHub-Staff, code 123456; wifi")
    for token in ("kb-003", "0x51", "picklehub-staff", "123456", "wi-fi"):
        assert token in tokens
    assert "picklehub" in tokens and "staff" in tokens  # parts are indexed too
    assert "on" not in tokens


@pytest.mark.parametrize(
    ("cosine", "agree", "expected"),
    [
        (0.85, True, 1.0),
        (0.95, False, 0.8),
        (0.45, True, 0.2),
        (0.30, False, 0.0),
        (0.65, True, 0.6),
    ],
)
def test_confidence_formula(settings, cosine, agree, expected):
    assert retrieval_confidence(cosine, agree, settings) == pytest.approx(expected)


def test_bands_use_design_thresholds(settings):
    assert [band_for(c, settings) for c in (0.70, 0.69, 0.50, 0.49)] == [
        "high",
        "medium",
        "medium",
        "low",
    ]


def test_members_never_retrieve_staff_only_documents(retriever):
    result = retriever.search("PickleHub-Staff Wi-Fi password keeps asking", "member")
    assert result.chunks
    assert all("member" in c.chunk.roles for c in result.chunks)
    assert "KB-011" not in result.doc_ids
    assert "KB-012" in result.doc_ids


def test_superseded_policy_is_hidden_from_staff_and_downranked_for_agents(retriever):
    query = "Can staff use the VPN from personal laptops? remote access policy PH-Remote"
    staff = retriever.search(query, "staff")
    assert "KB-014" not in staff.doc_ids

    agent = retriever.search(query, "agent")
    assert "KB-014" in agent.doc_ids
    assert agent.doc_ids.index("KB-013") < agent.doc_ids.index("KB-014")
    kb014 = next(c for c in agent.chunks if c.chunk.doc_id == "KB-014")
    assert kb014.context_header.startswith("[SUPERSEDED — replaced by KB-013] KB-014")


def test_context_is_packed_with_at_most_two_chunks_per_document(retriever):
    result = retriever.search("StaffID password reset portal temporary password", "staff")
    assert 0 < len(result.chunks) <= 5
    for doc_id in result.doc_ids:
        assert sum(c.chunk.doc_id == doc_id for c in result.chunks) <= 2
    scores = [c.rrf_score for c in result.chunks]
    assert scores == sorted(scores, reverse=True)


def test_falls_back_to_bm25_when_query_embedding_fails(indexed_kb):
    settings, store, _ = indexed_kb

    def broken(_text):
        raise RuntimeError("429 RESOURCE_EXHAUSTED")

    result = Retriever(store, broken, settings).search("DinkPOS PIN locked", "staff")
    assert not result.vector_ok
    assert result.doc_ids[0] == "KB-007"
    assert result.retrieval_confidence == BM25_ONLY_CONFIDENCE


def test_kb_version_is_stable_and_unknown_role_rejected(retriever):
    assert retriever.kb_version == retriever.kb_version != "empty"
    with pytest.raises(ValueError):
        retriever.search("anything", "guest")


def test_offline_hit_rate_on_golden_normal_questions(retriever, settings):
    """Regression guard with fake embeddings (BM25 does most of the work offline)."""
    golden = settings.kb_dir.parent / "eval" / "golden-set" / "golden_set.jsonl"
    items = [json.loads(line) for line in golden.read_text(encoding="utf-8").splitlines()]
    normal = [i for i in items if i["category"] == "normal"]
    assert len(normal) == 20 and {i["user_role"] for i in normal} <= set(GOLDEN_ROLES)
    hits = sum(
        any(
            d in retriever.search(i["question"], i["user_role"]).doc_ids
            for d in i["expected_source_ids"]
        )
        for i in normal
    )
    assert hits / len(normal) >= 0.9
