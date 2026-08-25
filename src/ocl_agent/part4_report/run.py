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
    return render_report(
        analysis,
        questions,
        Path(output_dir) / "OCL_Report.pptx",
        partner_interpretation=partner_interpretation,
    )
