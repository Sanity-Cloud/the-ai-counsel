from __future__ import annotations

import asyncio
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from backend.main import app, _active_runs
from backend import storage

@pytest.mark.asyncio
async def test_retry_failed_provider_stage1(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    storage.create_conversation("conv-retry-s1")

    conv = storage.get_conversation("conv-retry-s1")
    conv["messages"] = [{"role": "user", "content": "Question S1"}]
    storage.save_conversation(conv)

    queue = asyncio.Queue()

    _active_runs["conv-retry-s1"] = {
        "paused": True,
        "failed_providers": ["openai:gpt-4.1"],
        "stage1_responses": [],
        "progress": {"stage1": {"total": 1}},
        "queue": queue,
        "continuation_mode": "normal",
        "search_context": "search content",
    }

    async def fake_query_model_gated(model_id, messages, **kwargs):
        return {
            "content": "Stage 1 mocked reply",
            "usage": {"total_tokens": 100},
            "cost": {"total_cost": 0.002}
        }

    with patch("backend.council._query_model_gated", side_effect=fake_query_model_gated):
        with TestClient(app) as client:
            response = client.post(
                "/api/conversations/conv-retry-s1/pause/retry",
                json={"model": "openai:gpt-4.1", "stage": "stage1"}
            )

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["result"]["response"] == "Stage 1 mocked reply"

    events = []
    while not queue.empty():
        events.append(await queue.get())

    assert any("provider_retrying" in e for e in events)
    assert any("provider_retry_result" in e for e in events)

    run_info = _active_runs.get("conv-retry-s1")
    assert run_info is not None
    assert "openai:gpt-4.1" not in run_info["failed_providers"]
    assert len(run_info["stage1_responses"]) == 1
    assert run_info["stage1_responses"][0]["response"] == "Stage 1 mocked reply"

    _active_runs.pop("conv-retry-s1", None)


@pytest.mark.asyncio
async def test_retry_failed_provider_stage2(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    storage.create_conversation("conv-retry-s2")

    conv = storage.get_conversation("conv-retry-s2")
    conv["messages"] = [{"role": "user", "content": "Question S2"}]
    storage.save_conversation(conv)

    queue = asyncio.Queue()

    _active_runs["conv-retry-s2"] = {
        "paused": True,
        "failed_providers": ["openai:gpt-4.2"],
        "stage1_responses": [
            {"model": "model_a", "response": "Response A content", "error": None},
            {"model": "model_b", "response": "Response B content", "error": None},
        ],
        "stage2_responses": [],
        "progress": {"stage2": {"total": 1}},
        "queue": queue,
        "continuation_mode": "normal",
        "search_context": "",
    }

    async def fake_query_model_gated(model_id, messages, **kwargs):
        return {
            "content": "FINAL RANKING:\n1. Response A\n2. Response B",
            "usage": {"total_tokens": 120},
            "cost": {"total_cost": 0.003}
        }

    with patch("backend.council._query_model_gated", side_effect=fake_query_model_gated):
        with TestClient(app) as client:
            response = client.post(
                "/api/conversations/conv-retry-s2/pause/retry",
                json={"model": "openai:gpt-4.2", "stage": "stage2"}
            )

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert "FINAL RANKING:" in res_data["result"]["ranking"]
    assert res_data["result"]["parsed_ranking"] == ["Response A", "Response B"]

    events = []
    while not queue.empty():
        events.append(await queue.get())

    assert any("provider_retrying" in e for e in events)
    assert any("provider_retry_result" in e for e in events)

    run_info = _active_runs.get("conv-retry-s2")
    assert run_info is not None
    assert "openai:gpt-4.2" not in run_info["failed_providers"]
    assert len(run_info["stage2_responses"]) == 1
    assert "FINAL RANKING:" in run_info["stage2_responses"][0]["ranking"]

    _active_runs.pop("conv-retry-s2", None)


@pytest.mark.asyncio
async def test_fire_pending_provider_stage1(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    storage.create_conversation("conv-fire-s1")

    conv = storage.get_conversation("conv-fire-s1")
    conv["messages"] = [{"role": "user", "content": "Question Fire S1"}]
    storage.save_conversation(conv)

    queue = asyncio.Queue()

    _active_runs["conv-fire-s1"] = {
        "paused": True,
        "pending_providers": ["openai:gpt-4.1"],
        "active_providers": [],
        "failed_providers": [],
        "stage1_responses": [],
        "progress": {"stage1": {"total": 1}},
        "queue": queue,
        "continuation_mode": "normal",
        "search_context": "",
    }

    async def fake_query_model_gated(model_id, messages, **kwargs):
        return {
            "content": "Fire s1 response",
            "usage": None,
            "cost": None
        }

    with patch("backend.council._query_model_gated", side_effect=fake_query_model_gated):
        with TestClient(app) as client:
            response = client.post(
                "/api/conversations/conv-fire-s1/pause/fire",
                json={"model": "openai:gpt-4.1", "stage": "stage1"}
            )

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["result"]["response"] == "Fire s1 response"

    events = []
    while not queue.empty():
        events.append(await queue.get())

    assert any("provider_fired_manual" in e for e in events)
    assert any("stage1_progress" in e for e in events)

    run_info = _active_runs.get("conv-fire-s1")
    assert run_info is not None
    assert "openai:gpt-4.1" not in run_info["pending_providers"]
    assert len(run_info["stage1_responses"]) == 1
    assert run_info["stage1_responses"][0]["response"] == "Fire s1 response"

    _active_runs.pop("conv-fire-s1", None)


@pytest.mark.asyncio
async def test_fire_pending_provider_stage2(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    storage.create_conversation("conv-fire-s2")

    conv = storage.get_conversation("conv-fire-s2")
    conv["messages"] = [{"role": "user", "content": "Question Fire S2"}]
    storage.save_conversation(conv)

    queue = asyncio.Queue()

    _active_runs["conv-fire-s2"] = {
        "paused": True,
        "pending_providers": ["openai:gpt-4.2"],
        "active_providers": [],
        "failed_providers": [],
        "stage1_responses": [
            {"model": "model_a", "response": "Response A content", "error": None},
            {"model": "model_b", "response": "Response B content", "error": None},
        ],
        "stage2_responses": [],
        "progress": {"stage2": {"total": 1}},
        "queue": queue,
        "continuation_mode": "normal",
        "search_context": "",
    }

    async def fake_query_model_gated(model_id, messages, **kwargs):
        return {
            "content": "FINAL RANKING:\n1. Response B\n2. Response A",
            "usage": None,
            "cost": None
        }

    with patch("backend.council._query_model_gated", side_effect=fake_query_model_gated):
        with TestClient(app) as client:
            response = client.post(
                "/api/conversations/conv-fire-s2/pause/fire",
                json={"model": "openai:gpt-4.2", "stage": "stage2"}
            )

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["result"]["parsed_ranking"] == ["Response B", "Response A"]

    events = []
    while not queue.empty():
        events.append(await queue.get())

    assert any("provider_fired_manual" in e for e in events)
    assert any("stage2_progress" in e for e in events)

    _active_runs.pop("conv-fire-s2", None)


def test_pause_retry_not_paused():
    _active_runs["conv-not-paused"] = {
        "paused": False,
    }
    with TestClient(app) as client:
        response = client.post(
            "/api/conversations/conv-not-paused/pause/retry",
            json={"model": "openai:gpt-4.1", "stage": "stage1"}
        )
    assert response.status_code == 400
    _active_runs.pop("conv-not-paused", None)


def test_pause_retry_not_found():
    with TestClient(app) as client:
        response = client.post(
            "/api/conversations/conv-nonexistent/pause/retry",
            json={"model": "openai:gpt-4.1", "stage": "stage1"}
        )
    assert response.status_code == 404
