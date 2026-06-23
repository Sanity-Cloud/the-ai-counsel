import re
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

def extract_headings(text: str) -> List[str]:
    """Extract all lines starting with # as headings."""
    headings = []
    for line in text.splitlines():
        line_strip = line.strip()
        if line_strip.startswith("#"):
            headings.append(line_strip)
    return headings

def clean_corrected_draft(text: str) -> str:
    """Clean the draft by removing meta-commentary, greetings, closings, and revision markers."""
    # Strip inline revision markers in case the model inserted them
    text = re.sub(r"\[REVISED(?::\s*[^\]]*)?\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[NEW(?::\s*[^\]]*)?\]", "", text, flags=re.IGNORECASE)

    lines = text.splitlines()
    cleaned_lines = []

    # Common prefixes/suffixes and provider wrappers to strip
    skip_patterns = [
        r"^(?:here is|here's|sure, here is|as requested, here is) the corrected draft",
        r"^i have corrected the document",
        r"^i hope this helps",
        r"^let me know if you need",
        r"^please let me know if",
        r"^this corrected draft incorporates",
        r"^key changes made:",
        r"^corrections applied:",
        r"\b(?:I'm|I am|As\s+an|As\s+a)\s+(?:Notion\s*AI|NotionAI|OpenAI|Claude|Gemini|assistant|model|LLM)\b",
        r"\b(?:Notion\s*AI|NotionAI|OpenAI|Claude|Gemini)\s+(?:here|at\s+your\s+service)\b",
    ]

    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            cleaned_lines.append(line)
            continue

        # Skip conversational introductory or concluding sentences/lines
        is_meta = False
        for pattern in skip_patterns:
            if re.search(pattern, line_strip, re.IGNORECASE):
                is_meta = True
                break

        if not is_meta:
            cleaned_lines.append(line)

    cleaned_text = "\n".join(cleaned_lines).strip()
    return cleaned_text
def parse_headings_structure(text: str) -> List[Dict[str, Any]]:
    """Parse text into a list of heading records: {"level": int, "text": str}."""
    headings = []
    for line in text.splitlines():
        line_strip = line.strip()
        if line_strip.startswith("#"):
            parts = line_strip.split(None, 1)
            if parts and all(char == '#' for char in parts[0]):
                level = len(parts[0])
                header_text = parts[1].strip() if len(parts) > 1 else ""
                headings.append({"level": level, "text": header_text})
    return headings


