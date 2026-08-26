"""Single-repository end-to-end OCL workflow.

Raw Excel is owned by the full fdd-data-preparation workflow. OCL starts only
from its published standardized package. AI-host checkpoints are surfaced as
explicit coordination instructions rather than replaced with layout-specific
Python guesses.
"""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ocl_agent.config import RepoPaths
from ocl_agent.data_prep_bridge import run_full_data_preparation, source_package_fingerprint
from ocl_agent.final_qa import validate_final_databook
from ocl_agent.part1_databook.run import Part1Result, run_part1
from ocl_agent.part2_analysis.ai_interpretation import (
    AnalysisInterpretationError,
    load_analysis_interpretation,
    write_analysis_request,
)
from ocl_agent.part2_analysis.ai_render import apply_partner_interpretation
from ocl_agent.part2_analysis.pipeline import run_analysis
from ocl_agent.part4_report.run import run_report
from ocl_agent.workbook_style import apply_workbook_style


@dataclass(frozen=True)
class EndToEndResult:
    state: str
    data_prep_output: Path | None = None
    part1: Part1Result | None = None
    databook: Path | None = None
    report: Path | None = None
    findings: int = 0
    questions: int = 0
    qa: dict | None = None
    warnings: tuple[str, ...] = ()
    coordination: dict[str, Any] = field(default_factory=dict)
    runtime_config: Path | None = None


def run_end_to_end(
    paths: RepoPaths,
    *,
    data_prep_output: Path | None = None,
    part1_only: bool = False,
    skip_report: bool = False,
) -> EndToEndResult:
    """Advance raw source -> full data prep -> OCL -> final deliverables."""
    runtime_work = paths.output.parent / "work"
    warnings: list[str] = []
    source_fingerprint: str | None = None

    if data_prep_output is None:
        source_fingerprint = source_package_fingerprint(paths.source)
        _activate_source_package(runtime_work, paths.output, source_fingerprint)

        prep = run_full_data_preparation(paths.root, paths.source, runtime_work / "data_prep")
        if prep.source_fingerprint and prep.source_fingerprint != source_fingerprint:
            raise RuntimeError("Source files changed while the workflow was starting. Rerun after the source folder is stable.")
        warnings.extend(prep.warnings)
        if not prep.ready:
            return EndToEndResult(
                prep.state,
                warnings=tuple(warnings),
                coordination=_normalize_coordination(prep.coordination, prep.raw_status),
            )
        data_prep_output = prep.standardized_output
    else:
        data_prep_output = Path(data_prep_output).resolve()

    assert data_prep_output is not None
    package_id = _package_id(data_prep_output)
    safe_package_id = _safe_name(package_id)
    runtime_config = _prepare_package_config(paths.config, runtime_work / "ocl_config" / safe_package_id)

    part1 = run_part1(data_prep_output, runtime_config, paths.output)
    if part1.state != "DATABOOK_READY" or not part1.databook or not part1.build:
        return EndToEndResult(
            part1.state,
            data_prep_output,
            part1=part1,
            warnings=tuple(warnings),
            coordination=_ocl_coordination(part1, runtime_config, paths.root),
            runtime_config=runtime_config,
        )

    qa_path = runtime_work / "final_qa.json"
    if part1_only:
        apply_workbook_style(part1.databook)
        qa = validate_final_databook(part1.databook, qa_path)
        _mark_source_ready(runtime_work, source_fingerprint, package_id)
        return EndToEndResult(
            "DATABOOK_READY",
            data_prep_output,
            part1=part1,
            databook=part1.databook,
            qa=qa,
            warnings=tuple(warnings),
            runtime_config=runtime_config,
        )

    # Python calculates all metrics and writes the formula-linked analysis layer.
    # Explicit movement records are passed through only when Part 1 validated
    # their source roles/sign rules; missing movement evidence degrades to
    # UNSUPPORTED analysis rather than being inferred from balances.
    analysis = run_analysis(
        part1.build.records,
        part1.databook,
        package=part1.package,
        handoff=part1.handoff,
        movements=part1.movement_build.records if part1.movement_build else (),
    )

    # The active coding AI now performs the qualitative FDD-partner interpretation
    # from a hash-bound evidence package. It writes Deal Issues, Key Findings and
    # management Q&A; Python validates the artifact before rendering it.
    analysis_dir = runtime_work / "analysis" / safe_package_id
    request_path = analysis_dir / "analysis_evidence.json"
    interpretation_path = analysis_dir / "analysis_interpretation.json"
    instruction_path = paths.root / "src" / "ocl_agent" / "llm" / "FDD_PARTNER_ANALYSIS.md"
    write_analysis_request(
        analysis,
        request_path,
        required_artifact=interpretation_path,
        instruction_path=instruction_path,
    )

    if not interpretation_path.exists():
        return EndToEndResult(
            "AWAITING_ANALYSIS_INTERPRETATION",
            data_prep_output,
            part1=part1,
            databook=part1.databook,
            findings=len(analysis.findings),
            warnings=tuple(warnings),
            coordination=_analysis_coordination(request_path, interpretation_path, instruction_path),
            runtime_config=runtime_config,
        )

    try:
        interpretation = load_analysis_interpretation(interpretation_path, request_path)
    except AnalysisInterpretationError as error:
        coordination = _analysis_coordination(request_path, interpretation_path, instruction_path)
        coordination["validation_error"] = str(error)
        coordination["message"] = (
            "The FDD-partner analysis artifact is missing, stale or invalid. Rewrite it from the current evidence "
            "package; do not alter or recalculate Python metrics."
        )
        return EndToEndResult(
            "AWAITING_ANALYSIS_INTERPRETATION",
            data_prep_output,
            part1=part1,
            databook=part1.databook,
            findings=len(analysis.findings),
            warnings=tuple(warnings),
            coordination=coordination,
            runtime_config=runtime_config,
        )

    questions = apply_partner_interpretation(part1.databook, analysis, interpretation)
    apply_workbook_style(part1.databook)
    qa = validate_final_databook(part1.databook, qa_path)
    report = None if skip_report else run_report(
        analysis,
        questions,
        paths.output,
        partner_interpretation=interpretation,
    )
    _mark_source_ready(runtime_work, source_fingerprint, package_id)
    return EndToEndResult(
        "READY",
        data_prep_output,
        part1=part1,
        databook=part1.databook,
        report=report,
        findings=len(interpretation.get("key_findings") or []),
        questions=len(questions),
        qa=qa,
        warnings=tuple(warnings),
        runtime_config=runtime_config,
    )


