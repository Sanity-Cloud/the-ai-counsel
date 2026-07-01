"""Regression tests for Stage 2 prompt overrides and anonymous ranking labels."""
from types import SimpleNamespace

import pytest

from backend import council
from backend.prompts import STAGE2_CLAIM_PROMPT


def test_claim_prompt_requires_ranking_before_json():
    ranking_index = STAGE2_CLAIM_PROMPT.index("FINAL RANKING:")
    json_index = STAGE2_CLAIM_PROMPT.index("```json")

    assert ranking_index < json_index
    assert "Respond with valid JSON followed by your ranking" not in STAGE2_CLAIM_PROMPT
    assert "Begin with the complete ranking" in STAGE2_CLAIM_PROMPT


@pytest.mark.asyncio
async def test_prompt_override_receives_anonymous_label_contract(monkeypatch):
    captured_prompts = []

    settings = SimpleNamespace(
        response_language="English",
        stage2_prompt="",
        stage2_temperature=0.3,
        model_timeout_seconds=5,
        notion2api_firing_mode="rapid_fire",
        notion2api_sequential_max_concurrent=3,
        notion2api_pause_on_failure=False,
    )

    async def fake_query_model(model, messages, **kwargs):
        captured_prompts.append(messages[-1]["content"])
        return {
            "content": "{}\nFINAL RANKING:\n1. Response A\n2. Response B",
            "error": False,
        }

    monkeypatch.setattr(council, "get_settings", lambda: settings)
    monkeypatch.setattr(council, "query_model", fake_query_model)

    stage1_results = [
        {"model": "openai:model-a", "response": "First answer", "error": None},
        {"model": "openai:model-b", "response": "Second answer", "error": None},
    ]

    items = []
    async for item in council.stage2_collect_rankings(
        "Question",
        stage1_results,
        prompt_override="Evaluate the supplied claims.",
    ):
        items.append(item)

    assert len(captured_prompts) == 2
    for prompt in captured_prompts:
        assert "CRITICAL OUTPUT CONTRACT" in prompt
        assert "Response A, Response B" in prompt
        assert "Do not identify, infer, mention, or rank model/provider names" in prompt

    results = [item for item in items if isinstance(item, dict) and item.get("model")]
    assert all(result["parsed_ranking"] == ["Response A", "Response B"] for result in results)


@pytest.mark.asyncio
async def test_stage2_retries_truncated_output_with_compact_ranking_prompt(monkeypatch):
    calls = []
    per_model_calls = {}
    settings = SimpleNamespace(
        response_language="English",
        stage2_prompt="",
        stage2_temperature=0.2,
        stage2_max_output_tokens=16000,
        model_timeout_seconds=5,
        notion2api_firing_mode="rapid_fire",
        notion2api_sequential_max_concurrent=3,
        notion2api_pause_on_failure=False,
    )

    async def fake_query_model(model, messages, **kwargs):
        calls.append((model, messages[-1]["content"], kwargs))
        count = per_model_calls.get(model, 0) + 1
        per_model_calls[model] = count
        if count == 1:
            return {
                "content": "Detailed audit that ended before the ranking.",
                "finish_reason": "length",
                "error": False,
            }
        return {
            "content": "FINAL RANKING:\n1. Response B\n2. Response A",
            "finish_reason": "stop",
            "error": False,
        }

    monkeypatch.setattr(council, "get_settings", lambda: settings)
    monkeypatch.setattr(council, "query_model", fake_query_model)

    stage1_results = [
        {"model": "notion2api:model-a", "response": "First answer", "error": None},
        {"model": "notion2api:model-b", "response": "Second answer", "error": None},
    ]
    items = []
    async for item in council.stage2_collect_rankings(
        "Question",
        stage1_results,
        conversation_id="conversation-1",
    ):
        items.append(item)

    results = [item for item in items if isinstance(item, dict) and item.get("model")]
    assert len(results) == 2
    assert all(result["error"] is None for result in results)
    assert all(result["recovered_after_retry"] is True for result in results)
    assert all(result["parsed_ranking"] == ["Response B", "Response A"] for result in results)
    assert all(result["attempts"][0]["status"] == "truncated_evaluator_output" for result in results)
    assert all(result["max_output_tokens"] == 16000 for result in results)
    assert len(calls) == 4
    assert all(call[2]["max_output_tokens"] == 16000 for call in calls)
    retry_prompts = [prompt for _, prompt, _ in calls if "RECOVERY RETRY" in prompt]
    assert len(retry_prompts) == 2
    assert all("Return ONLY the complete ranking block" in prompt for prompt in retry_prompts)


