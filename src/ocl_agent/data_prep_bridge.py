"""Bridge from the OCL skill to the full AI+Python fdd-data-preparation workflow.

This module deliberately does not interpret raw Excel. The embedded full
``fdd-data-preparation`` runtime owns raw-source discovery, profiling, AI-host
Dataset Map / Processing Plan checkpoints, deterministic execution,
completeness, lineage and publication. OCL starts only after a publishable
standardized package exists.
"""
from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PUBLISHABLE_STATUSES = {"COMPLETED", "COMPLETED_WITH_WARNINGS"}
COORDINATION_KEYS = (
    "next_actor",
    "must_continue",
    "next_action",
    "handoff_path",
    "relevant_instruction",
    "required_artifact",
    "required_artifacts",
    "resume_command",
    "blocking_question_count",
    "approval_required",
    "interaction_type",
    "question_id",
    "question",
    "reason",
    "options",
    "recommended_option_id",
    "recommendation_reason",
    "allow_other",
    "multi_select",
    "decision_effect",
    "fallback_presentation",
    "workflow_state",
)


@dataclass(frozen=True)
class DataPrepBridgeResult:
    state: str
    upstream_state: str
    work_root: Path
    output_root: Path
    standardized_output: Path | None = None
    run_id: str | None = None
    coordination: dict[str, Any] = field(default_factory=dict)
    raw_status: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return self.standardized_output is not None


def run_full_data_preparation(repo_root: Path, source_dir: Path, work_root: Path) -> DataPrepBridgeResult:
    """Advance the full data-preparation workflow by one deterministic/AI-host turn.

    A coding-agent host should satisfy AI-host checkpoints using the exact
    instruction/handoff paths returned by the upstream workflow, then rerun the
    top-level OCL command. Python never substitutes a header-guessing parser for
    that reasoning step.

    ``output/latest`` is reusable only when its execution ID matches the current
    source-bound workflow. This lets later OCL/AI reruns reuse the same published
    package, while a changed source fingerprint can never silently inherit a
    previous package's output.
    """
    repo_root = Path(repo_root).resolve()
    source_dir = Path(source_dir).resolve()
    work_root = Path(work_root).resolve()
    runs_root = work_root / "runs"
    output_root = work_root / "output"
    runs_root.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)

    bootstrap = _load_bootstrap(repo_root)
    _project, fdd_data = bootstrap.activate_full_runtime()
    status = fdd_data.run_databook(
        source_dir,
        runs_root,
        output_root,
        approval_mode="AUTONOMOUS",
    )
    if not isinstance(status, dict):
        raise RuntimeError("fdd-data-preparation returned an invalid workflow status payload.")

    upstream_state = str(status.get("state") or "UNKNOWN")
    coordination = _coordination_from_status(status)
    run_id = status.get("run_id")
    current_execution_id = str(status.get("execution_id") or "")
    latest = output_root / "latest"
    manifest = _read_json(latest / "execution_manifest.json")
    published_status = str(manifest.get("final_execution_status") or "")
    published_execution_id = str(manifest.get("execution_id") or "")

    # Critical freshness rule. The upstream workflow fingerprints all current
    # source files and creates/resumes the matching workflow. We then bind
    # output/latest to that exact workflow execution ID. A newly changed source
    # package has no matching execution ID until it has been processed, so an old
    # latest folder cannot leak into the new OCL run.
    latest_belongs_to_current_run = bool(
        current_execution_id
        and published_execution_id
        and current_execution_id == published_execution_id
    )
    standardized_output = (
        latest
        if latest_belongs_to_current_run
        and latest.is_dir()
        and published_status in PUBLISHABLE_STATUSES
        else None
    )

    warnings: list[str] = []
    if standardized_output is not None and published_status == "COMPLETED_WITH_WARNINGS":
        warnings.append("fdd-data-preparation published with warnings; see execution_manifest.json and databook_metadata.json.")
    if standardized_output is not None:
        try:
            bootstrap.sync_runtime_knowledge()
        except Exception as error:  # knowledge persistence must never invalidate a published financial package
            warnings.append(f"Reusable knowledge sync warning: {error}")

    if standardized_output is not None:
        bridge_state = "DATA_PREP_READY"
    elif upstream_state == "FAILED":
        bridge_state = "DATA_PREP_FAILED"
    else:
        bridge_state = f"DATA_PREP_{upstream_state}"

    return DataPrepBridgeResult(
        state=bridge_state,
        upstream_state=upstream_state,
        work_root=runs_root,
        output_root=output_root,
        standardized_output=standardized_output,
        run_id=str(run_id) if run_id else None,
        coordination=coordination,
        raw_status=status,
        warnings=tuple(warnings),
    )


def _coordination_from_status(status: dict[str, Any]) -> dict[str, Any]:
    """Support the full upstream contract, which exposes coordination at top level."""
    nested = status.get("coordination")
    result = dict(nested) if isinstance(nested, dict) else {}
    for key in COORDINATION_KEYS:
        if key in status and status[key] is not None:
            result.setdefault(key, status[key])

    actor = str(result.get("next_actor") or "").upper()
    if actor == "AI_HOST":
        # Root OCL orchestration, not the user, owns continuation after the host
        # writes the requested reasoning artifacts.
        result["must_continue"] = True
    result["resume_command"] = "python run_all.py"
    return result


def _load_bootstrap(repo_root: Path):
    path = repo_root / "fdd-data-preparation" / "bootstrap.py"
    if not path.exists():
        raise FileNotFoundError("Full fdd-data-preparation bootstrap is missing from the OCL repository.")
    spec = importlib.util.spec_from_file_location("ocl_embedded_fdd_data_prep_bootstrap", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the embedded fdd-data-preparation bootstrap.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}
