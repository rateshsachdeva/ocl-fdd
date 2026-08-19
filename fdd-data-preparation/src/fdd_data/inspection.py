"""Bounded, read-only targeted inspection for known Stage 2 sources."""

from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path
from typing import Any

from openpyxl.utils.cell import range_boundaries

from .discovery import sha256_file
from .source_data import open_source_workbook


class InspectionError(ValueError):
    """Raised when an inspection request cannot be resolved from a profile."""


def inspect_source(
    profile_path: Path,
    source_id: str,
    worksheet_name: str,
    *,
    region_id: str | None = None,
    row_range: tuple[int, int] | None = None,
    column_range: tuple[int, int] | None = None,
    max_cells: int = 1_000,
) -> dict[str, Any]:
    """Return a bounded, immutable view of a known profiled source area.

    Values are returned as stored by ``openpyxl``. This function never saves,
    recalculates, or otherwise modifies the source workbook.
    """
    profile = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    source = next((item for item in profile["source_files"] if item["source_id"] == source_id), None)
    if source is None:
        raise InspectionError(f"Unknown source_id: {source_id}")
    workbook_profile = next(
        (item for item in profile["workbook_profiles"] if item["source_id"] == source_id), None
    )
    worksheet_profile = next(
        (
            item
            for item in (workbook_profile or {}).get("worksheet_profiles", [])
            if item["worksheet_name"] == worksheet_name
        ),
        None,
    )
    if worksheet_profile is None:
        raise InspectionError(f"Unknown worksheet for {source_id}: {worksheet_name}")

    region = None
    if region_id:
        region = next(
            (item for item in worksheet_profile["data_regions"] if item["region_id"] == region_id), None
        )
        if region is None:
            raise InspectionError(f"Unknown region for {source_id}/{worksheet_name}: {region_id}")

    min_column, min_row, max_column, max_row = _resolve_bounds(
        worksheet_profile, region, row_range, column_range
    )
    cell_count = (max_row - min_row + 1) * (max_column - min_column + 1)
    if cell_count > max_cells:
        raise InspectionError(f"Requested {cell_count} cells; max_cells is {max_cells}.")

    source_path = Path(source["path"])
    before_hash = sha256_file(source_path)
    workbook = open_source_workbook(source_path, read_only=False)
    worksheet = workbook[worksheet_name]
    cells = []
    for row in worksheet.iter_rows(min_row=min_row, max_row=max_row, min_col=min_column, max_col=max_column):
        for cell in row:
            if cell.value is None:
                continue
            cells.append(
                {
                    "cell": cell.coordinate,
                    "row": cell.row,
                    "column": cell.column,
                    "value": _json_value(cell.value),
                    "data_type": cell.data_type,
                    "number_format": cell.number_format,
                    "indent": cell.alignment.indent or 0,
                }
            )
    after_hash = sha256_file(source_path)
    if before_hash != after_hash or after_hash != source["sha256"]:
        raise InspectionError("Source SHA-256 changed during inspection; results must be reviewed.")
    workbook.close()
    return {
        "profile_run_id": profile["run_id"],
        "source_id": source_id,
        "filename": source["filename"],
        "worksheet_name": worksheet_name,
        "region_id": region_id,
        "bounds": {"min_row": min_row, "max_row": max_row, "min_column": min_column, "max_column": max_column},
        "cells": cells,
        "source_sha256_verified": True,
    }


def _resolve_bounds(
    worksheet: dict[str, Any],
    region: dict[str, Any] | None,
    row_range: tuple[int, int] | None,
    column_range: tuple[int, int] | None,
) -> tuple[int, int, int, int]:
    if region:
        min_column, min_row, max_column, max_row = range_boundaries(region["cell_range"])
    elif worksheet["meaningful_bounds"]:
        min_column, min_row, max_column, max_row = range_boundaries(worksheet["meaningful_bounds"])
    else:
        raise InspectionError("Worksheet has no meaningful populated bounds.")
    if row_range:
        min_row, max_row = row_range
    if column_range:
        min_column, max_column = column_range
    if min_row < 1 or min_column < 1 or max_row < min_row or max_column < min_column:
        raise InspectionError("Invalid row or column range.")
    return min_column, min_row, max_column, max_row


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
