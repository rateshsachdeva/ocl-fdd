"""Part 2 — deterministic analysis from the reconciled Part 1 OCL model.

Python calculates independent evidence for findings/reporting. Financial tables
embedded in Excel remain formula-linked to the formula-driven Part 1 schedules.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from openpyxl import load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from ocl_agent.part1_databook.input_contract import StandardizedPackage
from ocl_agent.part1_databook.semantic_handoff import SemanticHandoff
from ocl_agent.part2_analysis.context import enrich_with_context, load_context
from ocl_agent.part2_analysis.diagnostics import diagnostic_findings
from ocl_agent.part2_analysis.engine import analyse_records
from ocl_agent.schemas import AnalysisResult, OCLRecord


def run_analysis(records: Iterable[OCLRecord], databook_path: Path, *, package: StandardizedPackage | None = None, handoff: SemanticHandoff | None = None) -> AnalysisResult:
    rows = tuple(records)
    base = analyse_records(rows)
    extra = diagnostic_findings(rows)
    seen = {item.finding_id for item in base.findings}
    result = AnalysisResult((*base.findings, *(item for item in extra if item.finding_id not in seen)), base.tables, base.annual_periods, base.monthly_periods, base.latest_annual_period)
    if package is not None and handoff is not None:
        result = enrich_with_context(result, rows, load_context(package, handoff))
    _embed_analysis(Path(databook_path), result)
    return result


def _embed_analysis(path: Path, result: AnalysisResult) -> None:
    workbook = load_workbook(path)
    for name in ("Analysis Summary", "Key Findings"):
        if name in workbook.sheetnames:
            del workbook[name]
    summary = workbook.create_sheet("Analysis Summary")
    _write_formula_linked_annual(summary, workbook)
    _write_formula_linked_monthly_stats(summary, workbook)
    if any(table.key == "context_ratios" for table in result.tables):
        summary.append(["Optional contextual ratios", "Calculated independently by Python for reporting; not hard-coded into the Excel financial schedule."])
        summary.append([])

    findings = workbook.create_sheet("Key Findings")
    findings.append(["Priority", "Finding", "Evidence", "Type"])
    for finding in result.findings:
        findings.append([finding.priority, finding.title, finding.text, finding.finding_type])
    for sheet in (summary, findings):
        sheet.sheet_view.showGridLines = False
        sheet.freeze_panes = "A2"
        if sheet.max_row:
            for cell in sheet[1]:
                cell.font = Font(bold=True)
        for column in range(1, sheet.max_column + 1):
            width = min(60, max(12, max(len(str(sheet.cell(row, column).value or "")) for row in range(1, min(sheet.max_row, 150) + 1)) + 2))
            sheet.column_dimensions[get_column_letter(column)].width = width
    workbook.save(path)


def _write_formula_linked_annual(summary, workbook) -> None:
    if "Balance by Category" not in workbook.sheetnames:
        return
    source = workbook["Balance by Category"]
    summary.append(["Annual OCL balance by category"])
    summary.cell(summary.max_row, 1).font = Font(bold=True)
    for row in range(1, source.max_row + 1):
        values = []
        for column in range(1, source.max_column + 1):
            coordinate = source.cell(row, column).coordinate
            values.append(f"='Balance by Category'!{coordinate}")
        summary.append(values)
    summary.append([])


def _write_formula_linked_monthly_stats(summary, workbook) -> None:
    if "Monthly Balance" not in workbook.sheetnames:
        return
    source = workbook["Monthly Balance"]
    if source.max_column < 2:
        return
    summary.append(["Monthly OCL statistics by category"])
    summary.cell(summary.max_row, 1).font = Font(bold=True)
    summary.append(["Category", "Average", "Minimum", "Maximum", "Std_Dev", "Latest"])
    last_column = get_column_letter(source.max_column)
    for source_row in range(2, source.max_row + 1):
        label = source.cell(source_row, 1).value
        if label in (None, ""):
            continue
        summary.append([
            f"='Monthly Balance'!A{source_row}",
            f"=AVERAGE('Monthly Balance'!B{source_row}:{last_column}{source_row})",
            f"=MIN('Monthly Balance'!B{source_row}:{last_column}{source_row})",
            f"=MAX('Monthly Balance'!B{source_row}:{last_column}{source_row})",
            f"=STDEV.P('Monthly Balance'!B{source_row}:{last_column}{source_row})",
            f"='Monthly Balance'!{last_column}{source_row}",
        ])
    summary.append([])
