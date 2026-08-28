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
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ocl_agent.config import RepoPaths
from ocl_agent.data_prep_bridge import run_full_data_preparation, source_package_fingerprint
from ocl_agent.final_qa import validate_final_databook
from ocl_agent.final_presentation import apply_final_workbook_presentation
from ocl_agent.output_versioning import publish_versioned_databook
from ocl_agent.part1_databook.run import Part1Result, run_part1
from ocl_agent.part2_analysis.ai_interpretation import (
    AnalysisInterpretationError,
    load_analysis_interpretation,
    load_analysis_result,
    write_analysis_request,
)
from ocl_agent.part2_analysis.ai_render import apply_partner_interpretation
from ocl_agent.part2_analysis.pipeline import run_analysis
from ocl_agent.workflow_checkpoint import (
    checkpoint_matches,
    load_checkpoint,
    sha256_directory,
    sha256_file,
    sha256_named_files,
    write_checkpoint,
)


@dataclass(frozen=True)
class EndToEndResult:
    state: str
    data_prep_output: Path | None = None
    part1: Part1Result | None = None
    databook: Path | None = None
    working_databook: Path | None = None
    published_version: int | None = None
    findings: int = 0
    questions: int = 0
    qa: dict | None = None
    warnings: tuple[str, ...] = ()
    coordination: dict[str, Any] = field(default_factory=dict)
    runtime_config: Path | None = None
    checkpoint: Path | None = None
    timings: dict[str, float] = field(default_factory=dict)


