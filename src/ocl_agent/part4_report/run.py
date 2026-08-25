"""Part 4 — create the OCL PowerPoint report from the shared analysis model."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ocl_agent.part4_report.renderer import render_report
from ocl_agent.schemas import AnalysisResult, ManagementQuestion


def run_report(
    analysis: AnalysisResult,
    questions: tuple[ManagementQuestion, ...],
    output_dir: Path,
    *,
    partner_interpretation: dict[str, Any] | None = None,
) -> Path:
    # The workbook narrative is AI-host authored. The current deterministic PPT
    # renderer consumes the same validated analysis plus those AI-written Q&A
    # items; partner_interpretation is accepted here so the orchestration contract
    # stays stable while slide-specific narrative rendering remains presentation-only.
    return render_report(analysis, questions, Path(output_dir) / "OCL_Report.pptx")
