"""Presentation-only styling for the final OCL databook.

The style layer may improve layout and review usability but must never create or
change categories, periods, financial values, controls or conclusions.
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

TITLE_NAVY = "002060"
KPMG_BLUE = "00338D"
LIGHT_GREY = "E1E4E2"
GRAND_TOTAL = "E5E5E5"
SOURCE_GREY = "808080"
NOTE_GREY = "7F7F7F"
INPUT_BLUE = "0000FF"
LINK_GREEN = "008000"
BLACK = "000000"
WHITE = "FFFFFF"
AMBER = "FFF2CC"
PASS_FILL = "C6EFCE"
PASS_FONT = "006100"
FAIL_FILL = "FFC7CE"
FAIL_FONT = "9C0006"
ACCOUNTING = '#,##0;[Red](#,##0);-'
PERCENT = '0.0%;[Red](0.0%);-'
MULTIPLE = '0.0x'
THIN_GREY = Side(style="thin", color="BFBFBF")
MEDIUM_BLUE = Side(style="medium", color=KPMG_BLUE)

FRONT_ORDER = [
    "Deal Issues", "Key Findings", "Q&A", "Checks", "Balance by Category",
    "Roll-forward", "Seasonality", "Item Monthly Charts", "Analysis Summary",
]
SUPPORT_ORDER = ["Flat File", "Movements", "TB", "Monthly Flat", "Monthly Balance", "Mapping", "UNMAPPED", "SCOPE_EXCLUDED"]


def apply_workbook_style(path: Path) -> Path:
    path = Path(path)
    workbook = load_workbook(path)
    for sheet in workbook.worksheets:
        _base_sheet(sheet)
        if sheet.title.startswith("SRC_"):
            _source_sheet(sheet)
        elif sheet.title in {"Flat File", "Monthly Flat"}:
            _flat_sheet(sheet)
        elif sheet.title in {"Balance by Category", "Monthly Balance"}:
            _balance_sheet(sheet)
        elif sheet.title == "Roll-forward":
            _rollforward_sheet(sheet)
        elif sheet.title == "Checks":
            _checks_sheet(sheet)
        elif sheet.title == "Mapping":
            _mapping_sheet(sheet)
        elif sheet.title == "UNMAPPED":
            _unmapped_sheet(sheet)
        elif sheet.title == "SCOPE_EXCLUDED":
            _scope_excluded_sheet(sheet)
        elif sheet.title in {"Analysis Summary", "Seasonality", "Item Monthly Charts", "Key Findings", "Q&A"}:
            _analysis_sheet(sheet)
        elif sheet.title == "Deal Issues":
            _deal_issues_sheet(sheet)
        else:
            _generic_sheet(sheet)
    _reorder_sheets(workbook)
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
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.page_margins.left = 0.25
    sheet.page_margins.right = 0.25
    sheet.page_margins.top = 0.5
    sheet.page_margins.bottom = 0.5
    for row in sheet.iter_rows():
        for cell in row:
            cell.font = Font(name="Arial", size=8, color=BLACK, bold=bool(cell.font.bold), italic=bool(cell.font.italic))
            cell.alignment = Alignment(vertical="center", wrap_text=False)
            if isinstance(cell.value, str) and cell.value.startswith("="):
                cell.font = Font(name="Arial", size=8, color=LINK_GREEN if "!" in cell.value else BLACK, bold=bool(cell.font.bold))
    if sheet.max_row:
        sheet.row_dimensions[1].height = 18


def _title(sheet, title_row: int = 1, subtitle_row: int | None = 2) -> None:
    if sheet.cell(title_row, 1).value not in (None, ""):
        sheet.cell(title_row, 1).font = Font(name="Arial", size=14, bold=True, color=TITLE_NAVY)
    if subtitle_row and sheet.cell(subtitle_row, 1).value not in (None, ""):
        sheet.cell(subtitle_row, 1).font = Font(name="Arial", size=8, bold=True, color=BLACK)


def _header_row(sheet, row: int, start_col: int = 1, end_col: int | None = None, *, blue: bool = False) -> None:
    end_col = end_col or sheet.max_column
    for col in range(start_col, end_col + 1):
        cell = sheet.cell(row, col)
        if cell.value in (None, "") and not blue:
            continue
        cell.fill = PatternFill("solid", fgColor=KPMG_BLUE if blue else LIGHT_GREY)
        cell.font = Font(name="Arial", size=8, bold=True, color=WHITE if blue else BLACK)
        cell.alignment = Alignment(vertical="center", horizontal="right" if col > start_col else "left", wrap_text=True)
        cell.border = Border(bottom=MEDIUM_BLUE if blue else THIN_GREY)


def _section_row(sheet, row: int, start_col: int = 2, end_col: int | None = None) -> None:
    end_col = end_col or max(start_col, sheet.max_column)
    for col in range(start_col, end_col + 1):
        cell = sheet.cell(row, col)
        cell.fill = PatternFill("solid", fgColor=KPMG_BLUE)
        cell.font = Font(name="Arial", size=8, bold=True, color=WHITE)
        cell.border = Border(bottom=MEDIUM_BLUE)


def _source_sheet(sheet) -> None:
    _header_row(sheet, 1, blue=False)
    sheet.sheet_properties.tabColor = SOURCE_GREY
    sheet.freeze_panes = "A2"
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name="Arial", size=8, color=INPUT_BLUE)
            if isinstance(cell.value, (int, float)):
                cell.number_format = ACCOUNTING
    sheet.protection.sheet = True
    _reasonable_widths(sheet, 28)


def _flat_sheet(sheet) -> None:
    _title(sheet, 1, None)
    _header_row(sheet, 2)
    sheet.freeze_panes = "A3"
    sheet.sheet_properties.tabColor = KPMG_BLUE
    headers = _headers(sheet, 2)
    amount_col = headers.get("Amount")
    for row in range(3, sheet.max_row + 1):
        for col in range(1, sheet.max_column + 1):
            cell = sheet.cell(row, col)
            if isinstance(cell.value, str) and cell.value.startswith("="):
                cell.font = Font(name="Arial", size=8, color=LINK_GREEN if "!" in cell.value else BLACK)
            else:
                cell.font = Font(name="Arial", size=8, color=INPUT_BLUE)
        if amount_col:
            sheet.cell(row, amount_col).number_format = ACCOUNTING
    _reasonable_widths(sheet, 34)
    _set_width(sheet, headers.get("Source_Record_ID"), 26)
    _set_width(sheet, headers.get("Source_Label"), 30)


def _balance_sheet(sheet) -> None:
    _title(sheet)
    sheet.column_dimensions["A"].width = 5
    _section_row(sheet, 6, 2, sheet.max_column)
    _header_row(sheet, 7, 2, sheet.max_column)
    sheet.freeze_panes = "B8"
    sheet.sheet_properties.tabColor = KPMG_BLUE
    for row in range(8, sheet.max_row + 1):
        label = str(sheet.cell(row, 2).value or "")
        formula_cells = [sheet.cell(row, col) for col in range(3, sheet.max_column + 1) if isinstance(sheet.cell(row, col).value, str) and sheet.cell(row, col).value.startswith("=")]
        is_total = label.casefold() in {"total ocl", "total mapped ocl", "total"}
        is_parent = bool(formula_cells) and any(str(cell.value).upper().startswith("=SUM(") for cell in formula_cells) and not is_total
        if is_total:
            for col in range(2, sheet.max_column + 1):
                cell = sheet.cell(row, col)
                cell.fill = PatternFill("solid", fgColor=GRAND_TOTAL)
                cell.font = Font(name="Arial", size=8, bold=True, color=BLACK)
                cell.border = Border(top=MEDIUM_BLUE, bottom=MEDIUM_BLUE)
        elif is_parent:
            for col in range(2, sheet.max_column + 1):
                cell = sheet.cell(row, col)
                cell.font = Font(name="Arial", size=8, bold=True, color=BLACK)
                cell.border = Border(top=THIN_GREY)
        else:
            sheet.cell(row, 2).alignment = Alignment(indent=1, vertical="center")
        for col in range(3, sheet.max_column + 1):
            cell = sheet.cell(row, col)
            cell.number_format = ACCOUNTING
            cell.alignment = Alignment(horizontal="right", vertical="center")
            if isinstance(cell.value, str) and cell.value.startswith("="):
                cell.font = Font(name="Arial", size=8, bold=is_parent or is_total, color=LINK_GREEN if "!" in cell.value else BLACK)
    sheet.column_dimensions["B"].width = 30
    for col in range(3, sheet.max_column + 1):
        sheet.column_dimensions[get_column_letter(col)].width = 13


def _rollforward_sheet(sheet) -> None:
    sheet.sheet_properties.tabColor = KPMG_BLUE
    header_row = _find_header(sheet, "Category") or 1
    if header_row == 1:
        _header_row(sheet, 1, blue=True)
        sheet.freeze_panes = "A2"
    else:
        _title(sheet)
        _section_row(sheet, header_row - 1, 2, sheet.max_column)
        _header_row(sheet, header_row, 2, sheet.max_column)
        sheet.freeze_panes = f"B{header_row + 1}"
    for row in range(header_row + 1, sheet.max_row + 1):
        for col in range(2, sheet.max_column + 1):
            cell = sheet.cell(row, col)
            if isinstance(cell.value, (int, float)) or (isinstance(cell.value, str) and cell.value.startswith("=")):
                cell.number_format = ACCOUNTING
    _reasonable_widths(sheet, 24)


def _checks_sheet(sheet) -> None:
    _title(sheet, 1, 2)
    sheet.cell(2, 1).font = Font(name="Arial", size=8, color=NOTE_GREY)
    _header_row(sheet, 4)
    sheet.freeze_panes = "A5"
    sheet.sheet_properties.tabColor = KPMG_BLUE
    headers = _headers(sheet, 4)
    for row in range(5, sheet.max_row + 1):
        for name in ("Python_Actual", "Python_Expected", "Python_Difference", "Workbook_Difference"):
            col = headers.get(name)
            if col:
                sheet.cell(row, col).number_format = ACCOUNTING
        for name in ("Python_Status", "Workbook_Status"):
            col = headers.get(name)
            if col:
                _status_cell(sheet.cell(row, col), str(sheet.cell(row, col).value or ""))
    _set_width(sheet, headers.get("Control_ID"), 26)
    _set_width(sheet, headers.get("Message"), 70)


def _mapping_sheet(sheet) -> None:
    _title(sheet, 1, None)
    _header_row(sheet, 2)
    sheet.freeze_panes = "A3"
    headers = _headers(sheet, 2)
    for row in range(3, sheet.max_row + 1):
        for col in range(1, sheet.max_column + 1):
            sheet.cell(row, col).font = Font(name="Arial", size=8, color=INPUT_BLUE)
        status_col = headers.get("Review_Status")
        if status_col and str(sheet.cell(row, status_col).value or "").upper() != "REVIEWED":
            for col in range(1, sheet.max_column + 1):
                sheet.cell(row, col).fill = PatternFill("solid", fgColor=AMBER)
    _reasonable_widths(sheet, 36)
    _set_width(sheet, headers.get("Reason"), 55)


def _unmapped_sheet(sheet) -> None:
    _title(sheet, 1, 2)
    sheet.cell(2, 1).font = Font(name="Arial", size=8, color=NOTE_GREY)
    _header_row(sheet, 3)
    sheet.freeze_panes = "A4"
    sheet.sheet_properties.tabColor = "C65911"
    headers = _headers(sheet, 3)
    amount_col = headers.get("Amount")
    source_col = headers.get("Source_Dataset")
    for row in range(4, sheet.max_row + 1):
        for col in range(1, sheet.max_column + 1):
            cell = sheet.cell(row, col)
            cell.fill = PatternFill("solid", fgColor=AMBER)
            cell.font = Font(name="Arial", size=8, color=NOTE_GREY if col == source_col else BLACK)
        if amount_col:
            sheet.cell(row, amount_col).number_format = ACCOUNTING
    _reasonable_widths(sheet, 38)


def _scope_excluded_sheet(sheet) -> None:
    _title(sheet, 1, None)
    _header_row(sheet, 2)
    sheet.freeze_panes = "A3"
    sheet.sheet_properties.tabColor = SOURCE_GREY
    headers = _headers(sheet, 2)
    amount_col = headers.get("Amount")
    for row in range(3, sheet.max_row + 1):
        if amount_col:
            sheet.cell(row, amount_col).number_format = ACCOUNTING
    _reasonable_widths(sheet, 36)


def _analysis_sheet(sheet) -> None:
    _title(sheet)
    sheet.column_dimensions["A"].width = 5
    sheet.sheet_properties.tabColor = KPMG_BLUE
    sheet.freeze_panes = "B8"
    section_rows = [row for row in range(3, sheet.max_row + 1) if sheet.cell(row, 2).value not in (None, "") and all(sheet.cell(row, col).value in (None, "") for col in range(3, min(sheet.max_column, 8) + 1))]
    for row in section_rows:
        if row + 1 <= sheet.max_row:
            _section_row(sheet, row, 2, sheet.max_column)
            _header_row(sheet, row + 1, 2, sheet.max_column)
    if sheet.title in {"Key Findings", "Q&A", "Analysis Summary", "Seasonality", "Item Monthly Charts"}:
        _section_row(sheet, 6, 2, sheet.max_column)
        _header_row(sheet, 7, 2, sheet.max_column)
    for row in range(8, sheet.max_row + 1):
        wrap = sheet.title in {"Key Findings", "Q&A"}
        for col in range(2, sheet.max_column + 1):
            cell = sheet.cell(row, col)
            if isinstance(cell.value, str) and cell.value.startswith("="):
                cell.font = Font(name="Arial", size=8, color=LINK_GREEN if "!" in cell.value else BLACK)
            numeric = _numeric_like(cell)
            cell.alignment = Alignment(vertical="top" if wrap else "center", horizontal="right" if numeric else "left", wrap_text=wrap)
            if numeric:
                if "%" in str(sheet.cell(7, col).value or "") or "Magnitude" == str(sheet.cell(7, col).value or ""):
                    cell.number_format = PERCENT
                else:
                    cell.number_format = ACCOUNTING
        if wrap:
            sheet.row_dimensions[row].height = min(120, max(24, 12 + 12 * max(1, _wrapped_lines(sheet, row))))
    headers = _headers(sheet, 7)
    flag_col = headers.get("Flag") or headers.get("Review Flag")
    if flag_col:
        for row in range(8, sheet.max_row + 1):
            if sheet.cell(row, flag_col).value not in (None, ""):
                sheet.cell(row, flag_col).fill = PatternFill("solid", fgColor=AMBER)
    _analysis_widths(sheet)


def _deal_issues_sheet(sheet) -> None:
    _title(sheet)
    sheet.sheet_properties.tabColor = KPMG_BLUE
    sheet.freeze_panes = "A4"
    for row in range(4, sheet.max_row + 1):
        first = sheet.cell(row, 1)
        if first.value and row % 5 == 4:
            first.font = Font(name="Arial", size=8, bold=True, color=BLACK)
        if row % 5 == 0:
            first.alignment = Alignment(vertical="top", wrap_text=True)
            sheet.row_dimensions[row].height = 42
        if row % 5 == 1 and sheet.cell(row, 2).value not in (None, ""):
            sheet.cell(row, 1).font = Font(name="Arial", size=8, color=NOTE_GREY)
            sheet.cell(row, 2).font = Font(name="Arial", size=8, bold=True, color=LINK_GREEN if isinstance(sheet.cell(row, 2).value, str) and "!" in sheet.cell(row, 2).value else BLACK)
            sheet.cell(row, 2).number_format = ACCOUNTING
    sheet.column_dimensions["A"].width = 34
    sheet.column_dimensions["B"].width = 20
    sheet.column_dimensions["C"].width = 18
    sheet.column_dimensions["D"].width = 18


def _generic_sheet(sheet) -> None:
    _header_row(sheet, 1)
    _reasonable_widths(sheet, 30)


def _status_cell(cell, status: str) -> None:
    status = status.upper()
    if status == "PASS":
        cell.fill = PatternFill("solid", fgColor=PASS_FILL)
        cell.font = Font(name="Arial", size=8, bold=True, color=PASS_FONT)
    elif status == "FAIL":
        cell.fill = PatternFill("solid", fgColor=FAIL_FILL)
        cell.font = Font(name="Arial", size=8, bold=True, color=FAIL_FONT)
    elif status == "REVIEW_REQUIRED":
        cell.fill = PatternFill("solid", fgColor=AMBER)
        cell.font = Font(name="Arial", size=8, bold=True, color=BLACK)
    elif status == "NOT_APPLICABLE":
        cell.fill = PatternFill("solid", fgColor=LIGHT_GREY)
        cell.font = Font(name="Arial", size=8, bold=True, color=NOTE_GREY)


def _headers(sheet, row: int) -> dict[str, int]:
    return {str(sheet.cell(row, col).value): col for col in range(1, sheet.max_column + 1) if sheet.cell(row, col).value not in (None, "")}


def _find_header(sheet, value: str) -> int | None:
    wanted = value.casefold()
    for row in range(1, min(sheet.max_row, 12) + 1):
        for col in range(1, min(sheet.max_column, 6) + 1):
            if str(sheet.cell(row, col).value or "").strip().casefold() == wanted:
                return row
    return None


def _numeric_like(cell) -> bool:
    if isinstance(cell.value, (int, float)):
        return True
    return cell.column > 2 and isinstance(cell.value, str) and cell.value.startswith("=")


def _wrapped_lines(sheet, row: int) -> int:
    total = 1
    for col in range(2, sheet.max_column + 1):
        text = str(sheet.cell(row, col).value or "")
        total = max(total, max(1, len(text) // 55 + 1))
    return total


def _analysis_widths(sheet) -> None:
    for col in range(2, sheet.max_column + 1):
        header = str(sheet.cell(7, col).value or "")
        width = 14
        if header in {"So what", "Evidence", "Ask management", "Question", "Management response"}:
            width = 42
        elif header in {"Theme", "Area", "Metric", "FY periods / Item"}:
            width = 22
        elif header in {"Category"}:
            width = 28
        sheet.column_dimensions[get_column_letter(col)].width = width


def _reasonable_widths(sheet, max_width: int = 40) -> None:
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


def _reorder_sheets(workbook) -> None:
    ordered_names: list[str] = []
    for name in FRONT_ORDER + SUPPORT_ORDER:
        if name in workbook.sheetnames and name not in ordered_names:
            ordered_names.append(name)
    for name in workbook.sheetnames:
        if name.startswith("SRC_") and name not in ordered_names:
            ordered_names.append(name)
    for name in workbook.sheetnames:
        if name not in ordered_names:
            ordered_names.append(name)
    workbook._sheets = [workbook[name] for name in ordered_names]
