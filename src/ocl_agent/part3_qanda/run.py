"""Part 3 - management Q&A grouped by commercial theme."""
from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from ocl_agent.part3_qanda.engine import build_questions
from ocl_agent.schemas import AnalysisResult, ManagementQuestion


def run_qanda(analysis: AnalysisResult, databook_path: Path) -> tuple[ManagementQuestion, ...]:
    questions = build_questions(analysis)
    _embed_questions(Path(databook_path), questions, analysis)
    return questions


def _embed_questions(path: Path, questions: tuple[ManagementQuestion, ...], analysis: AnalysisResult) -> None:
    workbook = load_workbook(path)
    if "Management Questions" in workbook.sheetnames:
        del workbook["Management Questions"]
    sheet = workbook.create_sheet("Management Questions")
    finding_by_id = {finding.finding_id: finding for finding in analysis.findings}
    sheet.append(["Theme", "Priority", "Question", "Evidence", "Why This Matters", "Response", "Linked Finding"])
    for item in sorted(questions, key=lambda q: (_theme(finding_by_id.get(q.linked_finding_id)), q.priority, q.question)):
        finding = finding_by_id.get(item.linked_finding_id)
        sheet.append([
            _theme(finding),
            item.priority,
            item.question,
            _evidence(finding),
            item.rationale,
            "",
            item.linked_finding_id,
        ])
    sheet.sheet_view.showGridLines = False
    sheet.freeze_panes = "A2"
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for column in range(1, sheet.max_column + 1):
        width = min(65, max(14, max(len(str(sheet.cell(row, column).value or "")) for row in range(1, min(sheet.max_row, 150) + 1)) + 2))
        sheet.column_dimensions[get_column_letter(column)].width = width
    workbook.save(path)


def _theme(finding) -> str:
    if finding is None:
        return "Other OCL matters"
    return {
        "DEBT_LIKE": "Net debt & equity value",
        "DEBT_LIKE_GAP": "Net debt & equity value",
        "ONE_OFF": "Quality of earnings",
        "SEASONALITY": "Seasonality & phasing",
        "MONTHLY_VARIABILITY": "Seasonality & phasing",
        "STALE_BALANCE": "Working capital & balance validity",
        "NEW_ITEM": "Completeness & balance validity",
        "CLIFF": "Quality of earnings",
        "CATEGORY_MOVEMENT": "Balance movements",
        "TOTAL_CHANGE": "Balance movements",
        "CONCENTRATION": "Balance composition",
    }.get(finding.finding_type, "Other OCL matters")


def _evidence(finding) -> str:
    if finding is None:
        return ""
    references = ", ".join(finding.evidence_references)
    return finding.text + (f" | References: {references}" if references else "")
