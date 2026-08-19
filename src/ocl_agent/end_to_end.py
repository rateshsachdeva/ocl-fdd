"""Single-repository end-to-end OCL workflow.

Raw Excel is understood and standardized by the embedded full data-preparation
state machine. OCL starts only from its published long/flat package.
"""
from __future__ import annotations

import importlib
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from ocl_agent.config import RepoPaths
from ocl_agent.final_qa import validate_final_databook
from ocl_agent.part1_databook.run import Part1Result, run_part1
from ocl_agent.part2_analysis.run import run_analysis
from ocl_agent.part3_qanda.run import run_qanda
from ocl_agent.part4_report.run import run_report
from ocl_agent.workbook_style import apply_workbook_style


@dataclass(frozen=True)
class EndToEndResult:
    state: str
    data_prep_output: Path | None = None
    data_prep_state: str | None = None
    part1: Part1Result | None = None
    databook: Path | None = None
    report: Path | None = None
    findings: int = 0
    questions: int = 0
    qa: dict | None = None
    warnings: tuple[str, ...] = ()
    next_actor: str = "NONE"
    next_action: str | None = None
    handoff_path: Path | None = None
    relevant_instruction: Path | None = None
    required_artifacts: tuple[Path, ...] = ()
    runtime_config: Path | None = None


def run_end_to_end(
    paths: RepoPaths,
    *,
    data_prep_output: Path | None = None,
    part1_only: bool = False,
    skip_report: bool = False,
) -> EndToEndResult:
    runtime_work = paths.output.parent / "work"

    if data_prep_output is None:
        prep_status = _run_full_data_prep(paths.root, paths.source, runtime_work / "data_prep")
        prep_state = str(prep_status.get("state") or "FAILED")
        if prep_state not in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}:
            return EndToEndResult(
                state=f"DATA_PREP_{prep_state}",
                data_prep_state=prep_state,
                next_actor=str(prep_status.get("next_actor") or "NONE"),
                next_action=prep_status.get("next_action"),
                handoff_path=_optional_path(prep_status.get("handoff_path")),
                relevant_instruction=_optional_path(prep_status.get("relevant_instruction")),
                required_artifacts=tuple(Path(item) for item in prep_status.get("required_artifacts", []) if item),
            )
        data_prep_output = _optional_path(prep_status.get("handoff_path"))
        if data_prep_output is None or not data_prep_output.is_dir():
            raise RuntimeError("Data preparation completed but did not publish output/latest.")
        warnings = _publication_warnings(data_prep_output)
    else:
        data_prep_output = Path(data_prep_output).resolve()
        prep_state = "EXTERNAL_PUBLISHED_PACKAGE"
        warnings = ()

    package_id = _package_id(data_prep_output)
    runtime_config = _prepare_runtime_config(paths.config, runtime_work / "ocl_config" / package_id)
    part1 = run_part1(data_prep_output, runtime_config, paths.output)

    if part1.state != "DATABOOK_READY" or not part1.databook or not part1.build:
        action, handoff, required = _ocl_handoff(part1, runtime_config)
        return EndToEndResult(
            state=part1.state,
            data_prep_output=data_prep_output,
            data_prep_state=prep_state,
            part1=part1,
            warnings=warnings,
            next_actor="AI_HOST" if part1.state in {"AWAITING_SEMANTIC_HANDOFF", "AWAITING_JUDGMENT_REVIEW", "AWAITING_CONTROL_ALIGNMENT"} else "NONE",
            next_action=action,
            handoff_path=handoff,
            relevant_instruction=paths.root / "src" / "ocl_agent" / "llm" / "README.md",
            required_artifacts=required,
            runtime_config=runtime_config,
        )

    qa_path = runtime_work / "final_qa.json"
    if part1_only:
        apply_workbook_style(part1.databook)
        qa = validate_final_databook(part1.databook, qa_path)
        return EndToEndResult(
            "DATABOOK_READY", data_prep_output, prep_state, part1=part1,
            databook=part1.databook, qa=qa, warnings=warnings, runtime_config=runtime_config,
        )

    analysis = run_analysis(part1.build.records, part1.databook, package=part1.package, handoff=part1.handoff)
    questions = run_qanda(analysis, part1.databook)
    apply_workbook_style(part1.databook)
    qa = validate_final_databook(part1.databook, qa_path)
    report = None if skip_report else run_report(analysis, questions, paths.output)
    return EndToEndResult(
        "READY", data_prep_output, prep_state, part1=part1, databook=part1.databook,
        report=report, findings=len(analysis.findings), questions=len(questions), qa=qa,
        warnings=warnings, runtime_config=runtime_config,
    )