def run_end_to_end(
    paths: RepoPaths,
    *,
    data_prep_output: Path | None = None,
    part1_only: bool = False,
) -> EndToEndResult:
    """Advance raw source through one resumable, databook-only workflow."""
    runtime_work = paths.work
    warnings: list[str] = []
    source_fingerprint: str | None = None
    timings: dict[str, float] = {}
    package_started = time.perf_counter()

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
                timings={"data_prep_package_loading": time.perf_counter() - package_started},
            )
        data_prep_output = prep.standardized_output
    else:
        data_prep_output = Path(data_prep_output).resolve()
        source_fingerprint = _published_source_fingerprint(data_prep_output)

    assert data_prep_output is not None
    package_id = _package_id(data_prep_output)
    safe_package_id = _safe_name(package_id)
    runtime_config = _prepare_package_config(paths.config, runtime_work / "ocl_config" / safe_package_id)
    runtime_dir = paths.ocl_runtime / safe_package_id
    runtime_dir.mkdir(parents=True, exist_ok=True)
    support_dir = paths.support_working / safe_package_id
    working_databook = runtime_dir / "OCL_Databook_working.xlsx"
    checkpoint_path = runtime_dir / "workflow_checkpoint.json"
    qa_path = runtime_dir / "final_qa.json"
    analysis_dir = runtime_work / "analysis" / safe_package_id
    request_path = analysis_dir / "analysis_evidence.json"
    interpretation_path = analysis_dir / "analysis_interpretation.json"
    instruction_path = paths.root / "src" / "ocl_agent" / "llm" / "FDD_PARTNER_ANALYSIS.md"
    identity = _checkpoint_identity(data_prep_output, package_id, source_fingerprint, runtime_config)
    timings["data_prep_package_loading"] = time.perf_counter() - package_started

    checkpoint = load_checkpoint(checkpoint_path)
    resumable, resume_reason = checkpoint_matches(checkpoint, identity)
    if resumable:
        print(f"Checkpoint resume: ACCEPTED — {checkpoint.get('completed_stage')}", flush=True)
    else:
        print(f"Checkpoint resume: REJECTED — {resume_reason}", flush=True)
    if resumable and checkpoint.get("completed_stage") == "READY":
        published = Path(checkpoint["published_databook_path"])
        return EndToEndResult(
            "READY", data_prep_output, databook=published, working_databook=working_databook,
            published_version=int(checkpoint["published_version"]), qa=_read_dict(qa_path),
            findings=int(checkpoint.get("finding_count") or 0), questions=int(checkpoint.get("question_count") or 0),
            warnings=tuple(warnings), runtime_config=runtime_config, checkpoint=checkpoint_path, timings=timings,
        )
    if resumable and part1_only and checkpoint.get("completed_stage") == "PART1_READY" and checkpoint.get("part1_only_qa"):
        return EndToEndResult(
            "DATABOOK_READY", data_prep_output, databook=working_databook, working_databook=working_databook,
            qa=_read_dict(qa_path), warnings=tuple(warnings), runtime_config=runtime_config,
            checkpoint=checkpoint_path, timings=timings,
        )

    analysis = None
    interpretation = None
    if resumable and checkpoint.get("completed_stage") in {"ANALYSIS_READY", "INTERPRETATION_READY"}:
        analysis = load_analysis_result(request_path)
        if not interpretation_path.exists():
            return EndToEndResult(
                "AWAITING_ANALYSIS_INTERPRETATION", data_prep_output, databook=working_databook,
                working_databook=working_databook, findings=len(analysis.findings), warnings=tuple(warnings),
                coordination=_analysis_coordination(request_path, interpretation_path, instruction_path),
                runtime_config=runtime_config, checkpoint=checkpoint_path, timings=timings,
            )
        try:
            interpretation = load_analysis_interpretation(interpretation_path, request_path)
        except AnalysisInterpretationError as error:
            return _awaiting_interpretation(
                data_prep_output, working_databook, analysis, warnings, runtime_config, checkpoint_path,
                request_path, interpretation_path, instruction_path, timings, error,
            )
        if checkpoint.get("completed_stage") == "INTERPRETATION_READY":
            if checkpoint.get("analysis_interpretation_hash") != sha256_file(interpretation_path):
                resumable = False
            else:
                return _finalize_databook(
                    paths, data_prep_output, package_id, source_fingerprint, runtime_config, working_databook,
                    checkpoint_path, qa_path, request_path, interpretation_path, identity, analysis,
                    interpretation, warnings, timings, render_interpretation=False,
                )
        if resumable:
            return _finalize_databook(
                paths, data_prep_output, package_id, source_fingerprint, runtime_config, working_databook,
                checkpoint_path, qa_path, request_path, interpretation_path, identity, analysis,
                interpretation, warnings, timings, render_interpretation=True,
            )

    part1_started = time.perf_counter()
    part1 = run_part1(
        data_prep_output,
        runtime_config,
        paths.output,
        working_databook=working_databook,
        support_dir=support_dir,
    )
    timings["part1"] = time.perf_counter() - part1_started
    if part1.state != "DATABOOK_READY" or not part1.databook or not part1.build:
        return EndToEndResult(
            part1.state,
            data_prep_output,
            part1=part1,
            warnings=tuple(warnings),
            coordination=_ocl_coordination(part1, runtime_config, paths.root),
            runtime_config=runtime_config,
            checkpoint=checkpoint_path,
            timings=timings,
        )

    identity = _checkpoint_identity(
        data_prep_output,
        package_id,
        source_fingerprint,
        runtime_config,
        package_fingerprint=str(identity["package_fingerprint"]),
    )
    _write_stage_checkpoint(checkpoint_path, identity, "PART1_READY", working_databook)
    if part1_only:
        presentation_started = time.perf_counter()
        apply_final_workbook_presentation(part1.databook, runtime_config / "semantic_handoff.json")
        timings["final_presentation"] = time.perf_counter() - presentation_started
        qa_started = time.perf_counter()
        qa = validate_final_databook(part1.databook, qa_path)
        timings["final_qa"] = time.perf_counter() - qa_started
        _write_stage_checkpoint(
            checkpoint_path,
            identity,
            "PART1_READY",
            working_databook,
            part1_only_qa=True,
            final_qa_path=str(qa_path.resolve()),
            final_qa_hash=sha256_file(qa_path),
        )
        _mark_source_ready(runtime_work, source_fingerprint, package_id)
        return EndToEndResult(
            "DATABOOK_READY",
            data_prep_output,
            part1=part1,
            databook=part1.databook,
            working_databook=working_databook,
            qa=qa,
            warnings=tuple(warnings),
            runtime_config=runtime_config,
            checkpoint=checkpoint_path,
            timings=timings,
        )

    # Python calculates all metrics and writes the formula-linked analysis layer.
    # Explicit movement records are passed through only when Part 1 validated
    # their source roles/sign rules; missing movement evidence degrades to
    # UNSUPPORTED analysis rather than being inferred from balances.
    analysis_started = time.perf_counter()
    analysis = run_analysis(
        part1.build.records,
        part1.databook,
        package=part1.package,
        handoff=part1.handoff,
        movements=part1.movement_build.records if part1.movement_build else (),
    )
    timings["deterministic_analysis"] = time.perf_counter() - analysis_started

    # The active coding AI now performs the qualitative FDD-partner interpretation
    # from a hash-bound evidence package. It writes Deal Issues, Key Findings and
    # management Q&A; Python validates the artifact before rendering it.
    write_analysis_request(
        analysis,
        request_path,
        required_artifact=interpretation_path,
        instruction_path=instruction_path,
    )
    _write_stage_checkpoint(checkpoint_path, identity, "ANALYSIS_READY", working_databook, request_path)

    if not interpretation_path.exists():
        return EndToEndResult(
            "AWAITING_ANALYSIS_INTERPRETATION",
            data_prep_output,
            part1=part1,
            databook=part1.databook,
            working_databook=working_databook,
            findings=len(analysis.findings),
            warnings=tuple(warnings),
            coordination=_analysis_coordination(request_path, interpretation_path, instruction_path),
            runtime_config=runtime_config,
            checkpoint=checkpoint_path,
            timings=timings,
        )

    try:
        interpretation = load_analysis_interpretation(interpretation_path, request_path)
    except AnalysisInterpretationError as error:
        return _awaiting_interpretation(
            data_prep_output, working_databook, analysis, warnings, runtime_config, checkpoint_path,
            request_path, interpretation_path, instruction_path, timings, error, part1,
        )

    return _finalize_databook(
        paths, data_prep_output, package_id, source_fingerprint, runtime_config, working_databook,
        checkpoint_path, qa_path, request_path, interpretation_path, identity, analysis,
        interpretation, warnings, timings, render_interpretation=True, part1=part1,
    )


