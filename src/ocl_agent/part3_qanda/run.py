"""Part 3 — management questions driven by Part 2 findings."""
from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from ocl_agent.part3_qanda.engine import build_questions
from ocl_agent.schemas import AnalysisResult, ManagementQuestion


def run_qanda(analysis: AnalysisResult, databook_path: Path) -> tuple[ManagementQuestion, ...]:
    questions = build_questions(analysis)
    _embed_questions(Path(databook_path), questions)
    return questions


def _embed_questions(path: Path, questions: tuple[ManagementQuestion, ...]) -> None:
    workbook = load_workbook(path)
    if "Management Questions" in workbook.sheetnames:
        del workbook["Management Questions"]
    sheet = workbook.create_sheet("Management Questions")
    sheet.append(["Priority", "Management Question", "Why This Matters", "Linked Finding"])
    for item in questions:
        sheet.append([item.priority, item.question, item.rationale, item.linked_finding_id])
    sheet.sheet_view.showGridLines = False
    sheet.freeze_panes = "A2"
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for column in range(1, sheet.max_column + 1):
        width = min(65, max(14, max(len(str(sheet.cell(row, column).value or "")) for row in range(1, min(sheet.max_row, 150) + 1)) + 2))
        sheet.column_dimensions[get_column_letter(column)].width = width
    workbook.save(path)
