"""Bridge from the OCL skill to the full AI+Python fdd-data-preparation workflow.

This module deliberately does not interpret raw Excel. The embedded full
``fdd-data-preparation`` runtime owns raw-source discovery, profiling, AI-host
Dataset Map / Processing Plan checkpoints, deterministic execution,
completeness, lineage and publication. OCL starts only after a publishable
standardized package exists.
"""
from __future__ import annotations

import hashlib
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
    source_fingerprint: str | None = None
    coordination: dict[str, Any] = field(default_factory=dict)
    raw_status: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return self.standardized_output is not None


def source_package_fingerprint(source_dir: Path) -> str:
    """Fingerprint the exact current source package by relative path and bytes.

    The outer OCL workflow uses this fingerprint before the embedded data-prep
    runtime is allowed to inspect any previous run state. Therefore adding,
    removing, renaming or changing a source file creates a distinct upstream
    workspace even if the embedded runtime itself would otherwise resume an old
    run. Office lock files are ignored because they are not client source data.
    """
    source_dir = Path(source_dir).resolve()
    digest = hashlib.sha256()
    files = sorted(
        (
            path
            for path in source_dir.rglob("*")
            if path.is_file() and not path.name.startswith("~$")
        ),
        key=lambda path: path.relative_to(source_dir).as_posix().casefold(),
    ) if source_dir.exists() else []

    digest.update(f"files:{len(files)}\n".encode("utf-8"))
    for path in files:
        relative = path.relative_to(source_dir).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(path.stat().st_size).encode("ascii"))
        digest.update(b"\0")
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\n")
    return digest.hexdigest()


def run_full_data_preparation(repo_root: Path, source_dir: Path, work_root: Path) -> DataPrepBridgeResult:
    """Advance the full data-preparation workflow by one deterministic/AI-host turn.

    Each distinct set of files in ``references/source`` receives its own
    ``source_packages/<fingerprint>/`` runs and output directories. This outer
    isolation is deliberately stronger than relying only on an upstream run ID:
    old workflow state is never visible to a newly changed source package.

    Within that source-specific workspace, ``output/latest`` is reusable only
    when its execution ID matches the current upstream execution.
    """
    repo_root = Path(repo_root).resolve()
    source_dir = Path(source_dir).resolve()
    work_root = Path(work_root).resolve()

    source_fingerprint = source_package_fingerprint(source_dir)
    source_package_root = work_root / "source_packages" / source_fingerprint[:16]
    runs_root = source_package_root / "runs"
    output_root = source_package_root / "output"
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
    coordination.setdefault("source_fingerprint", source_fingerprint)
    coordination.setdefault("source_package_root", str(source_package_root))
    run_id = status.get("run_id")
    current_execution_id = str(status.get("execution_id") or "")
    latest = output_root / "latest"
    manifest = _read_json(latest / "execution_manifest.json")
    published_status = str(manifest.get("final_execution_status") or "")
    published_execution_id = str(manifest.get("execution_id") or "")

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
        source_fingerprint=source_fingerprint,
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