def _checkpoint_identity(
    data_prep_output: Path,
    package_id: str,
    source_fingerprint: str | None,
    runtime_config: Path,
    *,
    package_fingerprint: str | None = None,
) -> dict[str, Any]:
    semantic_path = Path(runtime_config) / "semantic_handoff.json"
    judgment_paths = [Path(runtime_config) / name for name in ("judgment_scope.csv", "mapping.csv", "judgment_wc_debt.csv")]
    return {
        "package_id": package_id,
        "source_fingerprint": source_fingerprint,
        "package_fingerprint": package_fingerprint or sha256_directory(data_prep_output),
        "semantic_handoff_hash": sha256_file(semantic_path) if semantic_path.is_file() else None,
        "judgment_config_hash": sha256_named_files(judgment_paths),
    }


def _write_stage_checkpoint(
    checkpoint_path: Path,
    identity: dict[str, Any],
    stage: str,
    working_databook: Path,
    analysis_evidence: Path | None = None,
    **extra: Any,
) -> None:
    payload = {
        **identity,
        "completed_stage": stage,
        "working_databook_path": str(Path(working_databook).resolve()),
        "working_databook_hash": sha256_file(working_databook),
        "analysis_evidence_path": str(Path(analysis_evidence).resolve()) if analysis_evidence else None,
        "analysis_evidence_hash": sha256_file(analysis_evidence) if analysis_evidence and Path(analysis_evidence).is_file() else None,
        **extra,
    }
    write_checkpoint(checkpoint_path, payload)


def _awaiting_interpretation(
    data_prep_output: Path,
    working_databook: Path,
    analysis,
    warnings: list[str],
    runtime_config: Path,
    checkpoint_path: Path,
    request_path: Path,
    interpretation_path: Path,
    instruction_path: Path,
    timings: dict[str, float],
    error: Exception,
    part1: Part1Result | None = None,
) -> EndToEndResult:
    coordination = _analysis_coordination(request_path, interpretation_path, instruction_path)
    coordination["validation_error"] = str(error)
    coordination["message"] = (
        "The FDD-partner analysis artifact is missing, stale or invalid. Rewrite it from the current evidence "
        "package; do not alter or recalculate Python metrics."
    )
    return EndToEndResult(
        "AWAITING_ANALYSIS_INTERPRETATION", data_prep_output, part1=part1,
        databook=working_databook, working_databook=working_databook,
        findings=len(analysis.findings), warnings=tuple(warnings), coordination=coordination,
        runtime_config=runtime_config, checkpoint=checkpoint_path, timings=timings,
    )


