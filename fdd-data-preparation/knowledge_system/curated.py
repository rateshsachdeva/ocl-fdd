"""Source-controlled curated knowledge and knowledge-assisted fast-path routing.

This module contains only reusable structural/semantic lessons distilled from
approved synthetic training prompts and golden-truth structure. It deliberately
contains no expected financial amounts, FDD conclusions, deal issues or answers.

The embedded runtime still profiles and validates the current source package.
Curated knowledge can reduce repeated AI discovery for an exact known training
pattern, but current source evidence always wins.
"""
from __future__ import annotations

import csv
import importlib
import json
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent
CURATED_ROOT = ROOT / "curated"
CURATED_KNOWLEDGE_ASSETS = ("field_knowledge.csv", "structure_knowledge.csv")
PATTERNS_PATH = CURATED_ROOT / "fast_path_patterns.json"


def hydrate_curated_knowledge(runtime_project: Path) -> dict[str, int]:
    """Merge source-controlled curated rows into the extracted runtime knowledge.

    The merge is schema-preserving and de-duplicated. A future runtime schema
    change simply causes that curated asset to be skipped rather than allowing an
    old training schema to replace the runtime's current contract.
    """
    destination_root = Path(runtime_project) / "knowledge"
    if not destination_root.is_dir():
        return {}

    merged: dict[str, int] = {}
    for name in CURATED_KNOWLEDGE_ASSETS:
        curated_path = CURATED_ROOT / name
        runtime_path = destination_root / name
        if not curated_path.exists() or not runtime_path.exists():
            continue
        runtime_header, runtime_rows = _read_csv(runtime_path)
        curated_header, curated_rows = _read_csv(curated_path)
        if not runtime_header or runtime_header != curated_header:
            continue

        seen = {_row_key(row) for row in runtime_rows}
        additions = [row for row in curated_rows if _row_key(row) not in seen]
        if additions:
            _write_csv(runtime_path, runtime_header, [*runtime_rows, *additions])
        merged[name] = len(additions)
    return merged


def configure_runtime(_fdd_data: object | None = None) -> None:
    """Install the curated routing/request wrapper into the extracted runtime."""
    orchestration = importlib.import_module("fdd_data.orchestration")
    if getattr(orchestration, "_ocl_curated_fast_path_configured", False):
        return

    original_assess = orchestration.assess_profile_complexity
    original_write_request = orchestration._write_fast_path_request

    def assess_profile_complexity(profile: dict[str, Any]) -> dict[str, Any]:
        base = original_assess(profile)
        return apply_curated_fast_path(profile, base)

    def write_fast_path_request(workflow_directory: Path, state: dict[str, Any]) -> None:
        original_write_request(workflow_directory, state)
        request_path = Path(workflow_directory) / "ai_tasks" / "fast_path_planning_request.json"
        profile_path = _state_profile_path(Path(workflow_directory), state)
        if request_path.exists() and profile_path and profile_path.exists():
            augment_fast_path_request(request_path, _read_json(profile_path))

    orchestration.assess_profile_complexity = assess_profile_complexity
    orchestration._write_fast_path_request = write_fast_path_request
    orchestration._ocl_curated_fast_path_configured = True


def apply_curated_fast_path(
    profile: dict[str, Any],
    base_assessment: dict[str, Any],
) -> dict[str, Any]:
    """Allow one-cycle planning for a strongly recognized curated pattern.

    Only known structural ambiguity reasons may be overridden. Profiling
    failures or any unrecognized reason retain the normal conservative complex
    path.
    """
    pattern = match_curated_pattern(profile)
    if pattern is None:
        return dict(base_assessment)

    reasons = list(base_assessment.get("reasons") or [])
    if not reasons:
        result = dict(base_assessment)
        result.update({
            "curated_pattern_id": pattern["pattern_id"],
            "knowledge_assisted_fast_path": True,
            "recognized_complexity_reasons": [],
        })
        return result

    allowed = set(pattern.get("allow_fast_path_complexity_types") or [])
    categories = [_complexity_reason_type(reason) for reason in reasons]
    if any(category is None or category not in allowed for category in categories):
        result = dict(base_assessment)
        result.update({
            "curated_pattern_id": pattern["pattern_id"],
            "knowledge_assisted_fast_path": False,
        })
        return result

    result = dict(base_assessment)
    result.update({
        "workflow_mode": "FAST_PATH",
        "requires_targeted_inspection": False,
        "reasons": [],
        "recognized_complexity_reasons": reasons,
        "curated_pattern_id": pattern["pattern_id"],
        "knowledge_assisted_fast_path": True,
        "routing_note": (
            "Known synthetic training structure recognized. Use one AI understanding/planning "
            "cycle; current source evidence and deterministic validation remain authoritative."
        ),
    })
    return result


