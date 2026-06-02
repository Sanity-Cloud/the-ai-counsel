from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.council import clean_generated_short_text, generate_conversation_title, generate_search_query


def test_clean_generated_short_text_strips_complete_think_block_before_truncation():
    title = clean_generated_short_text(
        "<think>The user wants a 3-stage council comparison.</think>\n\nModel Metrics Matrix"
    )

    assert title == "Model Metrics Matrix"


def test_clean_generated_short_text_falls_back_when_think_block_is_unclosed():
    title = clean_generated_short_text(
        "<think>The user wants a 3-stage council comparison.",
        fallback="Why is the matrix truncated?",
    )

    assert title == "Why is the matrix truncated?"


def test_clean_generated_short_text_removes_title_prefix_quotes_and_punctuation():
    assert clean_generated_short_text('"Title: Council Matrix Layout."') == "Council Matrix Layout"


@pytest.mark.asyncio
async def test_generate_conversation_title_sanitizes_reasoning_output():
    with (
        patch("backend.council.get_chairman_model", return_value="openai:gpt-4.1"),
        patch("backend.council.query_model", new_callable=AsyncMock) as mock_query,
    ):
        mock_query.return_value = {
            "error": False,
            "content": "<think>Need a concise title.</think>\n\nMatrix Scaling Fix",
        }

        title = await generate_conversation_title("Why is the matrix truncated?")

    assert title == "Matrix Scaling Fix"


@pytest.mark.asyncio
async def test_generate_search_query_sanitizes_reasoning_output():
    with (
        patch("backend.council.get_chairman_model", return_value="openai:gpt-4.1"),
        patch("backend.council.query_model", new_callable=AsyncMock) as mock_query,
    ):
        mock_query.return_value = {
            "error": False,
            "content": "<think>Need search terms.</think>\n\nCSS sticky table horizontal scroll",
        }

        query = await generate_search_query("How do I make a wide table usable?")

    assert query == "CSS sticky table horizontal scroll"
