"""Tests for Stage 2 ranking parse helpers."""

import pytest

from backend.council import (
    EvaluationError,
    PROVIDERS,
    _STAGE2_MODEL_ALIAS_CACHE,
    build_stage2_label_aliases,
    build_stage2_result,
    build_stage_texts,
    is_annotation_only_evaluator_output,
    is_evaluator_refusal,
    parse_ranking_from_text,
)


def test_parse_ranking_filters_hallucinated_labels():
    text = """Response A is strong.
Response B is weaker.

FINAL RANKING:
1. Response C
2. Response A
3. Response B"""

    parsed = parse_ranking_from_text(
        text,
        expected_count=2,
        valid_labels=["Response A", "Response B"],
    )

    assert parsed == ["Response A", "Response B"]


def test_parse_ranking_deduplicates_labels():
    text = """FINAL RANKING:
1. Response A
2. Response A
3. Response B"""

    parsed = parse_ranking_from_text(
        text,
        expected_count=2,
        valid_labels=["Response A", "Response B"],
    )

    assert parsed == ["Response A", "Response B"]


def test_parse_ranking_recovers_markdown_heading_and_parenthesized_numbers():
    text = """Response A is more complete, while Response B is more concise.

### **Final Ranking**
1) **Response B**
2) **Response A**"""

    parsed = parse_ranking_from_text(
        text,
        expected_count=2,
        valid_labels=["Response A", "Response B"],
    )

    assert parsed == ["Response B", "Response A"]


def test_parse_ranking_recovers_inline_freeform_order():
    text = """Both answers are useful, but B is more precise.

Overall ranking (best to worst): Response B > Response A"""

    parsed = parse_ranking_from_text(
        text,
        expected_count=2,
        valid_labels=["Response A", "Response B"],
    )

    assert parsed == ["Response B", "Response A"]


def test_parse_ranking_recovers_numbered_tail_without_heading():
    text = """Response A is thorough. Response B is more focused.

1. Response B
2. Response A"""

    parsed = parse_ranking_from_text(
        text,
        expected_count=2,
        valid_labels=["Response A", "Response B"],
    )

    assert parsed == ["Response B", "Response A"]


def test_parse_ranking_resolves_plain_model_names_before_claim_json():
    text = """FINAL RANKING:

Opus 4.7
GPT 5.5
GLM 5.2
DeepSeek V4 Pro
Gemini 3.5 Flash
Grok 4.3
Grok Build0.1
Gemini 3.1 Pro
{ "A1": {"verdict": "strong", "reason": "Claim audit follows."} }"""
    labels = [f"Response {letter}" for letter in "ABCDEFGH"]
    aliases = {
        "Response A": ["Gemini 3.5 Flash"],
        "Response B": ["Gemini 3.1 Pro"],
        "Response C": ["GLM 5.2"],
        "Response D": ["Grok 4.3"],
        "Response E": ["DeepSeek V4 Pro"],
        "Response F": ["GPT-5.5"],
        "Response G": ["Grok Build 0.1"],
        "Response H": ["Opus 4.7"],
    }

    parsed = parse_ranking_from_text(
        text,
        expected_count=8,
        valid_labels=labels,
        label_aliases=aliases,
    )

    assert parsed == [
        "Response H",
        "Response F",
        "Response C",
        "Response E",
        "Response A",
        "Response D",
        "Response G",
        "Response B",
    ]


def test_build_stage2_result_accepts_model_name_ranking():
    result = build_stage2_result(
        "evaluator-model",
        {
            "content": "FINAL RANKING:\nOpus 4.7\nGPT 5.5\n{\"A1\": {\"verdict\": \"strong\"}}",
            "error": False,
        },
        valid_labels=["Response A", "Response B"],
        expected_count=2,
        label_aliases={
            "Response A": ["GPT-5.5"],
            "Response B": ["Opus 4.7"],
        },
    )

    assert result["status"] == "completed"
    assert result["error"] is None
    assert result["parsed_ranking"] == ["Response B", "Response A"]


def test_parse_model_name_ranking_rejects_duplicates():
    with pytest.raises(EvaluationError, match="Duplicate ranked model name"):
        parse_ranking_from_text(
            "FINAL RANKING:\nOpus 4.7\nOpus 4.7",
            expected_count=2,
            valid_labels=["Response A", "Response B"],
            label_aliases={
                "Response A": ["Opus 4.7"],
                "Response B": ["GPT 5.5"],
            },
        )


@pytest.mark.asyncio
async def test_stage2_aliases_use_provider_model_metadata(monkeypatch):
    class FakeProvider:
        async def get_models(self):
            return [{
                "id": "notion2api:apricot-sorbet-high",
                "display_name": "Opus 4.7",
                "name": "Opus 4.7 [Notion2API]",
                "aliases": ["claude-opus4.7"],
            }]

    monkeypatch.setitem(PROVIDERS, "notion2api", FakeProvider())
    _STAGE2_MODEL_ALIAS_CACHE.pop("notion2api:apricot-sorbet-high", None)

    aliases = await build_stage2_label_aliases({
        "Response A": "notion2api:apricot-sorbet-high",
    })

    assert "Opus 4.7" in aliases["Response A"]
    assert "claude-opus4.7" in aliases["Response A"]


def test_annotation_only_output_is_rejected_as_a_ranking():
    text = """[
  {"response": "Response A", "paragraph": 1, "verdict": "strong", "comment": "Accurate."},
  {"response": "Response B", "paragraph": 1, "verdict": "weak", "comment": "Incomplete."}
]"""

    assert is_annotation_only_evaluator_output(text) is True

    result = build_stage2_result(
        "model-a",
        {"content": text, "error": False},
        valid_labels=["Response A", "Response B"],
        expected_count=2,
    )

    assert result["error"] is True
    assert result["status"] == "annotation_only_evaluator_output"
    assert result["parsed_ranking"] == []
    assert "omitted the required complete peer ranking" in result["error_message"]


def test_build_stage_texts_excludes_failed_rankings():
    stage1 = [{"model": "model-a", "response": "Candidate answer"}]
    stage2 = [
        {"model": "model-a", "ranking": "Valid ranking", "error": None},
        {"model": "model-b", "ranking": "Malformed model-name ranking", "error": True},
    ]

    _, stage2_text = build_stage_texts(stage1, stage2)

    assert "Valid ranking" in stage2_text
    assert "Malformed model-name ranking" not in stage2_text


def test_detects_stage2_refusal_separately_from_format_error():
    refusal = """I cannot perform this task.

I am Notion AI, and my capabilities are strictly limited to Notion workspace operations.
I do not have tools or the ability to compare, analyze, or rank external candidate responses.
"""

    assert is_evaluator_refusal(refusal) is True
    assert is_evaluator_refusal("FINAL RANKING:\n1. Response B\n2. Response A") is False