def match_curated_pattern(profile: dict[str, Any]) -> dict[str, Any] | None:
    """Return a pattern only when all strong signature requirements are present."""
    signatures = _profile_signatures(profile)
    for pattern in _load_patterns():
        files = {str(value).casefold() for value in pattern.get("required_source_files", [])}
        worksheets = {str(value).casefold() for value in pattern.get("required_worksheets", [])}
        headers = {str(value).casefold() for value in pattern.get("required_headers", [])}
        if not files.issubset(signatures["source_files"]):
            continue
        if not worksheets.issubset(signatures["worksheets"]):
            continue
        if not headers.issubset(signatures["headers"]):
            continue
        return pattern
    return None


def augment_fast_path_request(request_path: Path, profile: dict[str, Any]) -> bool:
    """Add compact curated context to the single AI planning request."""
    pattern = match_curated_pattern(profile)
    if pattern is None:
        return False

    request_path = Path(request_path)
    payload = _read_json(request_path)
    if not payload:
        return False

    payload["curated_training_pattern"] = {
        "pattern_id": pattern["pattern_id"],
        "description": pattern.get("description"),
        "hints": list(pattern.get("hints") or []),
        "status": "ADVISORY_HIGH_CONFIDENCE_STRUCTURE_KNOWLEDGE",
        "guardrail": (
            "Use these hints only when consistent with the current compact profile. "
            "Do not import expected financial balances, OCL conclusions, deal issues, key findings or answers."
        ),
    }
    payload["curated_knowledge_paths"] = [
        str((CURATED_ROOT / name).resolve()) for name in CURATED_KNOWLEDGE_ASSETS
    ] + [str(PATTERNS_PATH.resolve())]
    payload["performance_instruction"] = (
        "KNOWLEDGE-ASSISTED FAST PATH: resolve the recognized structural pattern from the compact "
        "profile, representative values, prior knowledge and curated hints first. Do not browse or "
        "scan the raw workbooks and do not request targeted inspection merely to reconfirm a curated "
        "pattern. Use bounded targeted inspection only when the current profile contradicts a hint, a "
        "required field/grain remains genuinely unresolved, or deterministic validation cannot otherwise "
        "be satisfied. Create dataset_map.json, processing_plan.json and approval_questions.json in this "
        "single reasoning cycle."
    )
    payload["targeted_inspection"] = (
        "For this recognized training pattern, targeted inspection is exception-only: use it solely for "
        "a concrete contradiction or unresolved evidence gap."
    )
    _write_json(request_path, payload)
    return True


def _profile_signatures(profile: dict[str, Any]) -> dict[str, set[str]]:
    source_files = {
        str(source.get("filename") or "").strip().casefold()
        for source in profile.get("source_files", [])
        if source.get("filename")
    }
    worksheets: set[str] = set()
    headers: set[str] = set()
    for workbook in profile.get("workbook_profiles", []):
        for worksheet in workbook.get("worksheet_profiles", []):
            name = str(worksheet.get("worksheet_name") or "").strip()
            if name:
                worksheets.add(name.casefold())
            for region in worksheet.get("data_regions", []):
                for field in region.get("column_profiles", []):
                    for key in ("exact_original_header", "normalized_display_header"):
                        value = str(field.get(key) or "").strip()
                        if value:
                            headers.add(value.casefold())
    return {"source_files": source_files, "worksheets": worksheets, "headers": headers}


def _complexity_reason_type(reason: str) -> str | None:
    text = str(reason or "").casefold()
    if "not fully profiled" in text:
        return "not_fully_profiled"
    if "contains multiple physical tables" in text:
        return "multiple_physical_tables"
    if "ambiguous header row" in text:
        return "ambiguous_header"
    if "multi-row header candidate" in text:
        return "multi_row_header"
    return None


def _load_patterns() -> list[dict[str, Any]]:
    payload = _read_json(PATTERNS_PATH)
    patterns = payload.get("patterns")
    return [item for item in patterns if isinstance(item, dict)] if isinstance(patterns, list) else []


def _state_profile_path(workflow_directory: Path, state: dict[str, Any]) -> Path | None:
    value = state.get("profile_path")
    if not value:
        return None
    path = Path(str(value))
    return path if path.is_absolute() else workflow_directory / path


def _read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    return (rows[0], rows[1:]) if rows else ([], [])


def _write_csv(path: Path, header: list[str], rows: Iterable[list[str]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def _row_key(row: Iterable[str]) -> tuple[str, ...]:
    return tuple(str(value or "").strip() for value in row)


def _read_json(path: Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


__all__ = [
    "augment_fast_path_request",
    "apply_curated_fast_path",
    "configure_runtime",
    "hydrate_curated_knowledge",
    "match_curated_pattern",
]
