"""AI-host handoff for FDD partner-level OCL interpretation.

Python prepares and validates evidence. The active coding AI writes narrative
judgment and management questions only; it never recalculates or overrides
financial metrics.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from ocl_agent.schemas import AnalysisResult


class AnalysisInterpretationError(ValueError):
    pass


def write_analysis_request(
    result: AnalysisResult,
    output_path: Path,
    *,
    required_artifact: Path,
    instruction_path: Path,
) -> Path:
    """Write the finalized Python-analysis evidence package the AI host may interpret."""
    output_path = Path(output_path)
    required_artifact = Path(required_artifact)
    evidence = {
        "annual_periods": list(result.annual_periods),
        "monthly_periods": list(result.monthly_periods),
        "latest_annual_period": result.latest_annual_period,
        "deterministic_findings": [_finding_payload(item) for item in result.findings],
        "analysis_tables": [_table_payload(table) for table in result.tables],
    }
    evidence_hash = _hash_payload(evidence)
    valid_refs = [f"finding:{item.finding_id}" for item in result.findings]
    for table in result.tables:
        valid_refs.extend(f"table:{table.key}:{index}" for index, _row in enumerate(table.rows))

    payload = {
        "request_version": "1.1",
        "next_actor": "AI_HOST",
        "next_action": "WRITE_FDD_PARTNER_ANALYSIS",
        "analysis_status": "FINALIZED",
        "source_scope": "PYTHON_ANALYSIS_ONLY",
        "instruction_path": str(instruction_path),
        "required_artifact": str(required_artifact),
        "evidence_hash": evidence_hash,
        "valid_evidence_refs": valid_refs,
        "evidence": evidence,
        "rules": [
            "Think and write as an experienced FDD partner.",
            "The deterministic Python analysis is finalized before this checkpoint.",
            "Use only the supplied finalized analysis evidence; do not reopen raw client data to create new findings.",
            "Do not recalculate, invent or override financial values or materiality.",
            "Triangulate related analysis tables/findings before deciding whether a point is a Deal Issue, Key Finding or Q&A item.",
            "Separate factual evidence from FDD implication and from evidence limitations.",
            "State the specific fact that would confirm, rebut or change a provisional FDD conclusion.",
            "Do not create filler findings or questions merely to populate a sheet.",
            "If no material issue is supported, state that conclusion explicitly rather than leaving the output blank.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, default=_json_default) + "\n", encoding="utf-8")
    return output_path


def load_analysis_interpretation(path: Path, request_path: Path) -> dict[str, Any]:
    """Load and validate AI narrative against the exact finalized Python evidence package."""
    path = Path(path)
    request_path = Path(request_path)
    if not path.exists():
        raise AnalysisInterpretationError(f"Analysis interpretation does not exist: {path}")
    request = json.loads(request_path.read_text(encoding="utf-8"))
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AnalysisInterpretationError("analysis_interpretation.json must contain a JSON object.")
    if request.get("analysis_status") != "FINALIZED" or request.get("source_scope") != "PYTHON_ANALYSIS_ONLY":
        raise AnalysisInterpretationError("Partner interpretation may only run from finalized Python analysis evidence.")
    if payload.get("status") != "COMPLETED":
        raise AnalysisInterpretationError("analysis_interpretation.json status must be COMPLETED.")
    if payload.get("evidence_hash") != request.get("evidence_hash"):
        raise AnalysisInterpretationError("Analysis interpretation is stale or belongs to different evidence; evidence_hash does not match.")

    overall = str(payload.get("overall_assessment") or "").strip()
    if not overall:
        raise AnalysisInterpretationError("overall_assessment is required.")

    deal_issues = payload.get("deal_issues")
    key_findings = payload.get("key_findings")
    questions = payload.get("management_questions")
    if not isinstance(deal_issues, list) or not isinstance(key_findings, list) or not isinstance(questions, list):
        raise AnalysisInterpretationError("deal_issues, key_findings and management_questions must be JSON arrays.")
    if len(deal_issues) > 6:
        raise AnalysisInterpretationError("Use no more than 6 deal issues.")
    if not key_findings:
        raise AnalysisInterpretationError("At least one key finding/conclusion is required so the workbook is never blank.")
    if len(key_findings) > 8:
        raise AnalysisInterpretationError("Use no more than 8 key findings.")
    if len(questions) > 8:
        raise AnalysisInterpretationError("Use no more than 8 management questions.")

    valid_refs = set(request.get("valid_evidence_refs") or [])
    valid_findings = {
        str(item.get("finding_id"))
        for item in request.get("evidence", {}).get("deterministic_findings", [])
        if item.get("finding_id")
    }
    for item in deal_issues:
        _validate_item(
            item,
            kind="deal issue",
            required=("id", "title", "fdd_lens", "so_what", "evidence", "evidence_limit", "management_focus"),
            valid_refs=valid_refs,
            valid_findings=valid_findings,
        )
        priority = str(item.get("priority") or "").upper()
        if priority not in {"HIGH", "MEDIUM", "LOW"}:
            raise AnalysisInterpretationError("Deal issue priority must be HIGH, MEDIUM or LOW.")
    for item in key_findings:
        _validate_item(
            item,
            kind="key finding",
            required=(
                "id",
                "fdd_lens",
                "area",
                "metric",
                "period_item",
                "so_what",
                "evidence",
                "evidence_limit",
                "fact_to_establish",
                "materiality",
            ),
            valid_refs=valid_refs,
            valid_findings=valid_findings,
        )
        materiality = str(item.get("materiality") or "").upper()
        if materiality not in {"MATERIAL", "NOTABLE", "NO_MATERIAL_ISSUE"}:
            raise AnalysisInterpretationError("Key finding materiality must be MATERIAL, NOTABLE or NO_MATERIAL_ISSUE.")
    for item in questions:
        _validate_item(
            item,
            kind="management question",
            required=("id", "fdd_lens", "theme", "question", "why_it_matters", "evidence", "priority"),
            valid_refs=valid_refs,
            valid_findings=valid_findings,
        )
        priority = str(item.get("priority") or "").upper()
        if priority not in {"HIGH", "MEDIUM", "LOW"}:
            raise AnalysisInterpretationError("Management question priority must be HIGH, MEDIUM or LOW.")
    return payload


def _validate_item(
    item: Any,
    *,
    kind: str,
    required: tuple[str, ...],
    valid_refs: set[str],
    valid_findings: set[str],
) -> None:
    if not isinstance(item, dict):
        raise AnalysisInterpretationError(f"Each {kind} must be a JSON object.")
    missing = [key for key in required if not str(item.get(key) or "").strip()]
    if missing:
        raise AnalysisInterpretationError(f"{kind.title()} is missing required field(s): {', '.join(missing)}")
    refs = item.get("evidence_refs")
    if not isinstance(refs, list) or not refs:
        raise AnalysisInterpretationError(f"Each {kind} must contain at least one evidence_refs entry.")
    invalid = [str(ref) for ref in refs if str(ref) not in valid_refs]
    if invalid:
        raise AnalysisInterpretationError(f"{kind.title()} contains invalid evidence reference(s): {', '.join(invalid)}")
    linked = item.get("linked_finding_id")
    if linked not in (None, "") and str(linked) not in valid_findings:
        raise AnalysisInterpretationError(f"{kind.title()} linked_finding_id is not present in deterministic findings: {linked}")


def _finding_payload(item) -> dict[str, Any]:
    return {
        "finding_id": item.finding_id,
        "title": item.title,
        "text": item.text,
        "finding_type": item.finding_type,
        "priority": item.priority,
        "evidence_references": list(item.evidence_references),
        "metrics": _jsonable(item.metrics),
    }


def _table_payload(table) -> dict[str, Any]:
    return {
        "key": table.key,
        "title": table.title,
        "headers": list(table.headers),
        "rows": [_jsonable(list(row)) for row in table.rows],
    }


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=_json_default).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
