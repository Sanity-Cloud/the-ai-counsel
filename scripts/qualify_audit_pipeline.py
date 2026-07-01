#!/usr/bin/env python3
"""Opt-in real-provider qualification for the Audit pipeline.

Run from the repository root with the project virtual environment:

    $env:RUN_REAL_PROVIDER_TESTS = "1"
    .\.venv\Scripts\python.exe scripts\qualify_audit_pipeline.py

The script reads Council models, Chairman, provider endpoints, and credentials from
normal application settings. Optional environment overrides:

    AUDIT_QUALIFICATION_MODELS=model-a,model-b
    AUDIT_QUALIFICATION_CHAIRMAN=chairman-model
    AUDIT_QUALIFICATION_PROFILE=general|legal
    AUDIT_QUALIFICATION_REPORT=X:\path\report.json
    AUDIT_QUALIFICATION_INCLUDE_RESPONSES=1

Normal unit tests never import or invoke this script. Reports are sanitized by
default and written below data/qualification, which is ignored by Git.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.audit_pipeline import run_audit_pipeline
from backend.config import get_chairman_model, get_council_models
from backend.model_preflight import preflight_models
from backend.providers.notion2api import Notion2APIProvider
from backend.settings import get_settings, normalize_model_ids

_TRUE_VALUES = {"1", "true", "yes", "on"}
_REQUIRED_EVENT_TYPES = {
    "stage1_start",
    "stage1_progress",
    "stage2a_start",
    "stage2a_complete",
    "stage2b_start",
    "stage2b_complete",
    "stage2c_start",
    "stage2c_complete",
    "stage3_start",
    "stage3_complete",
    "stage4_start",
    "stage4_complete",
    "debate_complete",
}

_DEFAULT_PROMPT = """Audit and correct the following short technical brief. Preserve the heading and all three numbered claims in the corrected draft.

# Boiling Point Brief

1. Pure water at standard sea-level atmospheric pressure boils at approximately 100 degrees Celsius.
2. Pure water always boils at exactly 100 degrees Celsius at every altitude and pressure.
3. Changes in atmospheric pressure change the boiling temperature of water.

