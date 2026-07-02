"""Concurrency tests for council request start gating."""

import asyncio

import pytest

from backend import council


@pytest.mark.asyncio
async def test_non_notion_models_bypass_notion_gate(monkeypatch):
    async def fake_query_model_raw(*args, **kwargs):
        return {"content": "ok", "error": False}

    def fail_if_called():
        raise AssertionError("non-Notion model used the Notion gate")

    monkeypatch.setattr(council, "_query_model_raw", fake_query_model_raw)
    monkeypatch.setattr(council, "_notion_council_lock", fail_if_called)

    result = await council._query_model_gated(
        "openai:gpt-test",
        [{"role": "user", "content": "hello"}],
        timeout=30,
        temperature=0,
    )

    assert result["content"] == "ok"


@pytest.mark.asyncio
async def test_notion_requests_overlap_after_start_gate(monkeypatch):
    active = 0
    peak_active = 0
    both_started = asyncio.Event()

    async def fake_query_model_raw(*args, **kwargs):
        nonlocal active, peak_active
        active += 1
        peak_active = max(peak_active, active)
        if active == 2:
            both_started.set()
        await asyncio.wait_for(both_started.wait(), timeout=0.5)
        active -= 1
        return {"content": "ok", "error": False}

    monkeypatch.setattr(council, "_query_model_raw", fake_query_model_raw)
    monkeypatch.setattr(council, "_NOTION_STAGGER_SECONDS", 0.0)
    monkeypatch.setattr(council, "_last_notion_call_started_at", 0.0)
    monkeypatch.setattr(council, "_NOTION_COUNCIL_LOCK", None)
    monkeypatch.setattr(council, "_NOTION_COUNCIL_LOCK_LOOP", None)

    await asyncio.gather(
        council._query_model_gated(
            "notion2api:model-a",
            [{"role": "user", "content": "one"}],
            timeout=30,
            temperature=0,
        ),
        council._query_model_gated(
            "notion2api:model-b",
            [{"role": "user", "content": "two"}],
            timeout=30,
            temperature=0,
        ),
    )

    assert peak_active == 2