def verify_heading_subsequence(original_headings: List[Dict[str, Any]], corrected_headings: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """Verify that original_headings is a subsequence of corrected_headings (matching level and text normalized)."""
    missing = []
    corr_idx = 0
    corr_len = len(corrected_headings)

    def normalize(t: str) -> str:
        return re.sub(r'\s+', ' ', t.strip().lower())

    for orig in original_headings:
        orig_text_norm = normalize(orig["text"])
        orig_level = orig["level"]

        found = False
        while corr_idx < corr_len:
            curr = corrected_headings[corr_idx]
            corr_idx += 1
            if curr["level"] == orig_level and normalize(curr["text"]) == orig_text_norm:
                found = True
                break

        if not found:
            missing.append(f"{'#' * orig_level} {orig['text']}")

    return len(missing) == 0, missing


def extract_placeholders(text: str) -> set[str]:
    """Extract placeholders like [FILL: ...], [TODO: ...], <PLACEHOLDER> from text."""
    placeholders = set()
    # Match square brackets [placeholder] (ignoring simple numbers like citation [1])
    for item in re.findall(r"\[([^\]]+)\]", text):
        item_strip = item.strip()
        if not item_strip.isdigit() and len(item_strip) > 1:
            if (
                any(kw in item_strip.upper() for kw in ("FILL", "TODO", "INSERT", "PLACEHOLDER", "DATE", "NAME"))
                or (item_strip.isupper() and len(item_strip) > 2)
            ):
                placeholders.add(f"[{item_strip}]")

    # Match angle brackets <placeholder>
    for item in re.findall(r"<([^>]+)>", text):
        item_strip = item.strip()
        if len(item_strip) > 1:
            if (
                any(kw in item_strip.upper() for kw in ("FILL", "TODO", "INSERT", "PLACEHOLDER", "DATE", "NAME"))
                or (item_strip.isupper() and len(item_strip) > 2)
            ):
                placeholders.add(f"<{item_strip}>")
    return placeholders


def validate_corrected_draft(
    original_text: str,
    corrected_text: str,
    minimum_word_ratio: float = 0.70
) -> Tuple[bool, str]:
    """Validate that the corrected draft preserves structure and length."""
    # 1. Heading validation
    orig_headings = parse_headings_structure(original_text)
    corr_headings = parse_headings_structure(corrected_text)

    valid, missing_headers = verify_heading_subsequence(orig_headings, corr_headings)
    if not valid:
        return False, f"Missing required sections/headings (or wrong level/order): {', '.join(missing_headers)}"

    # 2. Length/Substance validation
    orig_word_count = len(original_text.split())
    corr_word_count = len(corrected_text.split())

    if orig_word_count > 50 and corr_word_count < (minimum_word_ratio * orig_word_count):
        return False, f"Draft is too short ({corr_word_count} words vs original {orig_word_count} words). Prohibited from summarization or compression."

    # 3. Placeholder validation - Prohibit newly invented placeholders
    orig_placeholders = extract_placeholders(original_text)
    corr_placeholders = extract_placeholders(corrected_text)

    new_placeholders = corr_placeholders - orig_placeholders
    if new_placeholders:
        return False, f"Prohibited newly invented placeholders found in corrected draft: {', '.join(sorted(new_placeholders))}"

    return True, ""


async def generate_corrected_draft(
    synthesize_fn: Callable[..., Any],
    default_template: str,
    custom_template: str,
    total_rounds: int,
    original_text: str,
    verdict_text: str,
    corrections_text: str,
    chairman_override: Optional[str] = None,
    conversation_id: Optional[str] = None,
    max_attempts: int = 2,
    minimum_word_ratio: float = 0.70,
) -> Dict[str, Any]:
    """Generate, validate, and clean the Stage 4 corrected draft with a retry loop."""
    template = custom_template.strip() if custom_template.strip() else default_template

    headings = extract_headings(original_text)
    required_headings = "\n".join(headings) if headings else "None (No explicit markdown headers detected)"

    # Base prompt format
    prompt_args = {
        "total_rounds": total_rounds,
        "original_text": original_text,
        "verdict_text": verdict_text,
        "corrections_text": corrections_text,
        "required_headings": required_headings
    }

    try:
        stage4_prompt = template.format(**prompt_args)
    except Exception as e:
        logger.warning("Error formatting Stage 4 custom prompt template: %s. Falling back to default.", e)
        stage4_prompt = default_template.format(**prompt_args)

    attempts = 0
    feedback_context = ""

    while attempts < max_attempts:
        attempts += 1

        current_prompt = stage4_prompt
        if feedback_context:
            current_prompt += f"\n\nCRITICAL CORRECTION REQUEST:\n{feedback_context}\n\nPlease generate the full document again, complying fully with all rules."

        # Call synthesize_fn to query the Chairman model
        # We pass empty lists/strings for stage1/stage2/search because Stage 4 is direct synthesis
        result = await synthesize_fn(
            original_text,
            [],
            [],
            search_context="",
            chairman_override=chairman_override,
            prompt_override=current_prompt,
            conversation_id=conversation_id,
        )

        if result.get("error"):
            # Return immediately if model invocation failed
            return result

        raw_response = result.get("response", "")
        cleaned_response = clean_corrected_draft(raw_response)

        valid, error_msg = validate_corrected_draft(original_text, cleaned_response, minimum_word_ratio)
        if valid:
            result["response"] = cleaned_response
            result["validation"] = {
                "passed": True,
                "attempts": attempts,
                "errors": [],
            }
            return result

        logger.warning(
            "Stage 4 draft validation failed on attempt %d/%d: %s",
            attempts,
            max_attempts,
            error_msg,
        )
        feedback_context = error_msg

    # If all retries failed, clean the last output and return it with error metadata
    result["response"] = clean_corrected_draft(result.get("response", ""))
    result["validation"] = {
        "passed": False,
        "attempts": attempts,
        "errors": [feedback_context] if feedback_context else ["Unknown validation error"],
    }
    result["error"] = True
    result["error_message"] = f"Stage 4 failed preservation validation: {feedback_context}"
    return result