Identify which claims are well supported, which require correction or qualification, and produce a corrected brief."""


def _env_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in _TRUE_VALUES


def _qualification_enabled() -> bool:
    return _env_enabled("RUN_REAL_PROVIDER_TESTS") or _env_enabled(
        "RUN_AUDIT_PROVIDER_QUALIFICATION"
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_report_path() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return ROOT / "data" / "qualification" / f"audit-provider-{stamp}.json"


def _parse_models(raw: str | None, configured: Iterable[str]) -> list[str]:
    source = raw.split(",") if raw else list(configured)
    models = normalize_model_ids([str(item).strip() for item in source])
    limit_raw = os.getenv("AUDIT_QUALIFICATION_MODEL_LIMIT", "2").strip()
    try:
        limit = max(2, int(limit_raw))
    except ValueError:
        limit = 2
    return models[:limit]


def _event_model(event: dict[str, Any]) -> str | None:
    data = event.get("data")
    if isinstance(data, dict):
        model = data.get("model")
        return str(model) if model else None
    return None


def _safe_error(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: value.get(key)
            for key in ("stage", "status", "message", "error_message")
            if value.get(key) is not None
        }
    if value is None:
        return None
    return str(value)[:500]


def _summarize_event(event: dict[str, Any], elapsed_ms: int) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "type": event.get("type", "unknown"),
        "elapsed_ms": elapsed_ms,
    }
    for key in ("round", "count", "total", "status"):
        if event.get(key) is not None:
            summary[key] = event.get(key)

    model = _event_model(event)
    if model:
        summary["model"] = model

    if event.get("message"):
        summary["message"] = str(event.get("message"))[:500]
    if event.get("error"):
        summary["error"] = _safe_error(event.get("error"))

    event_type = event.get("type")
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    if event_type == "stage2c_complete":
        aggregate = event.get("aggregated") or {}
        summary["audit_status"] = aggregate.get("audit_status")
        summary["claims_evaluated"] = aggregate.get("claims_evaluated")
        summary["valid_evaluators"] = aggregate.get("valid_evaluators")
        summary["expected_evaluators"] = aggregate.get("expected_evaluators")
    elif event_type == "stage4_complete":
        validation = data.get("validation") or {}
        summary["error"] = bool(data.get("error"))
        summary["fallback_used"] = bool(data.get("fallback_used"))
        summary["validation_passed"] = validation.get("passed")
    elif event_type == "debate_complete":
        summary["convergence_status"] = event.get("convergence_status")
        summary["debate_rounds_executed"] = event.get("debate_rounds_executed")
        summary["terminal_error"] = _safe_error(event.get("error"))
    return summary


def _record_from_stage2c(stage2c: Any) -> dict[str, Any]:
    if not isinstance(stage2c, dict):
        return {}
    record = stage2c.get("record")
    if isinstance(record, dict):
        return record
    if any(key in stage2c for key in ("adopt", "reject", "qualify")):
        return stage2c
    return {}


def _stage4_acceptable(stage4: Any) -> tuple[bool, str]:
    if not isinstance(stage4, dict):
        return False, "Stage 4 result is missing or not an object"
    response = str(stage4.get("response") or "").strip()
    if response and not stage4.get("error"):
        return True, "non-empty corrected draft"

    validation = stage4.get("validation") or {}
    explicit_preservation_failure = (
        bool(stage4.get("error"))
        and validation.get("passed") is False
        and "preservation validation" in str(stage4.get("error_message") or "").lower()
    )
    if explicit_preservation_failure:
        return True, "explicit preservation-validation failure with fallback"
    return False, "Stage 4 produced neither a corrected draft nor an explicit preservation failure"


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _validate_run(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    event_types = [str(event.get("type") or "") for event in events]
    missing = sorted(_REQUIRED_EVENT_TYPES.difference(event_types))
    checks.append(
        _check(
            "required_event_sequence",
            not missing,
            "all required event types observed" if not missing else f"missing: {', '.join(missing)}",
        )
    )

    terminal = next(
        (event for event in reversed(events) if event.get("type") == "debate_complete"),
        None,
    )
    checks.append(_check("terminal_event", terminal is not None, "debate_complete observed"))
    if not terminal:
        return checks

    rounds = terminal.get("rounds") or []
    final_round = rounds[-1] if rounds and isinstance(rounds[-1], dict) else {}
    metadata = final_round.get("metadata") or {}

    canonical_claims = metadata.get("canonical_claims") or []
    claim_ids = {
        str(claim.get("claim_id"))
        for claim in canonical_claims
        if isinstance(claim, dict) and claim.get("claim_id")
    }
    checks.append(
        _check(
            "canonical_claims",
            bool(canonical_claims),
            f"{len(canonical_claims)} canonical claims",
        )
    )

    stage2a = final_round.get("stage2a") or metadata.get("stage2a_results") or []
    valid_2a = [item for item in stage2a if isinstance(item, dict) and not item.get("error")]
    checks.append(
        _check(
            "stage2a_quorum",
            len(valid_2a) >= 2,
            f"{len(valid_2a)} valid holistic evaluators",
        )
    )

    aggregate = metadata.get("aggregate_claim_verdicts") or metadata.get("aggregated_2b") or {}
    valid_2b = int(aggregate.get("valid_evaluators") or 0)
    expected_2b = int(aggregate.get("expected_evaluators") or 0)
    quorum_ratio = valid_2b / max(1, expected_2b)
    stage2b_ok = (
        aggregate.get("audit_status") in {"complete", "partial"}
        and valid_2b >= 2
        and quorum_ratio >= 0.5
    )
    checks.append(
        _check(
            "stage2b_quorum",
            stage2b_ok,
            f"status={aggregate.get('audit_status')}, valid={valid_2b}, expected={expected_2b}",
        )
    )

    stage2c = final_round.get("stage2c") or metadata.get("stage2c_result") or {}
    record = _record_from_stage2c(stage2c)
    record_keys = (
        "adopt",
        "reject",
        "qualify",
        "authority_gaps",
        "record_gaps",
        "stage3_constraints",
    )
    schema_ok = bool(record) and all(isinstance(record.get(key), list) for key in record_keys)
    checks.append(_check("stage2c_schema", schema_ok, "valid correction-record schema" if schema_ok else "invalid correction-record schema"))

    referenced_ids = {
        str(claim_id)
        for key in ("adopt", "reject", "qualify")
        for claim_id in (record.get(key) or [])
    }
    invalid_ids = sorted(referenced_ids.difference(claim_ids))
    checks.append(
        _check(
            "stage2c_claim_references",
            not invalid_ids,
            "all referenced IDs are canonical" if not invalid_ids else f"unknown IDs: {', '.join(invalid_ids)}",
        )
    )

    stage3 = final_round.get("stage3") or {}
    stage3_text = str(stage3.get("response") or "").strip() if isinstance(stage3, dict) else ""
    stage3_ok = bool(stage3_text) and not stage3.get("error")
    checks.append(
        _check(
            "stage3_synthesis",
            stage3_ok,
            f"{len(stage3_text)} characters" if stage3_ok else str(stage3.get("error_message") or "empty synthesis"),
        )
    )

    stage4 = terminal.get("stage4")
    if stage4 is None:
        stage4_event = next(
            (event for event in reversed(events) if event.get("type") == "stage4_complete"),
            {},
        )
        stage4 = stage4_event.get("data")
    stage4_ok, stage4_detail = _stage4_acceptable(stage4)
    checks.append(_check("stage4_result", stage4_ok, stage4_detail))

    terminal_error = terminal.get("error")
    terminal_ok = terminal.get("convergence_status") != "failed" and not terminal_error
    checks.append(
        _check(
            "terminal_status",
            terminal_ok,
            "no silent provider failure" if terminal_ok else json.dumps(_safe_error(terminal_error), ensure_ascii=False),
        )
    )
    return checks


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


async def _provider_preflight(models: list[str], chairman: str) -> tuple[bool, str]:
    settings = get_settings()
    selected = normalize_model_ids([*models, chairman])

    notion_models = [model for model in selected if model.lower().startswith("notion2api:")]
    if notion_models:
        provider = Notion2APIProvider()
        result = await provider.validate_connection(
            settings.notion2api_base_url,
            settings.notion2api_api_key or os.getenv("NOTION2API_API_KEY") or "",
        )
        if not result.get("success"):
            return False, str(result.get("message") or "Notion2API unavailable")

        available = await provider.get_models()
        accepted: set[str] = set()
        for item in available:
            model_id = str(item.get("id") or "").strip().lower()
            if model_id:
                accepted.add(model_id)
            for alias in item.get("aliases") or []:
                clean = str(alias).strip().lower()
                if clean:
                    accepted.add(f"notion2api:{clean}")
        missing = [model for model in notion_models if model.lower() not in accepted]
        if missing:
            return False, f"Notion2API does not currently advertise: {', '.join(missing)}"

    preflight = await preflight_models(selected, timeout=settings.preflight_timeout_seconds)
    if preflight.failures:
        details = "; ".join(
            f"{item['model']}: {item['error']}" for item in preflight.failures
        )
        return False, f"provider preflight failed: {details}"
    if preflight.timeouts:
        return False, f"provider preflight timed out: {', '.join(preflight.timeouts)}"
    if preflight.rate_limited:
        return False, f"provider preflight remained rate-limited: {', '.join(preflight.rate_limited)}"
    return True, "provider preflight passed"


async def _run(args: argparse.Namespace) -> int:
    report_path = Path(
        args.report
        or os.getenv("AUDIT_QUALIFICATION_REPORT", "")
        or _default_report_path()
    ).resolve()
    include_responses = args.include_responses or _env_enabled(
        "AUDIT_QUALIFICATION_INCLUDE_RESPONSES"
    )

    settings = get_settings()
    models = _parse_models(
        args.models or os.getenv("AUDIT_QUALIFICATION_MODELS"),
        get_council_models(),
    )
    chairman = (
        args.chairman
        or os.getenv("AUDIT_QUALIFICATION_CHAIRMAN", "").strip()
        or get_chairman_model()
    )
    profile = (
        args.profile
        or os.getenv("AUDIT_QUALIFICATION_PROFILE", "").strip()
        or settings.audit_profile
        or "general"
    )
    prompt = args.prompt or _DEFAULT_PROMPT

    report: dict[str, Any] = {
        "schema_version": 1,
        "started_at": _utc_now(),
        "status": "pending",
        "models": models,
        "chairman": chairman,
        "audit_profile": profile,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "prompt_characters": len(prompt),
        "events": [],
        "checks": [],
    }
    if include_responses:
        report["debug_prompt"] = prompt

    if not _qualification_enabled():
        report["status"] = "skipped"
        report["skip_reason"] = (
            "Set RUN_REAL_PROVIDER_TESTS=1 or RUN_AUDIT_PROVIDER_QUALIFICATION=1 to opt in."
        )
        report["finished_at"] = _utc_now()
        _write_report(report_path, report)
        print(f"SKIPPED: {report['skip_reason']}")
        print(f"Sanitized report: {report_path}")
        return 0

    if len(models) < 2:
        report["status"] = "skipped"
        report["skip_reason"] = "At least two configured Council models are required."
        report["finished_at"] = _utc_now()
        _write_report(report_path, report)
        print(f"SKIPPED: {report['skip_reason']}")
        print(f"Sanitized report: {report_path}")
        return 0
    if not chairman:
        report["status"] = "skipped"
        report["skip_reason"] = "A configured Chairman model is required."
        report["finished_at"] = _utc_now()
        _write_report(report_path, report)
        print(f"SKIPPED: {report['skip_reason']}")
        print(f"Sanitized report: {report_path}")
        return 0
    if profile not in {"general", "legal"}:
        report["status"] = "failed"
        report["failure"] = f"Unsupported audit profile: {profile}"
        report["finished_at"] = _utc_now()
        _write_report(report_path, report)
        print(f"FAILED: {report['failure']}")
        return 2

    available, preflight_message = await _provider_preflight(models, chairman)
    report["preflight"] = {"passed": available, "detail": preflight_message}
    if not available:
        report["status"] = "skipped"
        report["skip_reason"] = preflight_message
        report["finished_at"] = _utc_now()
        _write_report(report_path, report)
        print(f"SKIPPED: {preflight_message}")
        print(f"Sanitized report: {report_path}")
        return 0

    events: list[dict[str, Any]] = []
    raw_events: list[dict[str, Any]] = []
    started = time.monotonic()
    conversation_id = f"audit-qualification-{uuid.uuid4().hex[:12]}"
    try:
        async for event in run_audit_pipeline(
            prompt,
            search_context="",
            request=None,
            execution_mode="full",
            models_override=models,
            chairman_override=chairman,
            history=None,
            debate_rounds=1,
            conversation_id=conversation_id,
            audit_profile=profile,
        ):
            if not isinstance(event, dict):
                continue
            raw_events.append(event)
            elapsed_ms = int((time.monotonic() - started) * 1000)
            events.append(_summarize_event(event, elapsed_ms))
            print(f"[{elapsed_ms:>7} ms] {event.get('type', 'unknown')}")
    except Exception as exc:
        report["status"] = "failed"
        report["failure"] = f"{type(exc).__name__}: {exc}"
        report["events"] = events
        report["duration_ms"] = int((time.monotonic() - started) * 1000)
        report["finished_at"] = _utc_now()
        _write_report(report_path, report)
        print(f"FAILED: {report['failure']}")
        print(f"Sanitized report: {report_path}")
        return 1

    checks = _validate_run(raw_events)
    passed = all(check["passed"] for check in checks)
    report["status"] = "passed" if passed else "failed"
    report["events"] = events
    report["checks"] = checks
    report["duration_ms"] = int((time.monotonic() - started) * 1000)
    report["finished_at"] = _utc_now()
    if include_responses:
        report["debug_events"] = raw_events
    _write_report(report_path, report)

    print("\nQualification checks:")
    for check in checks:
        marker = "PASS" if check["passed"] else "FAIL"
        print(f"  {marker:4}  {check['name']}: {check['detail']}")
    print(f"\nResult: {report['status'].upper()}")
    print(f"Sanitized report: {report_path}")
    return 0 if passed else 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models",
        help="Comma-separated Council model IDs. Defaults to the first two configured models.",
    )
    parser.add_argument("--chairman", help="Chairman model ID. Defaults to application settings.")
    parser.add_argument("--profile", choices=("general", "legal"), help="Audit prompt profile.")
    parser.add_argument("--prompt", help="Qualification prompt override.")
    parser.add_argument("--report", help="Output JSON report path.")
    parser.add_argument(
        "--include-responses",
        action="store_true",
        help="Include raw event payloads and the full prompt in the report. May contain sensitive text.",
    )
    return parser


def main() -> int:
    return asyncio.run(_run(_build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
