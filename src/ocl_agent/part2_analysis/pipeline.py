"""Part 2 orchestration with evidence-aware extended analysis."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ocl_agent.part1_databook.input_contract import StandardizedPackage
from ocl_agent.part1_databook.semantic_handoff import SemanticHandoff
from ocl_agent.part2_analysis.context import load_context
from ocl_agent.part2_analysis.extended import extended_analysis
from ocl_agent.part2_analysis.extended_render import embed_extended_analysis
from ocl_agent.part2_analysis.run import run_analysis as run_base_analysis
from ocl_agent.schemas import AnalysisResult, MovementRecord, OCLRecord


def run_analysis(
    records: Iterable[OCLRecord],
    databook_path: Path,
    *,
    package: StandardizedPackage | None = None,
    handoff: SemanticHandoff | None = None,
    movements: Iterable[MovementRecord] = (),
) -> AnalysisResult:
    """Run the proven base analysis, then add evidence-supported FDD extensions."""
    rows = tuple(records)
    movement_rows = tuple(movements)
    base = run_base_analysis(rows, databook_path, package=package, handoff=handoff)
    context = load_context(package, handoff) if package is not None and handoff is not None else {}
    extra_findings, extra_tables = extended_analysis(rows, movements=movement_rows, context=context)

    seen = {item.finding_id for item in base.findings}
    findings = (*base.findings, *(item for item in extra_findings if item.finding_id not in seen))
    table_keys = {table.key for table in base.tables}
    tables = (*base.tables, *(table for table in extra_tables if table.key not in table_keys))
    result = AnalysisResult(findings, tables, base.annual_periods, base.monthly_periods, base.latest_annual_period)
    embed_extended_analysis(Path(databook_path), result)
    return result
