"""Bridge from the OCL skill to the full AI+Python fdd-data-preparation workflow.

This module deliberately does not interpret raw Excel.  The embedded full
``fdd-data-preparation`` runtime owns raw-source discovery, profiling, AI-host
Dataset Map / Processing Plan checkpoints, deterministic execution,
completeness, lineage and publication.  OCL starts only after a publishable
standardized package exists.
"""
from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PUBLISHABLE_STATUSES = {"COMPLETED", "COMPLETED_WITH_WARNINGS"}


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

    The function may return an ``AI_HOST`` or ``HUMAN`` coordination checkpoint.
    A coding-agent host should satisfy AI-host checkpoints using the exact
    instruction/handoff paths returned by the upstream workflow, then rerun the
    top-level OCL command.  Python never substitutes a header-guessing parser for
    that reasoning step.
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
    coordination = status.get("coordination") if isinstance(status.get("coordination"), dict) else {}
    run_id = status.get("run_id")
    latest = output_root / "latest"
    manifest = _read_json(latest / "execution_manifest.json")
    published_status = str(manifest.get("final_execution_status") or "")
    standardized_output = latest if latest.is_dir() and published_status in PUBLISHABLE_STATUSES else None

    warnings: list[str] = []
    if published_status == "COMPLETED_WITH_WARNINGS":
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
        actor = str(coordination.get("next_actor") or "").upper()
        bridge_state = f"DATA_PREP_AWAITING_{actor}" if actor else f"DATA_PREP_{upstream_state}"

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