def _activate_source_package(runtime_work: Path, output_dir: Path, source_fingerprint: str) -> None:
    """Make generated deliverables unambiguously belong to the current source package.

    When the source bytes/path set changes, previously generated principal
    deliverables are removed before any new processing starts. This prevents a
    user from opening an old OCL_Databook.xlsx while the new source package is
    still waiting at an AI or human checkpoint and mistaking it for current output.
    """
    runtime_work = Path(runtime_work)
    output_dir = Path(output_dir)
    runtime_work.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    marker_path = runtime_work / "active_source_package.json"
    previous = _read_dict(marker_path)
    if previous.get("source_fingerprint") == source_fingerprint:
        return

    for name in ("OCL_Databook.xlsx", "OCL_Report.pptx"):
        path = output_dir / name
        if not path.exists():
            continue
        try:
            path.unlink()
        except PermissionError as error:
            raise RuntimeError(
                f"Source files changed, but stale generated output is open and cannot be replaced: {path}. "
                "Close the file and rerun."
            ) from error

    qa_path = runtime_work / "final_qa.json"
    if qa_path.exists():
        qa_path.unlink()

    marker_path.write_text(
        json.dumps(
            {
                "source_fingerprint": source_fingerprint,
                "status": "IN_PROGRESS",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _mark_source_ready(runtime_work: Path, source_fingerprint: str | None, package_id: str) -> None:
    if not source_fingerprint:
        return
    marker_path = Path(runtime_work) / "active_source_package.json"
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(
        json.dumps(
            {
                "source_fingerprint": source_fingerprint,
                "status": "READY",
                "package_id": package_id,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _read_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _normalize_coordination(coordination: dict[str, Any], raw_status: dict[str, Any]) -> dict[str, Any]:
    result = dict(coordination)
    result.setdefault("source", "fdd-data-preparation")
    result.setdefault("must_continue", result.get("next_actor") == "AI_HOST")
    result.setdefault("resume_command", "python run_all.py")
    if raw_status.get("run_id"):
        result.setdefault("run_id", raw_status["run_id"])
    if raw_status.get("run_directory"):
        result.setdefault("run_directory", raw_status["run_directory"])
    return result


def _analysis_coordination(request_path: Path, interpretation_path: Path, instruction_path: Path) -> dict[str, Any]:
    return {
        "source": "ocl_agent",
        "next_actor": "AI_HOST",
        "next_action": "WRITE_FDD_PARTNER_ANALYSIS",
        "relevant_instruction": str(instruction_path),
        "handoff_path": str(request_path),
        "required_artifacts": [str(interpretation_path)],
        "must_continue": True,
        "resume_command": "python run_all.py",
        "message": (
            "Review the validated Python metrics as an experienced FDD partner and write evidence-backed Deal Issues, "
            "Key Findings and Management Q&A. Do not recalculate or invent financial values; continue automatically "
            "after writing the artifact."
        ),
    }


def _ocl_coordination(part1: Part1Result, runtime_config: Path, repo_root: Path) -> dict[str, Any]:
    instruction = repo_root / "src" / "ocl_agent" / "llm" / "README.md"
    if part1.state == "AWAITING_SEMANTIC_HANDOFF":
        return {
            "source": "ocl_agent",
            "next_actor": "AI_HOST",
            "next_action": "CONFIRM_OCL_SEMANTIC_HANDOFF",
            "relevant_instruction": str(instruction),
            "handoff_path": str(part1.handoff_draft) if part1.handoff_draft else None,
            "required_artifacts": [str(runtime_config / "semantic_handoff.json")],
            "must_continue": True,
            "resume_command": "python run_all.py",
            "message": "Interpret the published standardized datasets for OCL roles; do not reinterpret raw Excel or calculate financial amounts with AI.",
        }
    if part1.state == "AWAITING_JUDGMENT_REVIEW":
        return {
            "source": "ocl_agent",
            "next_actor": "HUMAN",
            "next_action": "REVIEW_OCL_JUDGMENTS",
            "relevant_instruction": str(instruction),
            "review_context": str(part1.review_context) if part1.review_context else None,
            "review_workbook": str(part1.semantic_review) if part1.semantic_review else None,
            "runtime_config": str(runtime_config),
            "must_continue": False,
            "resume_command": "python run_all.py",
            "message": "Scope, mapping/hierarchy, WC/debt-like and normal/one-off judgments require reviewed decisions. Existing human config remains authoritative.",
        }
    if part1.state == "AWAITING_CONTROL_ALIGNMENT":
        blocking = [
            control.control_id
            for control in part1.controls
            if control.status.value in {"FAIL", "REVIEW_REQUIRED"}
        ]
        return {
            "source": "ocl_agent",
            "next_actor": "AI_HOST",
            "next_action": "INVESTIGATE_OCL_CONTROL_ALIGNMENT",
            "relevant_instruction": str(instruction),
            "review_context": str(part1.review_context) if part1.review_context else None,
            "review_workbook": str(part1.semantic_review) if part1.semantic_review else None,
            "blocking_controls": blocking,
            "runtime_config": str(runtime_config),
            "must_continue": True,
            "resume_command": "python run_all.py",
            "message": "Investigate source-backed alignment or genuine breaks. Never solve a control with a plug.",
        }
    return {
        "source": "ocl_agent",
        "next_actor": "HUMAN",
        "next_action": "REVIEW_UNEXPECTED_STATE",
        "must_continue": False,
        "resume_command": "python run_all.py",
        "message": f"OCL Part 1 returned unexpected state {part1.state}.",
    }


def _prepare_package_config(human_config: Path, runtime_config: Path) -> Path:
    """Seed package-specific runtime config once; preserve later AI/human review artifacts."""
    human_config = Path(human_config)
    runtime_config = Path(runtime_config)
    runtime_config.mkdir(parents=True, exist_ok=True)
    if not human_config.exists():
        return runtime_config
    for path in human_config.iterdir():
        if not path.is_file() or path.name in {".gitkeep", "semantic_handoff.json"}:
            continue
        destination = runtime_config / path.name
        if not destination.exists():
            shutil.copy2(path, destination)
    return runtime_config


def _package_id(data_prep_output: Path) -> str:
    for filename, key in (("execution_manifest.json", "execution_id"), ("databook_metadata.json", "workflow_run_id")):
        path = Path(data_prep_output) / filename
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and payload.get(key):
            return str(payload[key])
    return Path(data_prep_output).resolve().name


def _safe_name(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return safe[:100] or "package"
