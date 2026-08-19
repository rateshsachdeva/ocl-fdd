"""AI-understanding + deterministic-Python orchestration for data preparation.

Python profiles, validates, executes, reconciles and publishes. The active AI
host interprets the current source evidence and authors Dataset Map / Processing
Plan artifacts. No model-provider API is called from this package.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

from .approval_questions import apply_user_decisions, persist_user_decisions, unresolved_blocking_questions, validate_approval_questions
from .autonomous_approval import AI_HOST_APPROVER, evaluate_processing_approval
from .dataset_map import validate_dataset_map, write_dataset_map_review
from .discovery import discover_source_files
from .executor import execute_processing_plan
from .fast_path import assess_profile_complexity, compact_evidence_package
from .metadata import publish_databook_metadata
from .processing_plan import approve_plan, build_source_snapshot, prepare_plan, validate_processing_plan, write_processing_plan_review
from .profiler import profile_directory
from .source_provider import LocalFolderSourceProvider

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_DIRECTORY = REPOSITORY_ROOT / "references" / "source"
DEFAULT_WORK_ROOT = REPOSITORY_ROOT / "work" / "runs"
DEFAULT_OUTPUT_ROOT = REPOSITORY_ROOT / "output"
APPROVAL_MODES = {"AUTONOMOUS", "REVIEW"}

WORKFLOW_STATES = {
    "STARTED", "PROFILE_COMPLETE", "AWAITING_DATASET_UNDERSTANDING", "AWAITING_AI_PLANNING",
    "DATASET_MAP_COMPLETE", "AWAITING_PROCESSING_PLAN", "AWAITING_APPROVAL_QUESTIONS",
    "PROCESSING_PLAN_COMPLETE", "AWAITING_USER_DECISIONS", "AWAITING_USER_APPROVAL",
    "APPROVED", "EXECUTING", "COMPLETED", "COMPLETED_WITH_WARNINGS", "FAILED_VALIDATION", "FAILED",
}
TERMINAL_STATES = {"COMPLETED", "COMPLETED_WITH_WARNINGS", "FAILED_VALIDATION", "FAILED"}


class WorkflowError(RuntimeError):
    pass


def run_databook(
    source_directory: Path | str | None = None,
    work_root: Path | str | None = None,
    output_root: Path | str | None = None,
    *,
    force_new: bool = False,
    approval_mode: str = "AUTONOMOUS",
    audit_artifacts: bool = False,
) -> dict[str, Any]:
    approval_mode = str(approval_mode).upper()
    if approval_mode not in APPROVAL_MODES:
        raise WorkflowError(f"approval_mode must be one of {sorted(APPROVAL_MODES)}.")
    source_directory = _repository_path(source_directory, DEFAULT_SOURCE_DIRECTORY)
    work_root = _repository_path(work_root, DEFAULT_WORK_ROOT)
    output_root = _repository_path(output_root, DEFAULT_OUTPUT_ROOT)
    output_root.mkdir(parents=True, exist_ok=True)
    fingerprint, snapshot = source_fingerprint(source_directory)
    if not snapshot:
        raise WorkflowError("No supported Excel source files were found.")
    workflow_directory, state = _find_or_create_workflow(work_root, fingerprint, snapshot, force_new, approval_mode)
    _advance_workflow(workflow_directory, state, source_directory, output_root, audit_artifacts)
    return _status_response(_read_state(workflow_directory), workflow_directory, output_root)


def get_databook_status(source_directory=None, work_root=None, output_root=None) -> dict[str, Any]:
    source_directory = _repository_path(source_directory, DEFAULT_SOURCE_DIRECTORY)
    work_root = _repository_path(work_root, DEFAULT_WORK_ROOT)
    output_root = _repository_path(output_root, DEFAULT_OUTPUT_ROOT)
    fingerprint, _ = source_fingerprint(source_directory)
    workflow = _find_existing_workflow(work_root, fingerprint)
    if workflow is None:
        return _status_response({"run_id": None, "state": "NOT_STARTED"}, None, output_root)
    return _status_response(workflow[1], workflow[0], output_root)


def record_workflow_user_decisions(workflow_directory: Path, responses: list[dict[str, Any]]) -> dict[str, Any]:
    workflow_directory = Path(workflow_directory)
    questions = _read_json(workflow_directory / "approval_questions.json")
    return persist_user_decisions(questions, responses, workflow_directory / "user_decisions.json")


def source_fingerprint(source_directory: Path) -> tuple[str, list[dict[str, Any]]]:
    root = Path(source_directory).resolve()
    files = discover_source_files(LocalFolderSourceProvider(root))
    snapshot = [
        {"source_id": source.source_id, "filename": source.filename,
         "relative_path": source.path.resolve().relative_to(root).as_posix(),
         "extension": source.extension, "sha256": source.sha256}
        for source in files
    ]
    encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest(), snapshot


def _find_or_create_workflow(work_root, fingerprint, snapshot, force_new, approval_mode):
    work_root = Path(work_root); work_root.mkdir(parents=True, exist_ok=True)
    if not force_new:
        candidates = []
        for state_path in work_root.glob("RUN_*/workflow_state.json"):
            state = _read_json(state_path)
            if state.get("source_fingerprint") == fingerprint and state.get("state") not in TERMINAL_STATES and state.get("approval_mode") == approval_mode:
                candidates.append((state_path.parent, state))
        if candidates:
            return sorted(candidates, key=lambda item: item[1].get("updated_at", ""), reverse=True)[0]
    run_id = _new_run_id(fingerprint, work_root)
    workflow_directory = work_root / run_id; workflow_directory.mkdir(parents=True, exist_ok=False)
    now = datetime.now(timezone.utc).isoformat()
    state = {"run_id": run_id, "state": "STARTED", "source_fingerprint": fingerprint,
             "source_snapshot": snapshot, "approval_mode": approval_mode, "created_at": now,
             "updated_at": now, "history": [{"state": "STARTED", "at": now, "message": "Workflow created."}]}
    _write_state(workflow_directory, state)
    return workflow_directory, state


def _find_existing_workflow(work_root: Path, fingerprint: str):
    if not Path(work_root).exists(): return None
    candidates = []
    for state_path in Path(work_root).glob("RUN_*/workflow_state.json"):
        state = _read_json(state_path)
        if state.get("source_fingerprint") == fingerprint: candidates.append((state_path.parent, state))
    return sorted(candidates, key=lambda item: item[1].get("updated_at", ""), reverse=True)[0] if candidates else None


def _advance_workflow(workflow_directory, state, source_directory, output_root, audit_artifacts):
    while True:
        current = state["state"]
        if current in TERMINAL_STATES:
            return
        if current == "STARTED":
            _run_profile(workflow_directory, state, source_directory, audit_artifacts)
            if state["state"] == "FAILED": return
            continue
        if current == "PROFILE_COMPLETE":
            if state.get("workflow_mode") == "FAST_PATH":
                _write_fast_path_request(workflow_directory, state, source_directory)
                _set_state(workflow_directory, state, "AWAITING_AI_PLANNING", "AI host must understand the profiled package and create the Dataset Map, Processing Plan and approval-question artifact.")
            else:
                _write_dataset_understanding_request(workflow_directory, state)
                _set_state(workflow_directory, state, "AWAITING_DATASET_UNDERSTANDING", "AI host must create the Dataset Map from current source evidence.")
            return
        if current == "AWAITING_AI_PLANNING":
            required = [workflow_directory / "dataset_map.json", workflow_directory / "processing_plan.json", workflow_directory / "approval_questions.json"]
            if not all(path.exists() for path in required): return
            artifacts = _validate_dataset_artifact(workflow_directory, state, audit_artifacts)
            if artifacts is None: return
            profile, dataset_map = artifacts
            plan = _prepare_validate_plan(workflow_directory, state, profile, dataset_map, source_directory, audit_artifacts)
            if plan is None: return
            questions = _read_json(workflow_directory / "approval_questions.json")
            errors = validate_approval_questions(questions, state["run_id"], plan)
            if errors: return _fail(workflow_directory, state, "Approval-question artifact validation failed.", errors)
            _set_state(workflow_directory, state, "PROCESSING_PLAN_COMPLETE", "AI understanding and source-bound Processing Plan validated.")
            continue
        if current == "AWAITING_DATASET_UNDERSTANDING":
            if not (workflow_directory / "dataset_map.json").exists(): return
            if _validate_dataset_artifact(workflow_directory, state, audit_artifacts) is None: return
            _set_state(workflow_directory, state, "DATASET_MAP_COMPLETE", "Dataset Map validated.")
            continue
        if current == "DATASET_MAP_COMPLETE":
            _write_processing_plan_request(workflow_directory, state, source_directory)
            _set_state(workflow_directory, state, "AWAITING_PROCESSING_PLAN", "AI host must create the deterministic Processing Plan.")
            return
        if current == "AWAITING_PROCESSING_PLAN":
            if not (workflow_directory / "processing_plan.json").exists(): return
            profile = _read_json(_artifact_path(workflow_directory, state, "profile_path"))
            dataset_map = _read_json(workflow_directory / "dataset_map.json")
            if _prepare_validate_plan(workflow_directory, state, profile, dataset_map, source_directory, audit_artifacts) is None: return
            _set_state(workflow_directory, state, "AWAITING_APPROVAL_QUESTIONS", "Processing Plan validated; AI host must classify any genuine material questions.")
            _write_approval_questions_request(workflow_directory, state)
            return
        if current == "AWAITING_APPROVAL_QUESTIONS":
            questions_path = workflow_directory / "approval_questions.json"
            if not questions_path.exists(): return
            plan = _read_json(workflow_directory / "processing_plan.json")
            errors = validate_approval_questions(_read_json(questions_path), state["run_id"], plan)
            if errors: return _fail(workflow_directory, state, "Approval-question artifact validation failed.", errors)
            _set_state(workflow_directory, state, "PROCESSING_PLAN_COMPLETE", "Approval-question classification validated.")
            continue
        if current in {"PROCESSING_PLAN_COMPLETE", "AWAITING_USER_DECISIONS", "AWAITING_USER_APPROVAL"}:
            plan_path = workflow_directory / "processing_plan.json"; plan = _read_json(plan_path)
            questions_path = workflow_directory / "approval_questions.json"
            if not questions_path.exists():
                _write_approval_questions_request(workflow_directory, state)
                _set_state(workflow_directory, state, "AWAITING_APPROVAL_QUESTIONS", "AI host must classify material approval questions.")
                return
            questions = _read_json(questions_path)
            errors = validate_approval_questions(questions, state["run_id"], plan)
            if errors: return _fail(workflow_directory, state, "Approval-question artifact validation failed.", errors)
            decisions_path = workflow_directory / "user_decisions.json"
            if decisions_path.exists(): questions = apply_user_decisions(questions, _read_json(decisions_path))
            if unresolved_blocking_questions(questions):
                _set_state(workflow_directory, state, "AWAITING_USER_DECISIONS", "Genuine material user decisions remain unresolved.")
                return
            if plan.get("plan_metadata", {}).get("status") == "APPROVED":
                _set_state(workflow_directory, state, "APPROVED", "Existing exact approved plan detected."); continue
            if state.get("approval_mode") == "AUTONOMOUS":
                profile = _read_json(_artifact_path(workflow_directory, state, "profile_path")); dataset_map = _read_json(workflow_directory / "dataset_map.json")
                audit = evaluate_processing_approval(plan, profile, dataset_map, questions, str(source_directory))
                _write_json(workflow_directory / "processing_approval_audit.json", audit)
                if audit["decision"] == "APPROVE":
                    approved = approve_plan(plan, plan_id=plan["plan_metadata"]["plan_id"], plan_version=plan["plan_metadata"]["plan_version"], plan_hash=plan["plan_metadata"]["plan_hash"], approver_note=audit.get("approval_rationale"), approver_type=AI_HOST_APPROVER, approval_policy_version=audit["approval_policy_version"], approval_audit=audit)
                    _write_json(plan_path, approved); _set_state(workflow_directory, state, "APPROVED", "Autonomous policy approved the exact validated plan."); continue
                state["human_escalation"] = audit
            _set_state(workflow_directory, state, "AWAITING_USER_APPROVAL", "Plan requires a genuine human approval/escalation.")
            return
        if current == "APPROVED":
            _set_state(workflow_directory, state, "EXECUTING", "Starting deterministic execution."); continue
        if current == "EXECUTING":
            result = execute_processing_plan(workflow_directory / "processing_plan.json", _artifact_path(workflow_directory, state, "profile_path"), workflow_directory / "dataset_map.json", source_directory, Path(output_root) / "runs", staging_directory=(workflow_directory / "staging") if (workflow_directory / "staging").exists() else None, audit_artifacts=audit_artifacts)
            manifest = result["manifest"]
            state["execution_id"] = result["execution_id"]
            state["execution_directory"] = str(result["execution_directory"])
            state["execution_manifest"] = str(result["execution_directory"] / "execution_manifest.json")
            final_state = manifest["final_execution_status"]
            if final_state in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}:
                _publish_latest(result["execution_directory"], Path(output_root), manifest["outputs_created"], workflow_directory / "databook_metadata.json")
            if final_state not in WORKFLOW_STATES: final_state = "FAILED"
            _set_state(workflow_directory, state, final_state, f"Execution completed with status {final_state}.")
            return
        return


def _run_profile(workflow_directory, state, source_directory, audit_artifacts):
    result = profile_directory(source_directory, workflow_directory, generate_review=audit_artifacts, staging_directory=workflow_directory / "staging")
    fingerprint_after, _ = source_fingerprint(source_directory)
    if fingerprint_after != state["source_fingerprint"]: return _fail(workflow_directory, state, "Source package changed during profiling.", [])
    state["profile_run_id"] = result.run_id
    state["profile_path"] = str((result.run_directory / "profile.json").relative_to(workflow_directory))
    if result.failed_count: return _fail(workflow_directory, state, "One or more workbooks failed deterministic profiling.", [str(result.failed_count)])
    profile = _read_json(result.run_directory / "profile.json")
    tabular = [region for wb in profile.get("workbook_profiles", []) for ws in wb.get("worksheet_profiles", []) for region in ws.get("data_regions", []) if region.get("candidate_confidence") == "TABULAR_CANDIDATE"]
    if not tabular: return _fail(workflow_directory, state, "No tabular source region could be structurally profiled.", [])
    routing = assess_profile_complexity(profile)
    state["workflow_mode"] = routing["workflow_mode"]; state["complexity_assessment"] = routing
    _set_state(workflow_directory, state, "PROFILE_COMPLETE", "Deterministic profiling completed.")


def _validate_dataset_artifact(workflow_directory, state, audit_artifacts):
    profile = _read_json(_artifact_path(workflow_directory, state, "profile_path")); dataset_map = _read_json(workflow_directory / "dataset_map.json")
    errors = validate_dataset_map(dataset_map, profile)
    if errors: _fail(workflow_directory, state, "Dataset Map validation failed.", errors); return None
    if audit_artifacts: write_dataset_map_review(dataset_map, workflow_directory / "dataset_map_review.xlsx")
    publish_databook_metadata(dataset_map, state["run_id"], workflow_directory / "databook_metadata.json")
    return profile, dataset_map


def _prepare_validate_plan(workflow_directory, state, profile, dataset_map, source_directory, audit_artifacts):
    plan_path = workflow_directory / "processing_plan.json"; plan = _read_json(plan_path)
    metadata = plan.setdefault("plan_metadata", {})
    if not metadata.get("source_snapshot"): metadata["source_snapshot"] = build_source_snapshot(profile, source_directory)
    if metadata.get("status") != "APPROVED":
        metadata.setdefault("status", "PLAN_DRAFTED")
        plan = prepare_plan(plan); _write_json(plan_path, plan)
    errors = validate_processing_plan(plan, profile, dataset_map)
    if errors: _fail(workflow_directory, state, "Processing Plan validation failed.", errors); return None
    if audit_artifacts: write_processing_plan_review(plan, workflow_directory / "processing_plan_review.xlsx")
    return plan


def _write_fast_path_request(workflow_directory, state, source_directory):
    profile_path = _artifact_path(workflow_directory, state, "profile_path").resolve(); profile = _read_json(profile_path)
    payload = {"task": "FAST_PATH_DATASET_UNDERSTANDING_AND_PROCESSING_PLAN", "workflow_run_id": state["run_id"], "workflow_mode": "FAST_PATH", "profile_path": str(profile_path), "evidence_package": compact_evidence_package(profile), "instructions": str(REPOSITORY_ROOT / "instructions" / "AI_HOST_ORCHESTRATION.md"), "dataset_understanding_instructions": str(REPOSITORY_ROOT / "instructions" / "dataset_understanding.md"), "processing_plan_instructions": str(REPOSITORY_ROOT / "instructions" / "processing_plan.md"), "dataset_map_schema": str(REPOSITORY_ROOT / "schemas" / "dataset_map.schema.json"), "processing_plan_schema": str(REPOSITORY_ROOT / "schemas" / "processing_plan.schema.json"), "approval_questions_schema": str(REPOSITORY_ROOT / "schemas" / "approval_questions.schema.json"), "source_snapshot": build_source_snapshot(profile, source_directory), "targets": {"dataset_map": str((workflow_directory / "dataset_map.json").resolve()), "processing_plan": str((workflow_directory / "processing_plan.json").resolve()), "approval_questions": str((workflow_directory / "approval_questions.json").resolve())}, "stable_field_id_rule": "Use profile field_id values as deterministic source keys; displayed headers are evidence only.", "targeted_inspection": "Use fdd_data.inspection.inspect_source only for a specific unresolved ambiguity.", "next_action": "Create all three target artifacts in one reasoning cycle, validate them, then resume the root workflow."}
    _write_json(workflow_directory / "ai_tasks" / "fast_path_planning_request.json", payload)


def _write_dataset_understanding_request(workflow_directory, state):
    payload = {"task": "DATASET_UNDERSTANDING", "workflow_run_id": state["run_id"], "profile_path": str(_artifact_path(workflow_directory, state, "profile_path").resolve()), "instructions": str(REPOSITORY_ROOT / "instructions" / "dataset_understanding.md"), "dataset_map_schema": str(REPOSITORY_ROOT / "schemas" / "dataset_map.schema.json"), "target_dataset_map_path": str((workflow_directory / "dataset_map.json").resolve()), "targeted_inspection": "fdd_data.inspection.inspect_source", "next_action": "Create dataset_map.json, validate it, then resume the root workflow."}
    _write_json(workflow_directory / "ai_tasks" / "dataset_understanding_request.json", payload)


def _write_processing_plan_request(workflow_directory, state, source_directory):
    profile = _read_json(_artifact_path(workflow_directory, state, "profile_path"))
    payload = {"task": "PROCESSING_PLAN", "workflow_run_id": state["run_id"], "profile_path": str(_artifact_path(workflow_directory, state, "profile_path").resolve()), "dataset_map_path": str((workflow_directory / "dataset_map.json").resolve()), "instructions": str(REPOSITORY_ROOT / "instructions" / "processing_plan.md"), "processing_plan_schema": str(REPOSITORY_ROOT / "schemas" / "processing_plan.schema.json"), "source_snapshot": build_source_snapshot(profile, source_directory), "target_processing_plan_path": str((workflow_directory / "processing_plan.json").resolve()), "next_action": "Create the source-bound deterministic processing_plan.json, then resume the root workflow."}
    _write_json(workflow_directory / "ai_tasks" / "processing_plan_request.json", payload)


def _write_approval_questions_request(workflow_directory, state):
    plan = _read_json(workflow_directory / "processing_plan.json")
    payload = {"task": "APPROVAL_QUESTIONS", "workflow_run_id": state["run_id"], "dataset_map_path": str((workflow_directory / "dataset_map.json").resolve()), "processing_plan_path": str((workflow_directory / "processing_plan.json").resolve()), "target_approval_questions_path": str((workflow_directory / "approval_questions.json").resolve()), "plan_id": plan["plan_metadata"]["plan_id"], "plan_version": plan["plan_metadata"]["plan_version"], "instructions": str(REPOSITORY_ROOT / "instructions" / "approval_questions.md"), "approval_questions_schema": str(REPOSITORY_ROOT / "schemas" / "approval_questions.schema.json"), "next_action": "Create approval_questions.json; ask a human only for genuine unresolved material decisions."}
    _write_json(workflow_directory / "ai_tasks" / "approval_questions_request.json", payload)


def _publish_latest(execution_directory, output_root, output_files, metadata_source):
    latest, temporary = Path(output_root) / "latest", Path(output_root) / "latest_pending"
    if temporary.exists(): shutil.rmtree(temporary)
    temporary.mkdir(parents=True, exist_ok=False)
    for filename in output_files: shutil.copy2(Path(execution_directory) / filename, temporary / filename)
    for filename in ("execution_review.xlsx", "execution_manifest.json", "lineage.csv", "field_lineage.csv", "exclusions.csv", "processing_issues.csv"):
        source = Path(execution_directory) / filename
        if source.exists(): shutil.copy2(source, temporary / filename)
    if Path(metadata_source).exists(): shutil.copy2(metadata_source, temporary / "databook_metadata.json")
    if latest.exists(): shutil.rmtree(latest)
    temporary.rename(latest)


def _status_response(state, workflow_directory, output_root):
    response = deepcopy(state)
    current = state.get("state", "NOT_STARTED")
    next_actor, next_action, handoff, required = "NONE", "STOP", None, []
    instruction = REPOSITORY_ROOT / "instructions" / "AI_HOST_ORCHESTRATION.md"
    if current in {"STARTED", "PROFILE_COMPLETE", "DATASET_MAP_COMPLETE", "PROCESSING_PLAN_COMPLETE", "APPROVED", "EXECUTING"}: next_actor, next_action = "PYTHON", "CONTINUE"
    elif current == "AWAITING_AI_PLANNING": next_actor, next_action, handoff, required = "AI_HOST", "UNDERSTAND_AND_PLAN", workflow_directory / "ai_tasks" / "fast_path_planning_request.json", [workflow_directory / "dataset_map.json", workflow_directory / "processing_plan.json", workflow_directory / "approval_questions.json"]
    elif current == "AWAITING_DATASET_UNDERSTANDING": next_actor, next_action, handoff, required = "AI_HOST", "DATASET_UNDERSTANDING", workflow_directory / "ai_tasks" / "dataset_understanding_request.json", [workflow_directory / "dataset_map.json"]
    elif current == "AWAITING_PROCESSING_PLAN": next_actor, next_action, handoff, required = "AI_HOST", "PROCESSING_PLAN", workflow_directory / "ai_tasks" / "processing_plan_request.json", [workflow_directory / "processing_plan.json"]
    elif current == "AWAITING_APPROVAL_QUESTIONS": next_actor, next_action, handoff, required = "AI_HOST", "CLASSIFY_APPROVAL_QUESTIONS", workflow_directory / "ai_tasks" / "approval_questions_request.json", [workflow_directory / "approval_questions.json"]
    elif current in {"AWAITING_USER_DECISIONS", "AWAITING_USER_APPROVAL"}: next_actor, next_action, handoff = "HUMAN", "RESOLVE_MATERIAL_DECISION", workflow_directory / "approval_questions.json"
    elif current in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}: handoff = Path(output_root) / "latest"
    response.update({"next_actor": next_actor, "must_continue": next_actor in {"PYTHON", "AI_HOST"}, "next_action": next_action, "handoff_path": str(handoff.resolve()) if handoff else None, "relevant_instruction": str(instruction.resolve()), "required_artifacts": [str(path.resolve()) for path in required], "resume_command": "python run_all.py"})
    response["workflow_directory"] = str(workflow_directory.resolve()) if workflow_directory else None
    return response


def _new_run_id(fingerprint, work_root):
    base = f"RUN_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{fingerprint[:8]}"; candidate, suffix = base, 1
    while (Path(work_root) / candidate).exists(): suffix += 1; candidate = f"{base}_{suffix:02d}"
    return candidate


def _set_state(workflow_directory, state, new_state, message):
    if new_state not in WORKFLOW_STATES: raise WorkflowError(f"Unknown workflow state: {new_state}")
    state["state"] = new_state; state["updated_at"] = datetime.now(timezone.utc).isoformat(); state.setdefault("history", []).append({"state": new_state, "at": state["updated_at"], "message": message}); _write_state(workflow_directory, state)


def _fail(workflow_directory, state, message, errors):
    state["errors"] = errors; _set_state(workflow_directory, state, "FAILED", message)


def _artifact_path(workflow_directory, state, key): return workflow_directory / state[key]
def _repository_path(path, default):
    candidate = default if path is None else Path(path)
    if not candidate.is_absolute(): candidate = REPOSITORY_ROOT / candidate
    return candidate.resolve()
def _write_state(workflow_directory, state): _write_json(workflow_directory / "workflow_state.json", state)
def _read_state(workflow_directory): return _read_json(workflow_directory / "workflow_state.json")
def _write_json(path, payload): Path(path).parent.mkdir(parents=True, exist_ok=True); Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
def _read_json(path): return json.loads(Path(path).read_text(encoding="utf-8"))

__all__ = ["WORKFLOW_STATES", "WorkflowError", "get_databook_status", "record_workflow_user_decisions", "run_databook", "source_fingerprint"]