def _run_full_data_prep(repo_root: Path, source_dir: Path, work_root: Path) -> dict:
    embedded_src = repo_root / "fdd-data-preparation" / "src"
    if not embedded_src.is_dir():
        raise FileNotFoundError("Embedded fdd-data-preparation runtime is missing from the repository.")
    text = str(embedded_src)
    if text not in sys.path:
        sys.path.insert(0, text)
    module = importlib.import_module("fdd_data.orchestration")
    runs_root = work_root / "runs"
    output_root = work_root / "output"

    # Once this exact source package has been prepared successfully, reuse its
    # publication while OCL works through its own AI review checkpoints. A new
    # data-prep run is needed only when the source fingerprint changes.
    status = module.get_databook_status(
        source_directory=source_dir,
        work_root=runs_root,
        output_root=output_root,
    )
    if status.get("state") in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}:
        published = _optional_path(status.get("handoff_path"))
        if published is not None and published.is_dir():
            return status

    return module.run_databook(
        source_directory=source_dir,
        work_root=runs_root,
        output_root=output_root,
        approval_mode="AUTONOMOUS",
        audit_artifacts=False,
    )


def _prepare_runtime_config(human_config: Path, runtime_config: Path) -> Path:
    """Create a package-specific working config once, then preserve AI review work."""
    human_config, runtime_config = Path(human_config), Path(runtime_config)
    if runtime_config.exists():
        return runtime_config
    runtime_config.mkdir(parents=True, exist_ok=True)
    if human_config.exists():
        for path in human_config.iterdir():
            if path.is_file() and path.name != ".gitkeep":
                shutil.copy2(path, runtime_config / path.name)
    return runtime_config


def _package_id(root: Path) -> str:
    for filename, key in (("execution_manifest.json", "execution_id"), ("databook_metadata.json", "workflow_run_id")):
        path = Path(root) / filename
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and payload.get(key):
                return _safe_name(str(payload[key]))
    return _safe_name(Path(root).name)


def _publication_warnings(root: Path) -> tuple[str, ...]:
    path = Path(root) / "execution_manifest.json"
    if not path.exists():
        return ()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return tuple(str(item) for item in payload.get("warnings", []) if item)


def _ocl_handoff(part1: Part1Result, runtime_config: Path) -> tuple[str, Path | None, tuple[Path, ...]]:
    if part1.state == "AWAITING_SEMANTIC_HANDOFF":
        return (
            "OCL_SEMANTIC_HANDOFF",
            part1.handoff_draft or part1.input_review,
            (runtime_config / "semantic_handoff.json",),
        )
    if part1.state == "AWAITING_JUDGMENT_REVIEW":
        return (
            "OCL_JUDGMENT_REVIEW",
            part1.review_context or part1.semantic_review,
            (runtime_config / "judgment_scope.csv", runtime_config / "mapping.csv", runtime_config / "judgment_wc_debt.csv"),
        )
    if part1.state == "AWAITING_CONTROL_ALIGNMENT":
        return ("OCL_CONTROL_REVIEW", part1.semantic_review, ())
    return ("STOP", None, ())


def _optional_path(value) -> Path | None:
    return Path(value).resolve() if value else None


def _safe_name(value: str) -> str:
    return "".join(character if character.isalnum() or character in "-_" else "_" for character in value)[:80] or "package"