@pytest.mark.asyncio
async def test_stage2_retries_annotation_only_output_as_invalid_ranking(monkeypatch):
    per_model_calls = {}
    settings = SimpleNamespace(
        response_language="English",
        stage2_prompt="",
        stage2_temperature=0.2,
        stage2_max_output_tokens=12000,
        model_timeout_seconds=5,
        notion2api_firing_mode="rapid_fire",
        notion2api_sequential_max_concurrent=3,
        notion2api_pause_on_failure=False,
    )

    async def fake_query_model(model, messages, **kwargs):
        count = per_model_calls.get(model, 0) + 1
        per_model_calls[model] = count
        if count == 1:
            return {
                "content": '[{"response":"Response A","paragraph":1,"verdict":"strong","comment":"ok"},'
                           '{"response":"Response B","paragraph":1,"verdict":"weak","comment":"thin"}]',
                "error": False,
            }
        return {
            "content": "FINAL RANKING:\n1. Response A\n2. Response B",
            "error": False,
        }

    monkeypatch.setattr(council, "get_settings", lambda: settings)
    monkeypatch.setattr(council, "query_model", fake_query_model)

    stage1_results = [
        {"model": "model-a", "response": "First answer", "error": None},
        {"model": "model-b", "response": "Second answer", "error": None},
    ]
    items = []
    async for item in council.stage2_collect_rankings("Question", stage1_results):
        items.append(item)

    results = [item for item in items if isinstance(item, dict) and item.get("model")]
    assert len(results) == 2
    assert all(result["error"] is None for result in results)
    assert all(result["recovered_after_retry"] is True for result in results)
    assert all(result["attempts"][0]["status"] == "annotation_only_evaluator_output" for result in results)


@pytest.mark.asyncio
async def test_stage2_retries_when_ranking_is_valid_but_claim_payload_is_missing(monkeypatch):
    calls = []
    per_model_calls = {}
    settings = SimpleNamespace(
        response_language="English",
        stage2_prompt="",
        stage2_temperature=0.2,
        stage2_max_output_tokens=12000,
        model_timeout_seconds=5,
        notion2api_firing_mode="rapid_fire",
        notion2api_sequential_max_concurrent=3,
        notion2api_pause_on_failure=False,
    )

    async def fake_query_model(model, messages, **kwargs):
        calls.append(messages[-1]["content"])
        count = per_model_calls.get(model, 0) + 1
        per_model_calls[model] = count
        if count == 1:
            return {
                "content": "FINAL RANKING:\n1. Response A\n2. Response B",
                "error": False,
            }
        return {
            "content": (
                "FINAL RANKING:\n1. Response A\n2. Response B\n\n"
                '{"A1":{"verdict":"strong","reason":"The claim is directly supported by the supplied record and reasoning."}}'
            ),
            "error": False,
        }

    def validate_claim_payload(text):
        if '"A1"' not in text:
            raise council.EvaluationError("Claim evaluation JSON is not an object")
        return {"claim_verdicts": {"A1": {"verdict": "strong", "reason": "supported"}}}

    monkeypatch.setattr(council, "get_settings", lambda: settings)
    monkeypatch.setattr(council, "query_model", fake_query_model)

    stage1_results = [
        {"model": "model-a", "response": "First answer", "error": None},
        {"model": "model-b", "response": "Second answer", "error": None},
    ]
    items = []
    async for item in council.stage2_collect_rankings(
        "Question",
        stage1_results,
        output_validator=validate_claim_payload,
        structured_output_recovery=(
            "Return a JSON object containing A1 with verdict and reason fields."
        ),
    ):
        items.append(item)

    results = [item for item in items if isinstance(item, dict) and item.get("model")]
    assert len(results) == 2
    assert all(result["error"] is None for result in results)
    assert all(result["recovered_after_retry"] is True for result in results)
    assert all(result["attempts"][0]["status"] == "invalid_structured_evaluator_output" for result in results)
    assert all("claim_verdicts" in result for result in results)
    retry_prompts = [prompt for prompt in calls if "RECOVERY RETRY" in prompt]
    assert len(retry_prompts) == 2
    assert all("After the ranking block" in prompt for prompt in retry_prompts)
    assert all("containing A1" in prompt for prompt in retry_prompts)
    assert all("Allowed labels: Response A, Response B" in prompt for prompt in retry_prompts)
    assert all("Respond with valid JSON followed by your ranking" not in prompt for prompt in retry_prompts)
    assert all("CRITICAL OUTPUT CONTRACT" not in prompt for prompt in retry_prompts)
