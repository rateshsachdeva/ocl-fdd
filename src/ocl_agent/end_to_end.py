"""Single-repository end-to-end OCL workflow."""
from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from pathlib import Path

from ocl_agent.auto_judgments import ensure_autonomous_judgments
from ocl_agent.auto_semantics import ensure_semantic_handoff
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
    part1: Part1Result | None = None
    databook: Path | None = None
    report: Path | None = None
    findings: int = 0
    questions: int = 0
    qa: dict | None = None
    warnings: tuple[str, ...] = ()


def run_end_to_end(paths: RepoPaths, *, data_prep_output: Path | None = None, part1_only: bool = False, skip_report: bool = False) -> EndToEndResult:
    """Run raw source -> data prep -> OCL databook -> analysis/Q&A/report/QA.

    When `data_prep_output` is supplied, the upstream step is skipped for
    backwards compatibility. Otherwise raw workbooks are read from the single
    top-level `references/source/` folder.
    """
    warnings: tuple[str, ...] = ()
    if data_prep_output is None:
        prep_root = paths.root / "work" / "data_prep" / "latest"
        prep_result = _run_embedded_data_prep(paths.root, paths.source, prep_root)
        data_prep_output = prep_result.output_dir
        warnings = tuple(prep_result.warnings)
    else:
        data_prep_output = Path(data_prep_output).resolve()

    ensure_semantic_handoff(data_prep_output, paths.config)
    ensure_autonomous_judgments(data_prep_output, paths.config)
    part1 = run_part1(data_prep_output, paths.config, paths.output)
    if part1.state != "DATABOOK_READY" or not part1.databook or not part1.build:
        return EndToEndResult(part1.state, data_prep_output, part1=part1, warnings=warnings)

    if part1_only:
        apply_workbook_style(part1.databook)
        qa = validate_final_databook(part1.databook, paths.root / "work" / "final_qa.json")
        return EndToEndResult("DATABOOK_READY", data_prep_output, part1=part1, databook=part1.databook, qa=qa, warnings=warnings)

    analysis = run_analysis(part1.build.records, part1.databook, package=part1.package, handoff=part1.handoff)
    questions = run_qanda(analysis, part1.databook)
    apply_workbook_style(part1.databook)
    qa = validate_final_databook(part1.databook, paths.root / "work" / "final_qa.json")
    report = None if skip_report else run_report(analysis, questions, paths.output)
    return EndToEndResult(
        "READY",
        data_prep_output,
        part1=part1,
        databook=part1.databook,
        report=report,
        findings=len(analysis.findings),
        questions=len(questions),
        qa=qa,
        warnings=warnings,
    )


def _run_embedded_data_prep(repo_root: Path, source_dir: Path, output_dir: Path):
    embedded_src = repo_root / "fdd-data-preparation" / "src"
    if not embedded_src.is_dir():
        raise FileNotFoundError("Embedded fdd-data-preparation runtime is missing from the repository.")
    text = str(embedded_src)
    if text not in sys.path:
        sys.path.insert(0, text)
    module = importlib.import_module("fdd_data")
    return module.prepare_source_package(source_dir, output_dir)
