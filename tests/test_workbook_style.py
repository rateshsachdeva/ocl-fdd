from __future__ import annotations

from collections import Counter, defaultdict

import pytest
from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from ocl_agent.workbook_style import _analysis_sheet, _flat_sheet


def _flat_sheet_with_rows(row_count: int) -> Worksheet:
    sheet = Workbook().active
    sheet.title = "Flat File"
    sheet.cell(1, 1, "Flat File")
    headers = ["Source_Record_ID", "Source_Label", "Category", "Period", "Amount"]
    for col, header in enumerate(headers, start=1):
        sheet.cell(2, col, header)
    for row in range(3, row_count + 3):
        sheet.cell(row, 1, f"SRC-{row}")
        sheet.cell(row, 2, "Dataset A")
        sheet.cell(row, 3, "Bonus")
        sheet.cell(row, 4, "FY2025")
        sheet.cell(row, 5, row)
    return sheet


def _analysis_sheet_with_rows(row_count: int) -> Worksheet:
    sheet = Workbook().active
    sheet.title = "Key Findings"
    sheet.cell(1, 1, "Key Findings")
    sheet.cell(6, 2, "Key Findings")
    headers = ["Area", "Metric", "FY periods / Item", "So what", "Evidence", "Ask management"]
    for col, header in enumerate(headers, start=2):
        sheet.cell(7, col, header)
    for row in range(8, row_count + 8):
        for col, value in enumerate(("Area", "Metric", "FY2025", "Implication", "Evidence", ""), start=2):
            sheet.cell(row, col, value)
    return sheet


@pytest.mark.parametrize(
    ("styler", "builder"),
    [
        (_flat_sheet, _flat_sheet_with_rows),
        (_analysis_sheet, _analysis_sheet_with_rows),
    ],
)
def test_dimension_property_reads_do_not_scale_with_data_rows(monkeypatch, styler, builder) -> None:
    small_sheet = builder(2)
    large_sheet = builder(250)
    reads: defaultdict[int, Counter[str]] = defaultdict(Counter)
    original_max_row = Worksheet.max_row
    original_max_column = Worksheet.max_column

    def counted_max_row(sheet: Worksheet) -> int:
        reads[id(sheet)]["max_row"] += 1
        return original_max_row.fget(sheet)

    def counted_max_column(sheet: Worksheet) -> int:
        reads[id(sheet)]["max_column"] += 1
        return original_max_column.fget(sheet)

    monkeypatch.setattr(Worksheet, "max_row", property(counted_max_row))
    monkeypatch.setattr(Worksheet, "max_column", property(counted_max_column))

    styler(small_sheet)
    styler(large_sheet)

    assert reads[id(large_sheet)] == reads[id(small_sheet)]
    assert 0 < reads[id(large_sheet)]["max_row"] <= 3
    assert 0 < reads[id(large_sheet)]["max_column"] <= 4
