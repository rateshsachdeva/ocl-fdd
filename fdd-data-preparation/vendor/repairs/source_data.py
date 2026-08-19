"""Utilities that reconnect a processing plan to exact source cells."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.utils.cell import range_boundaries

from .discovery import FULLY_PROFILEABLE_EXCEL_EXTENSIONS


class SourceDataError(ValueError):
    """Raised when exact source data cannot be read safely."""


@dataclass(slots=True)
class SourceCell:
    row: int
    column: int
    coordinate: str
    value: Any
    formula: str | None = None
    data_type: str | None = None
    number_format: str | None = None
    row_hidden: bool = False
    column_hidden: bool = False
    indentation_level: int = 0
    is_merged: bool = False
    merged_range: str | None = None


@dataclass(slots=True)
class SourceMatrix:
    source_id: str
    filename: str
    worksheet_name: str
    cell_range: str
    rows: list[list[SourceCell]]

    @property
    def start_row(self) -> int:
        return self.rows[0][0].row if self.rows and self.rows[0] else 0

    @property
    def end_row(self) -> int:
        return self.rows[-1][0].row if self.rows and self.rows[-1] else 0

    @property
    def start_column(self) -> int:
        return self.rows[0][0].column if self.rows and self.rows[0] else 0

    @property
    def end_column(self) -> int:
        return self.rows[0][-1].column if self.rows and self.rows[0] else 0


def read_source_matrix(
    *,
    source_file: Any,
    worksheet_name: str,
    cell_range: str,
) -> SourceMatrix:
    """Read the exact plan-referenced source range with formula provenance."""

    extension = str(getattr(source_file, "extension", "")).lower()
    if extension not in FULLY_PROFILEABLE_EXCEL_EXTENSIONS:
        raise SourceDataError(
            f"Exact source reads are not available for {extension or 'unknown format'}; "
            "convert the workbook first or use a supported OOXML format."
        )

    path = Path(getattr(source_file, "path", ""))
    if not path.exists():
        raise SourceDataError(f"Source file does not exist: {path}")

    try:
        min_column, min_row, max_column, max_row = range_boundaries(cell_range)
    except (TypeError, ValueError) as error:
        raise SourceDataError(f"Invalid source range: {cell_range}") from error

    formula_workbook = load_workbook(path, data_only=False, read_only=False)
    value_workbook = load_workbook(path, data_only=True, read_only=False)
    try:
        if worksheet_name not in formula_workbook.sheetnames:
            raise SourceDataError(f"Worksheet not found: {worksheet_name}")
        formula_sheet = formula_workbook[worksheet_name]
        value_sheet = value_workbook[worksheet_name]
        merged_lookup = _merged_lookup(formula_sheet)
        rows: list[list[SourceCell]] = []
        for row_number in range(min_row, max_row + 1):
            output_row: list[SourceCell] = []
            for column_number in range(min_column, max_column + 1):
                formula_cell = formula_sheet.cell(row=row_number, column=column_number)
                value_cell = value_sheet.cell(row=row_number, column=column_number)
                formula = (
                    formula_cell.value
                    if formula_cell.data_type == "f" or (isinstance(formula_cell.value, str) and formula_cell.value.startswith("="))
                    else None
                )
                value = value_cell.value if formula is not None else formula_cell.value
                output_row.append(
                    SourceCell(
                        row=row_number,
                        column=column_number,
                        coordinate=formula_cell.coordinate,
                        value=_serialize_value(value),
                        formula=formula,
                        data_type=str(formula_cell.data_type) if formula_cell.data_type is not None else None,
                        number_format=formula_cell.number_format,
                        row_hidden=bool(formula_sheet.row_dimensions[row_number].hidden),
                        column_hidden=bool(
                            formula_sheet.column_dimensions[formula_cell.column_letter].hidden
                        ),
                        indentation_level=int(formula_cell.alignment.indent or 0),
                        is_merged=formula_cell.coordinate in merged_lookup,
                        merged_range=merged_lookup.get(formula_cell.coordinate),
                    )
                )
            rows.append(output_row)
    finally:
        formula_workbook.close()
        value_workbook.close()

    return SourceMatrix(
        source_id=str(getattr(source_file, "source_id", "")),
        filename=str(getattr(source_file, "filename", path.name)),
        worksheet_name=worksheet_name,
        cell_range=cell_range,
        rows=rows,
    )


def row_values(matrix: SourceMatrix, row_number: int) -> list[Any]:
    """Return values for a 1-based source row inside the matrix."""

    for row in matrix.rows:
        if row and row[0].row == row_number:
            return [cell.value for cell in row]
    raise SourceDataError(
        f"Row {row_number} is outside source range {matrix.cell_range} on {matrix.worksheet_name}."
    )


def column_values(matrix: SourceMatrix, column_number: int) -> list[Any]:
    """Return values for a 1-based source column inside the matrix."""

    values: list[Any] = []
    for row in matrix.rows:
        for cell in row:
            if cell.column == column_number:
                values.append(cell.value)
                break
    if not values:
        raise SourceDataError(
            f"Column {column_number} is outside source range {matrix.cell_range} on {matrix.worksheet_name}."
        )
    return values


def cell_at(matrix: SourceMatrix, row_number: int, column_number: int) -> SourceCell:
    """Return one exact source cell from the loaded matrix."""

    for row in matrix.rows:
        for cell in row:
            if cell.row == row_number and cell.column == column_number:
                return cell
    raise SourceDataError(
        f"Cell r{row_number}c{column_number} is outside source range {matrix.cell_range} on {matrix.worksheet_name}."
    )


def _merged_lookup(worksheet: Any) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for merged_range in worksheet.merged_cells.ranges:
        range_text = str(merged_range)
        min_column, min_row, max_column, max_row = range_boundaries(range_text)
        for row_number in range(min_row, max_row + 1):
            for column_number in range(min_column, max_column + 1):
                lookup[worksheet.cell(row=row_number, column=column_number).coordinate] = range_text
    return lookup


def _serialize_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value