def _finalize_databook(
    paths: RepoPaths,
    data_prep_output: Path,
    package_id: str,
    source_fingerprint: str | None,
    runtime_config: Path,
    working_databook: Path,
    checkpoint_path: Path,
    qa_path: Path,
    request_path: Path,
    interpretation_path: Path,
    identity: dict[str, Any],
    analysis,
    interpretation: dict[str, Any],
    warnings: list[str],
    timings: dict[str, float],
    *,
    render_interpretation: bool,
    part1: Part1Result | None = None,
) -> EndToEndResult:
    if render_interpretation:
        render_started = time.perf_counter()
        questions = apply_partner_interpretation(working_databook, analysis, interpretation)
        timings["partner_interpretation_rendering"] = time.perf_counter() - render_started
        _write_stage_checkpoint(
            checkpoint_path,
            identity,
            "INTERPRETATION_READY",
            working_databook,
            request_path,
            analysis_interpretation_path=str(Path(interpretation_path).resolve()),
            analysis_interpretation_hash=sha256_file(interpretation_path),
        )
        question_count = len(questions)
    else:
        question_count = len(interpretation.get("management_questions") or [])

    presentation_started = time.perf_counter()
    apply_final_workbook_presentation(working_databook, runtime_config / "semantic_handoff.json")
    timings["final_presentation"] = time.perf_counter() - presentation_started

    qa_started = time.perf_counter()
    qa = validate_final_databook(working_databook, qa_path)
    timings["final_qa"] = time.perf_counter() - qa_started
    qa_databook_hash = sha256_file(working_databook)
    if qa.get("databook_sha256") not in (None, qa_databook_hash):
        raise RuntimeError("Final QA result is not bound to the current final workbook bytes.")

    publication_started = time.perf_counter()
    published = publish_versioned_databook(
        working_databook,
        paths.output,
        expected_sha256=qa_databook_hash,
    )
    timings["version_publication"] = time.perf_counter() - publication_started
    published_databook_hash = sha256_file(published.databook)
    if published_databook_hash != qa_databook_hash:
        raise RuntimeError("Published databook bytes differ from the exact workbook that passed final QA.")
    _write_stage_checkpoint(
        checkpoint_path,
        identity,
        "READY",
        working_databook,
        request_path,
        analysis_interpretation_path=str(Path(interpretation_path).resolve()),
        analysis_interpretation_hash=sha256_file(interpretation_path),
        published_version=published.version,
        published_databook_path=str(published.databook.resolve()),
        published_databook_hash=published_databook_hash,
        qa_databook_hash=qa_databook_hash,
        final_qa_path=str(Path(qa_path).resolve()),
        final_qa_hash=sha256_file(qa_path),
        finding_count=len(interpretation.get("key_findings") or []),
        question_count=question_count,
    )
    _mark_source_ready(paths.work, source_fingerprint, package_id)
    return EndToEndResult(
        "READY", data_prep_output, part1=part1, databook=published.databook,
        working_databook=working_databook, published_version=published.version,
        findings=len(interpretation.get("key_findings") or []), questions=question_count,
        qa=qa, warnings=tuple(warnings), runtime_config=runtime_config,
        checkpoint=checkpoint_path, timings=timings,
    )


def _published_source_fingerprint(data_prep_output: Path) -> str | None:
    for filename in ("execution_manifest.json", "databook_metadata.json"):
        payload = _read_dict(Path(data_prep_output) / filename)
        for key in ("source_fingerprint", "source_package_fingerprint"):
            value = str(payload.get(key) or "").strip()
            if value:
                return value
    return None


def _activate_source_package(runtime_work: Path, output_dir: Path, source_fingerprint: str) -> None:
    """Activate a source package without ever deleting versioned history.

    Exact legacy unversioned files are removed during migration. Current working
    databooks/checkpoints are package-scoped under ``work/ocl_runtime`` and are
    invalidated by content hashes rather than by deleting historical output.
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
