import pytest
from backend.corrected_draft import (
    clean_corrected_draft,
    validate_corrected_draft,
    generate_corrected_draft,
)

def test_clean_corrected_draft_preserves_legitimate_references():
    # Legitimate reference inside text body should be kept:
    text = (
        "This document describes the company roadmap.\n"
        "We plan to evaluate OpenAI and Gemini for document classification.\n"
        "Our internal system currently integrates Claude."
    )
    cleaned = clean_corrected_draft(text)
    assert "OpenAI" in cleaned
    assert "Gemini" in cleaned
    assert "Claude" in cleaned
    assert "the Council" not in cleaned

def test_clean_corrected_draft_removes_wrapper_meta_commentary():
    # Conversational intro wrapper with model identity should be removed:
    text = (
        "I am Claude, and here is your corrected document:\n"
        "# Executive Summary\n"
        "The company is growing.\n"
        "I hope this helps!"
    )
    cleaned = clean_corrected_draft(text)
    assert "I am Claude" not in cleaned
    assert "I hope this helps!" not in cleaned
    assert "# Executive Summary" in cleaned
    assert "The company is growing." in cleaned

    # Notion AI wrapper should be removed:
    text = (
        "I'm Notion AI. As requested, here is the corrected draft:\n"
        "# Section 1\n"
        "Hello world"
    )
    cleaned = clean_corrected_draft(text)
    assert "Notion AI" not in cleaned
    assert "# Section 1" in cleaned

def test_validate_corrected_draft_headings_structure():
    original = "# Section A\n## Section A.1\n# Section B"

    # 1. Exact match should pass
    valid, err = validate_corrected_draft(original, "# Section A\n## Section A.1\n# Section B")
    assert valid
    assert not err

    # 2. Missing heading should fail
    valid, err = validate_corrected_draft(original, "# Section A\n# Section B")
    assert not valid
    assert "Missing required sections/headings" in err
    assert "Section A.1" in err

    # 3. Wrong relative order should fail
    valid, err = validate_corrected_draft(original, "# Section B\n# Section A\n## Section A.1")
    assert not valid
    assert "Wrong relative order" in err or "Missing" in err

    # 4. Wrong level should fail
    valid, err = validate_corrected_draft(original, "# Section A\n# Section A.1\n# Section B")
    assert not valid
    assert "Missing" in err

def test_validate_corrected_draft_length():
    original = "a " * 100

    # 1. 75% length should pass
    valid, err = validate_corrected_draft(original, "a " * 75)
    assert valid

    # 2. Under 70% length should fail
    valid, err = validate_corrected_draft(original, "a " * 65)
    assert not valid
    assert "Draft is too short" in err

@pytest.mark.asyncio
async def test_generate_corrected_draft_fails_validation_twice():
    async def fake_synthesize(*args, **kwargs):
        # Always return a compressed response that will fail validation
        return {"error": False, "response": "Too short response"}

    original = "a " * 100
    result = await generate_corrected_draft(
        synthesize_fn=fake_synthesize,
        default_template="Original: {original_text}\nVerdict: {verdict_text}\nCorrections: {corrections_text}",
        custom_template="",
        total_rounds=1,
        original_text=original,
        verdict_text="Some verdict",
        corrections_text="Some corrections",
        max_attempts=2,
    )

    assert result["error"] is True
    assert "Stage 4 failed preservation validation" in result["error_message"]
    assert result["validation"]["passed"] is False
    assert result["validation"]["attempts"] == 2
    assert len(result["validation"]["errors"]) == 1


def test_validate_corrected_draft_placeholders():
    original = "This is a document with [FILL: company name] and <DATE>."

    # 1. Exact or subset/resolved placeholders should pass
    # Resolved [FILL: company name] -> Acme Corp, but kept <DATE>
    valid, err = validate_corrected_draft(original, "This is a document with Acme Corp and <DATE>.")
    assert valid
    assert not err

    # 2. Re-introducing original placeholders should pass
    valid, err = validate_corrected_draft(original, "This is a document with [FILL: company name] and <DATE>.")
    assert valid
    assert not err

    # 3. Newly invented placeholder should fail
    valid, err = validate_corrected_draft(original, "This is a document with Acme Corp and <DATE> and [TODO: add logo].")
    assert not valid
    assert "Prohibited newly invented placeholders" in err
    assert "TODO: add logo" in err
