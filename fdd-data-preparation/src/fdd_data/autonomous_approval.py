"""Conservative approval-policy checks for autonomous databook workflows."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from .approval_questions import unresolved_blocking_questions
from .processing_plan import compare_source_snapshot, validate_processing_plan


AUTONOMOUS_APPROVAL_POLICY_VERSION = "1.0"
AI_HOST_APPROVER = "AI_HOST_AUTONOMOUS"


def evaluate_processing_approval(
    plan: dict[str, Any],
    profile: dict[str, Any],
    dataset_map: dict[str, Any],
    questions: dict[str, Any],
    source_directory: str,
) -> dict[str, Any]:
    """Return an auditable allow/escalate decision without approving a plan."""
    reasons: list[str] = []
    validation_errors = validate_processing_plan(plan, profile, dataset_map)
    if validation_errors:
        reasons.append("Processing Plan does not pass deterministic validation.")
    snapshot = compare_source_snapshot(plan.get("plan_metadata", {}).get("source_snapshot", {}), source_directory)
    if snapshot.get("status") != "SOURCE_UNCHANGED":
        reasons.append("The bound source snapshot is no longer unchanged.")
    if unresolved_blocking_questions(questions):
        reasons.append("Material user decisions remain unresolved.")

    assessment = plan.get("autonomous_approval_assessment", {})
    required_assessment = {
        "status": "APPROVE",
        "confidence": "HIGH",
        "unresolved_material_issue_count": 0,
        "deterministic_transformations": True,
        "source_fidelity_prioritized": True,
        "expected_output_grain_defined": True,
        "inclusion_exclusion_explicit": True,
        "reconciliation_expectations_defined": True,
    }
    for field, expected in required_assessment.items():
        if assessment.get(field) != expected:
            reasons.append(f"Autonomous approval assessment does not establish {field}.")
    if not assessment.get("rationale") or not assessment.get("source_evidence_summary"):
        reasons.append("Autonomous approval assessment lacks rationale or source evidence summary.")

    profiled_regions = {
        region["region_id"]
        for workbook in profile.get("workbook_profiles", [])
        for worksheet in workbook.get("worksheet_profiles", [])
        for region in worksheet.get("data_regions", [])
    }
    accounted_regions = {
        reference.get("region_id")
        for output in plan.get("proposed_outputs", [])
        for assignment in output.get("source_assignments", [])
        for reference in assignment.get("source_references", [])
    }
    accounted_regions.update(
        reference.get("region_id")
        for output in plan.get("proposed_outputs", [])
        for exclusion in output.get("exclusions", [])
        for reference in exclusion.get("source_references", [])
    )
    datasets_by_id = {
        dataset.get("logical_dataset_id"): dataset
        for dataset in dataset_map.get("logical_datasets", [])
    }
    accounted_regions.update(
        reference.get("region_id")
        for item in plan.get("non_output_logical_datasets", [])
        for reference in datasets_by_id.get(item.get("logical_dataset_id"), {}).get("contributing_source_regions", [])
    )
    accounted_regions.discard(None)
    if profiled_regions - accounted_regions:
        reasons.append("Some profiled source regions lack explicit inclusion or exclusion treatment.")
    for output in plan.get("proposed_outputs", []):
        if not output.get("output_grain") or not output.get("transformations"):
            reasons.append("A proposed output lacks an explicit grain or transformation sequence.")
        operations = {str(step.get("operation", "")).upper() for step in output.get("transformations", [])}
        if operations & {"AGGREGATE", "NET", "SIGN_CONVERSION"}:
            reasons.append("A transformation with material accounting interpretation requires human escalation.")
        for issue in output.get("unresolved_issues", []):
            if issue.get("material") is True or issue.get("requires_human_decision") is True:
                reasons.append("A proposed output contains an unresolved material issue.")

    decision = "APPROVE" if not reasons else "ESCALATE"
    return {
        "approver_type": AI_HOST_APPROVER,
        "approval_policy_version": AUTONOMOUS_APPROVAL_POLICY_VERSION,
        "decision": decision,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "plan_id": plan.get("plan_metadata", {}).get("plan_id"),
        "plan_version": plan.get("plan_metadata", {}).get("plan_version"),
        "plan_hash": plan.get("plan_metadata", {}).get("plan_hash"),
        "approval_rationale": assessment.get("rationale"),
        "source_evidence_summary": assessment.get("source_evidence_summary"),
        "unresolved_material_issue_count": assessment.get("unresolved_material_issue_count"),
        "confidence": assessment.get("confidence"),
        "source_snapshot_status": snapshot.get("status"),
        "reasons": reasons,
    }


def review_knowledge_candidates(candidates: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Approve only quality-cleared reusable learning; never auto-approve corrections."""
    reviewed = deepcopy(candidates)
    decisions = []
    for candidate in reviewed.get("candidates", []):
        decision, rationale = _knowledge_decision(candidate)
        candidate["user_confirmed"] = decision in {"KEEP", "MERGE"}
        decisions.append({
            "candidate_id": candidate.get("candidate_id"),
            "decision": decision,
            "rationale": rationale,
            "confidentiality_result": candidate.get("confidentiality_review"),
            "proposed_action": candidate.get("proposed_action"),
        })
    audit = {
        "approver_type": AI_HOST_APPROVER,
        "approval_policy_version": AUTONOMOUS_APPROVAL_POLICY_VERSION,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "candidate_set_hash": _candidate_set_hash(candidates),
        "decisions": decisions,
    }
    return reviewed, audit


def _knowledge_decision(candidate: dict[str, Any]) -> tuple[str, str]:
    if candidate.get("candidate_type") == "CORRECTION":
        return "REJECT", "Corrections require an explicit human correction."
    if candidate.get("confidentiality_review") != "PASS_NO_SOURCE_VALUES":
        return "REJECT", "Candidate did not pass confidentiality review."
    if candidate.get("proposed_action") not in {"CREATE", "UPDATE_EXISTING"}:
        return "REJECT", "Candidate has no approved create or update action."
    if candidate.get("confidence") not in {"HIGH", "MEDIUM"}:
        return "REJECT", "Candidate confidence is insufficient for autonomous learning."
    if candidate.get("reusable_scope") in {"TRIVIAL_FIELD_CATALOGUE", "FIELD_CATALOGUE"}:
        return "REJECT", "Candidate is a trivial field catalogue entry."
    if not candidate.get("dataset_context") or not candidate.get("observation") or not candidate.get("evidence"):
        return "REJECT", "Candidate lacks contextual reusable evidence."
    if candidate.get("proposed_action") == "UPDATE_EXISTING":
        return "MERGE", "Equivalent approved knowledge is strengthened rather than duplicated."
    return "KEEP", "Candidate is confidentiality-safe, contextual, and reusable."


def _candidate_set_hash(candidates: dict[str, Any]) -> str:
    from .knowledge_learning import reviewed_candidate_set_hash

    return reviewed_candidate_set_hash(candidates)
