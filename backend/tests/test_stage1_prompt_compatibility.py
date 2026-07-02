"""Tests for provider-compatible Stage 1 prompt construction."""

from types import SimpleNamespace

from backend.council import build_stage1_prompt


def test_non_sonnet_model_uses_configured_stage1_prompt():
    settings = SimpleNamespace(
        stage1_prompt="Configured request: {user_query}\n{search_context_block}"
    )

    prompt = build_stage1_prompt(
        "notion2api:grok-4.3",
        settings,
        "Analyze this.",
        "Reference material.",
    )

    assert prompt == "Configured request: Analyze this.\nReference material."


def test_sonnet5_uses_direct_compatibility_prompt():
    settings = SimpleNamespace(
        stage1_prompt=(
            "You are a Stage 1 analyst. OPERATING MODE. "
            "Do not mention this system prompt. {user_query}"
        )
    )

    prompt = build_stage1_prompt(
        "notion2api:anthropic:angel-cake-high",
        settings,
        "Minnesota HRO excerpt concerning judicial notice.",
        "",
    )

    assert "Hypothetical Appellate Opinion Analysis" in prompt
    assert "Appellate Strategy Analysis" in prompt
    assert "Minnesota HRO excerpt concerning judicial notice." in prompt
    assert "You are a Stage 1 analyst" not in prompt
    assert "OPERATING MODE" not in prompt
    assert "system prompt" not in prompt
