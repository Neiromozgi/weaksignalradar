"""Bounded OpenAI LIVE LLM smoke (opt-in RUN_LIVE_LLM=1, requires OPENAI_API_KEY in env)."""

from __future__ import annotations

import hashlib
import os
from dataclasses import asdict

import httpx
import pytest
from sqlalchemy import create_engine


def _host_database_url() -> str | None:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return None
    return url.replace("@db:", "@127.0.0.1:")


@pytest.fixture
def pg_engine():
    from alembic import command
    from alembic.config import Config

    url = _host_database_url()
    if not url:
        pytest.skip("DATABASE_URL not set")
    os.environ["DATABASE_URL"] = url
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    return create_engine(url, pool_pre_ping=True)


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_LLM", "").strip() != "1"
    or not os.environ.get("OPENAI_API_KEY", "").strip(),
    reason="Set RUN_LIVE_LLM=1 and OPENAI_API_KEY for live LLM smoke",
)


class _CountingHttpClient:
    def __init__(self) -> None:
        self.post_count = 0
        self._inner = httpx.Client(timeout=90.0)

    def post(self, *args, **kwargs):
        self.post_count += 1
        return self._inner.post(*args, **kwargs)

    def close(self) -> None:
        self._inner.close()


def _fixture_evidence() -> tuple[str, list[str]]:
    from weaksignalradar.fasttrack.corpus.snapshot_loader import load_openalex_works

    works = load_openalex_works("ft_bench_v1")
    for work in works:
        abstract = (work.get("abstract_inverted_index") or work.get("abstract") or "")
        if isinstance(abstract, dict):
            # OpenAlex inverted index → plain text (minimal)
            words: list[tuple[int, str]] = []
            for word, positions in abstract.items():
                for pos in positions:
                    words.append((pos, word))
            abstract = " ".join(w for _, w in sorted(words))
        title = str(work.get("title") or work.get("display_name") or "candidate")
        text = str(abstract).strip() or title
        if len(text) >= 40:
            return title, [text]
    first = works[0]
    title = str(first.get("title") or "benchmark candidate")
    return title, [title]


def test_openai_live_extraction_persist_and_replay(pg_engine):
    from weaksignalradar.fasttrack.db.repository import PostgresRunRepository
    from weaksignalradar.fasttrack.llm.openai_responses import OpenAIResponsesExtractionAdapter
    from weaksignalradar.fasttrack.llm.profile import LLM_MODEL, LLM_PROFILE_ID

    candidate_name, evidence = _fixture_evidence()
    evidence_hash = hashlib.sha256("\n".join(evidence).encode("utf-8")).hexdigest()
    snapshot_id = "ft_bench_v1"
    run_id = "live_llm_smoke_run"
    candidate_id = "live_llm_smoke_cand"

    counter = _CountingHttpClient()
    try:
        adapter = OpenAIResponsesExtractionAdapter(
            api_key=os.environ["OPENAI_API_KEY"].strip(),
            http_client=counter,  # type: ignore[arg-type]
        )
        sig = adapter.extract_signature(candidate_name=candidate_name, evidence_texts=evidence)
    finally:
        counter.close()

    assert counter.post_count == 1, "expected exactly one OpenAI HTTP call"
    if sig.validation_status != "PASSED":
        pytest.fail(
            f"LLM LIVE failed: validation_status={sig.validation_status!r} "
            f"extraction_status={sig.extraction_status!r} model={LLM_MODEL}"
        )

    assert sig.llm_profile_id == LLM_PROFILE_ID
    assert sig.validation_status == "PASSED"
    assert sig.extraction_status in {"OK", "PARTIAL", "UNKNOWN"}
    assert isinstance(sig.evidence_span_refs, list)

    repo = PostgresRunRepository(pg_engine)
    repo.save_extraction(
        run_id=run_id,
        candidate_id=candidate_id,
        evidence_hash=evidence_hash,
        signature=sig,
        extraction_payload={"signature": asdict(sig)},
        provenance={"snapshot_id": snapshot_id, "mode": "SMOKE"},
    )

    replay = repo.get_extraction_replay(snapshot_id, candidate_id, evidence_hash)
    assert replay is not None
    assert replay.validation_status == "PASSED"

    counter2 = _CountingHttpClient()
    try:
        replay_only = repo.get_extraction_replay(snapshot_id, candidate_id, evidence_hash)
        assert replay_only is not None
        assert counter2.post_count == 0
    finally:
        counter2.close()
