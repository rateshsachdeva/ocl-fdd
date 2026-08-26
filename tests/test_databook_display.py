from datetime import date
from pathlib import Path
from types import SimpleNamespace

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font

from ocl_agent.databook_display import apply_databook_display_preferences


def _handoff():
    return SimpleNamespace(
        monthly_to_annual=(
            SimpleNamespace(annual_period="FY25", monthly_period="2025-12"),
        )
    )


def _build_balance_sheet(workbook, title: str, period: str):
    sheet = workbook.create_sheet(title)
    sheet.sheet_view.showGridLines = True
    sheet["B7"] = "Category"
    sheet["C7"] = period
    sheet["B8"] = "Bonus accrual"
    sheet["C8"] = "=100"
    sheet["C8"].font = Font(name="Arial", size=8, color="008000")
    sheet["B9"] = "Holiday pay"
    sheet["C9"] = "=200"
    sheet["C9"].font = Font(name="Arial", size=8, color="008000")
    sheet["B10"] = "Employee accruals"
    sheet["C10"] = "=SUM(C8:C9)"
    sheet["C10"].font = Font(name="Arial", size=8, color="008000")
    sheet["B11"] = "Total OCL"
    sheet["C11"] = "=C8+C9"
    sheet["C11"].font = Font(name="Arial", size=8, color="008000")
    return sheet


def test_display_preferences_black_dates_no_gridlines_total_fill_and_redundant_subtotal(tmp_path: Path):
    path = tmp_path / "OCL_Databook.xlsx"
    workbook = Workbook()
    workbook.remove(workbook.active)
    _build_balance_sheet(workbook, "Balance by Category", "FY25")
    _build_balance_sheet(workbook, "Monthly Balance", "2025-12")
    workbook.save(path)

    apply_databook_display_preferences(path, _handoff())

    workbook = load_workbook(path)
    for sheet_name in ("Balance by Category", "Monthly Balance"):
        sheet = workbook[sheet_name]
        assert sheet.sheet_view.showGridLines is False
        assert sheet.print_options.gridLines is False
        assert sheet["C7"].value == date(2025, 12, 31)
        assert sheet["C7"].number_format == "dd-mmm-yy"
        assert sheet["C8"].font.color.type == "rgb"
        assert sheet["C8"].font.color.rgb.endswith("000000")
        assert sheet.row_dimensions[10].hidden is True
        assert sheet["B11"].fill.fgColor.rgb.endswith("E5E5E5")
        assert sheet["C11"].fill.fgColor.rgb.endswith("E5E5E5")
        assert sheet["C11"].font.color.rgb.endswith("000000")
    workbook.close()


def test_nonredundant_parent_subtotals_remain_visible(tmp_path: Path):
    path = tmp_path / "OCL_Databook.xlsx"
    workbook = Workbook()
    workbook.remove(workbook.active)
    sheet = workbook.create_sheet("Balance by Category")
    sheet["B7"] = "Category"
    sheet["C7"] = "FY25"
    sheet["B8"] = "Bonus accrual"
    sheet["C8"] = "=100"
    sheet["B9"] = "Holiday pay"
    sheet["C9"] = "=200"
    sheet["B10"] = "Employee accruals"
    sheet["C10"] = "=SUM(C8:C9)"
    sheet["B11"] = "VAT payable"
    sheet["C11"] = "=150"
    sheet["B12"] = "Total OCL"
    sheet["C12"] = "=C8+C9+C11"
    workbook.save(path)

    apply_databook_display_preferences(path, _handoff())

    workbook = load_workbook(path)
    sheet = workbook["Balance by Category"]
    assert sheet.row_dimensions[10].hidden is False
    assert sheet["B12"].fill.fgColor.rgb.endswith("E5E5E5")
    workbook.close()
