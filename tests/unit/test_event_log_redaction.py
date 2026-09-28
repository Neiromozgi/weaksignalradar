
from weaksignalradar.observability.event_log import _redact_text, emit_event, read_recent_events


def test_redact_api_key_and_database_url():
    raw = "postgresql+psycopg://user:secret@db:5432/wsr OPENAI sk-abc1234567890xyz"
    out = _redact_text(raw)
    assert "secret" not in out
    assert "sk-abc1234567890xyz" not in out
    assert "REDACTED" in out


def test_emit_and_read_events(tmp_path, monkeypatch):
    log_file = tmp_path / "snnit-radar.jsonl"
    monkeypatch.setenv("WSR_EVENT_LOG_PATH", str(log_file))
    emit_event("SERVICE_STARTED", component="test", extra={"note": "ok"})
    events = read_recent_events(limit=5)
    assert len(events) == 1
    assert events[0]["event"] == "SERVICE_STARTED"
    assert "sk-" not in log_file.read_text(encoding="utf-8")
