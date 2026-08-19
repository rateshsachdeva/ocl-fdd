"""Presentation-only styling for the final OCL databook.

The style layer may improve readability but must never create categories,
periods, financial values or analyses that are absent from the reconciled model.
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

NAVY = "17365D"
MEDIUM_BLUE = "4472C4"
LIGHT_BLUE = "D9EAF7"
SOURCE_GREY = "7F8C8D"
LIGHT_GREY = "E7E6E6"
INPUT_BLUE = "0000FF"
LINK_GREEN = "008000"
BLACK = "000000"
WHITE = "FFFFFF"
AMBER = "FFF2CC"
AMBER_FONT = "9C6500"
PASS_FILL = "C6EFCE"
PASS_FONT = "006100"
FAIL_FILL = "FFC7CE"
FAIL_FONT = "9C0006"
HIGH_FILL = "FCE4D6"
MEDIUM_FILL = "FFF2CC"
ACCOUNTING = '#,##0;[Red](#,##0);-'
THIN_GREY = Side(style="thin", color="BFBFBF")
MEDIUM_NAVY = Side(style="medium", color=NAVY)


def apply_workbook_style(path: Path) -> Path:
    path = Path(path)
    workbook = load_workbook(path)
    for sheet in workbook.worksheets:
        _base_sheet(sheet)
        if sheet.title.startswith("SRC_"):
            _source_sheet(sheet)
        elif sheet.title in {"Flat File", "Monthly Flat"}:
            _flat_sheet(sheet)
        elif sheet.title in {"Balance by Category", "Monthly Balance", "Roll-forward", "Analysis Summary"}:
            _analysis_sheet(sheet)
        elif sheet.title == "Checks":
            _checks_sheet(sheet)
        elif sheet.title == "Mapping":
            _mapping_sheet(sheet)
        elif sheet.title == "UNMAPPED":
            _unmapped_sheet(sheet)
        elif sheet.title == "SCOPE_EXCLUDED":
            _scope_excluded_sheet(sheet)
        elif sheet.title == "Key Findings":
            _findings_sheet(sheet)
        elif sheet.title == "Management Questions":
            _questions_sheet(sheet)
        else:
            _standard_header(sheet)
    try:
        workbook.calculation.fullCalcOnLoad = True
        workbook.calculation.forceFullCalc = True
    except AttributeError:
        pass
    workbook.save(path)
    return path


def _base_sheet(sheet) -> None:
    sheet.sheet_view.showGridLines = False
    sheet.sheet_view.zoomScale = 90
    if sheet.freeze_panes is None:
        sheet.freeze_panes = "A2"
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.page_margins.left = 0.25
    sheet.page_margins.right = 0.25
    sheet.page_margins.top = 0.5
    sheet.page_margins.bottom = 0.5
    for row in sheet.iter_rows():
        for cell in row:
            cell.font = Font(name="Arial", size=10, color=cell.font.color if cell.font and cell.font.color and cell.font.color.type == "rgb" else BLACK,
                             bold=cell.font.bold if cell.font else False,
                             italic=cell.font.italic if cell.font else False)
            cell.alignment = Alignment(vertical="center", wrap_text=False)
    if sheet.max_row:
        sheet.row_dimensions[1].height = 22


def _standard_header(sheet, fill: str = NAVY) -> None:
    if sheet.max_row < 1:
        return
    for cell in sheet[1]:
        cell.fill = PatternFill("solid", fgColor=fill)
        cell.font = Font(name="Arial", size=10, bold=True, color=WHITE)
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        cell.border = Border(bottom=MEDIUM_NAVY)
    sheet.auto_filter.ref = sheet.dimensions if sheet.max_row >= 2 else None
    _reasonable_widths(sheet)


def _source_sheet(sheet) -> None:
    _standard_header(sheet, SOURCE_GREY)
    sheet.sheet_properties.tabColor = SOURCE_GREY
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name="Arial", size=9, color=INPUT_BLUE)
            if isinstance(cell.value, (int, float)):
                cell.number_format = ACCOUNTING
    sheet.protection.sheet = True


def _flat_sheet(sheet) -> None:
    _standard_header(sheet)
    sheet.sheet_properties.tabColor = MEDIUM_BLUE
    headers = {str(cell.value): cell.column for cell in sheet[1] if cell.value}
    amount_col = headers.get("Amount")
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name="Arial", size=9, color=INPUT_BLUE)
        if amount_col:
            amount_cell = sheet.cell(row[0].row, amount_col)
            amount_cell.number_format = ACCOUNTING
            if isinstance(amount_cell.value, str) and amount_cell.value.startswith("="):
                amount_cell.font = Font(name="Arial", size=9, color=LINK_GREEN)
    _set_width(sheet, headers.get("Source_Record_ID"), 26)
    _set_width(sheet, headers.get("Source_Label"), 30)
    _set_width(sheet, headers.get("Reason"), 38)


def _analysis_sheet(sheet) -> None:
    _standard_header(sheet)
    sheet.sheet_properties.tabColor = NAVY
    for row in range(2, sheet.max_row + 1):
        label = str(sheet.cell(row, 1).value or "")
        is_total = label.casefold().startswith("total ocl")
        formula_cells = [cell for cell in sheet[row][1:] if isinstance(cell.value, str) and cell.value.startswith("=")]
        is_parent = bool(formula_cells) and any(str(cell.value).upper().startswith("=SUM(") for cell in formula_cells) and not is_total
        if is_total:
            for cell in sheet[row]:
                cell.fill = PatternFill("solid", fgColor=NAVY)
                cell.font = Font(name="Arial", size=10, bold=True, color=WHITE)
                cell.border = Border(top=MEDIUM_NAVY, bottom=MEDIUM_NAVY)
        elif is_parent:
            for cell in sheet[row]:
                cell.fill = PatternFill("solid", fgColor=LIGHT_BLUE)
                cell.font = Font(name="Arial", size=10, bold=True, color=BLACK)
                cell.border = Border(top=THIN_GREY)
        for cell in sheet[row][1:]:
            if isinstance(cell.value, (int, float)) or (isinstance(cell.value, str) and cell.value.startswith("=")):
                cell.number_format = ACCOUNTING
                if not is_total:
                    cell.font = Font(name="Arial", size=10, bold=is_parent, color=BLACK)
    if sheet.title in {"Balance by Category", "Monthly Balance"}:
        sheet.column_dimensions["A"].width = 32
        for col in range(2, sheet.max_column + 1):
            sheet.column_dimensions[get_column_letter(col)].width = 14
    elif sheet.title == "Roll-forward":
        sheet.column_dimensions["A"].width = 30
        for col in range(2, sheet.max_column + 1):
            sheet.column_dimensions[get_column_letter(col)].width = 16
    elif sheet.title == "Analysis Summary":
        _reasonable_widths(sheet, max_width=28)


def _checks_sheet(sheet) -> None:
    _standard_header(sheet)
    sheet.sheet_properties.tabColor = MEDIUM_BLUE
    headers = {str(cell.value): cell.column for cell in sheet[1] if cell.value}
    for row in range(2, sheet.max_row + 1):
        for name in ("Python_Actual", "Python_Expected", "Python_Difference", "Workbook_Difference"):
            col = headers.get(name)
            if col:
                sheet.cell(row, col).number_format = ACCOUNTING
        for name in ("Python_Status", "Workbook_Status"):
            col = headers.get(name)
            if not col:
                continue
            cell = sheet.cell(row, col)
            _status_cell(cell, str(cell.value or ""))
    _set_width(sheet, headers.get("Control_ID"), 26)
    _set_width(sheet, headers.get("Message"), 70)


def _mapping_sheet(sheet) -> None:
    _standard_header(sheet)
    headers = {str(cell.value): cell.column for cell in sheet[1] if cell.value}
    for row in range(2, sheet.max_row + 1):
        for cell in sheet[row]:
            cell.font = Font(name="Arial", size=9, color=INPUT_BLUE)
        status_col = headers.get("Review_Status")
        if status_col:
            status = str(sheet.cell(row, status_col).value or "")
            if status.upper() != "REVIEWED":
                for cell in sheet[row]:
                    cell.fill = PatternFill("solid", fgColor=AMBER)
    _set_width(sheet, headers.get("Source_Label"), 30)
    _set_width(sheet, headers.get("Reason"), 55)


def _unmapped_sheet(sheet) -> None:
    _standard_header(sheet, "C65911")
    sheet.sheet_properties.tabColor = "C65911"
    for row in range(2, sheet.max_row + 1):
        for cell in sheet[row]:
            cell.fill = PatternFill("solid", fgColor=AMBER)
            cell.font = Font(name="Arial", size=9, color=BLACK)
    _reasonable_widths(sheet, max_width=38)


def _scope_excluded_sheet(sheet) -> None:
    _standard_header(sheet, SOURCE_GREY)
    sheet.sheet_properties.tabColor = SOURCE_GREY
    for row in range(2, sheet.max_row + 1):
        for cell in sheet[row]:
            cell.fill = PatternFill("solid", fgColor="F2F2F2")
            cell.font = Font(name="Arial", size=9, color=BLACK)
            if isinstance(cell.value, (int, float)):
                cell.number_format = ACCOUNTING
    _reasonable_widths(sheet, max_width=36)


def _findings_sheet(sheet) -> None:
    _standard_header(sheet)
    sheet.sheet_properties.tabColor = MEDIUM_BLUE
    headers = {str(cell.value): cell.column for cell in sheet[1] if cell.value}
    priority_col = headers.get("Priority")
    evidence_col = headers.get("Evidence")
    finding_col = headers.get("Finding")
    for row in range(2, sheet.max_row + 1):
        priority = str(sheet.cell(row, priority_col).value or "").upper() if priority_col else ""
        fill = HIGH_FILL if priority == "HIGH" else MEDIUM_FILL if priority == "MEDIUM" else "FFFFFF"
        for cell in sheet[row]:
            cell.fill = PatternFill("solid", fgColor=fill)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
        sheet.row_dimensions[row].height = 36
    _set_width(sheet, priority_col, 12)
    _set_width(sheet, finding_col, 34)
    _set_width(sheet, evidence_col, 78)


def _questions_sheet(sheet) -> None:
    _standard_header(sheet)
    sheet.sheet_properties.tabColor = MEDIUM_BLUE
    headers = {str(cell.value): cell.column for cell in sheet[1] if cell.value}
    priority_col = headers.get("Priority")
    question_col = headers.get("Management question") or headers.get("Question")
    rationale_col = headers.get("Why we are asking") or headers.get("Rationale")
    for row in range(2, sheet.max_row + 1):
        priority = str(sheet.cell(row, priority_col).value or "").upper() if priority_col else ""
        fill = HIGH_FILL if priority == "HIGH" else MEDIUM_FILL if priority == "MEDIUM" else "FFFFFF"
        for cell in sheet[row]:
            cell.fill = PatternFill("solid", fgColor=fill)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
        sheet.row_dimensions[row].height = 56
    _set_width(sheet, priority_col, 12)
    _set_width(sheet, question_col, 78)
    _set_width(sheet, rationale_col, 62)


def _status_cell(cell, status: str) -> None:
    status = status.upper()
    if status == "PASS":
        cell.fill = PatternFill("solid", fgColor=PASS_FILL)
        cell.font = Font(name="Arial", size=10, bold=True, color=PASS_FONT)
    elif status == "FAIL":
        cell.fill = PatternFill("solid", fgColor=FAIL_FILL)
        cell.font = Font(name="Arial", size=10, bold=True, color=FAIL_FONT)
    elif status == "REVIEW_REQUIRED":
        cell.fill = PatternFill("solid", fgColor=AMBER)
        cell.font = Font(name="Arial", size=10, bold=True, color=AMBER_FONT)
    elif status == "NOT_APPLICABLE":
        cell.fill = PatternFill("solid", fgColor=LIGHT_GREY)
        cell.font = Font(name="Arial", size=10, bold=True, color=SOURCE_GREY)


def _reasonable_widths(sheet, *, max_width: int = 40) -> None:
    for col in range(1, sheet.max_column + 1):
        width = 10
        for row in range(1, min(sheet.max_row, 120) + 1):
            value = sheet.cell(row, col).value
            if value is not None:
                width = max(width, min(max_width, len(str(value)) + 2))
        sheet.column_dimensions[get_column_letter(col)].width = width


def _set_width(sheet, column: int | None, width: int) -> None:
    if column:
        sheet.column_dimensions[get_column_letter(column)].width = width
