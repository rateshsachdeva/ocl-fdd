"""Deterministic Excel renderer for a dynamic workbook blueprint.

This is deliberately a renderer, not an accounting decision engine.  It does
not create categories or analyses that are absent from the blueprint.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from openpyxl import Workbook

from ocl_agent.part1_databook.workbook_blueprint import WorkbookBlueprint
from ocl_agent.schemas import ControlResult, OCLRecord


def render_workbook(
    blueprint: WorkbookBlueprint,
    records: Iterable[OCLRecord],
    controls: Iterable[ControlResult],
    output_path: Path,
) -> Path:
    rows = tuple(records)
    checks = tuple(controls)
    workbook = Workbook()
    workbook.remove(workbook.active)

    for sheet_spec in blueprint.sheets:
        sheet = workbook.create_sheet(sheet_spec.title)
        sheet.sheet_view.showGridLines = False
        if sheet_spec.key == "checks":
            sheet.append(["Control_ID", "Status", "Actual", "Expected", "Difference", "Message"])
            for check in checks:
                sheet.append([check.control_id, check.status.value, check.actual, check.expected, check.difference, check.message])
        elif sheet_spec.key == "mapping":
            sheet.append(["Source_Label", "Scope", "Category", "Parent_Category", "Review_Status", "Reason"])
            seen = set()
            for row in rows:
                key = row.source_label.casefold().strip()
                if key in seen:
                    continue
                seen.add(key)
                judgment = row.judgment
                sheet.append([
                    row.source_label,
                    judgment.scope.value,
                    judgment.category,
                    judgment.parent_category,
                    judgment.review_status.value,
                    judgment.reason,
                ])
        elif sheet_spec.key == "unmapped":
            sheet.append(["Source_Record_ID", "Period", "Source_Label", "Amount", "Source_File", "Source_Sheet", "Source_Cell"])
            for row in rows:
                if row.judgment.scope.value == "IN_SCOPE" and not row.judgment.category:
                    sheet.append([row.source.source_record_id, row.period, row.source_label, row.amount, row.source.source_file, row.source.source_sheet, row.source.source_cell])
        elif sheet_spec.key == "scope_excluded":
            sheet.append(["Source_Record_ID", "Period", "Source_Label", "Scope", "Amount", "Source_File", "Source_Sheet", "Source_Cell"])
            for row in rows:
                if row.judgment.scope.value != "IN_SCOPE":
                    sheet.append([row.source.source_record_id, row.period, row.source_label, row.judgment.scope.value, row.amount, row.source.source_file, row.source.source_sheet, row.source.source_cell])
        elif sheet_spec.key == "ocl_balance":
            sheet.append(["Category", *sheet_spec.periods])
            for category in sheet_spec.categories:
                values = []
                for period in sheet_spec.periods:
                    values.append(sum((row.amount for row in rows if row.period == period and row.judgment.category == category and row.judgment.scope.value == "IN_SCOPE"), 0))
                sheet.append([category, *values])
        else:
            # Analytical sheets are only created if the blueprint supports them.
            # Their Part 2 population is intentionally separate from Part 1.
            sheet.append(["Analysis", "Status"])
            sheet.append([sheet_spec.title, "SUPPORTED_BY_BLUEPRINT"])
        sheet.freeze_panes = "A2"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)
    return output_path
