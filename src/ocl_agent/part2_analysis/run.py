"""Part 2 — deterministic analysis from the reconciled Part 1 OCL model."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from openpyxl import load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from ocl_agent.part1_databook.input_contract import StandardizedPackage
from ocl_agent.part1_databook.semantic_handoff import SemanticHandoff
from ocl_agent.part2_analysis.context import enrich_with_context, load_context
from ocl_agent.part2_analysis.engine import analyse_records
from ocl_agent.schemas import AnalysisResult, OCLRecord


def run_analysis(records: Iterable[OCLRecord], databook_path: Path, *, package: StandardizedPackage | None = None, handoff: SemanticHandoff | None = None) -> AnalysisResult:
    rows = tuple(records)
    result = analyse_records(rows)
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
    for table in result.tables:
        summary.append([table.title])
        summary.cell(summary.max_row, 1).font = Font(bold=True)
        summary.append(list(table.headers))
        for row in table.rows:
            summary.append(list(row))
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
            width = min(55, max(12, max(len(str(sheet.cell(row, column).value or "")) for row in range(1, min(sheet.max_row, 150) + 1)) + 2))
            sheet.column_dimensions[get_column_letter(column)].width = width
    workbook.save(path)
