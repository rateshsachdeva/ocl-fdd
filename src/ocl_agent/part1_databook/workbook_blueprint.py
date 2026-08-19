"""Dynamic workbook blueprint: what exists, never a fixed legacy layout."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from ocl_agent.schemas import OCLRecord, Scope


@dataclass(frozen=True)
class SheetBlueprint:
    key: str
    title: str
    purpose: str
    periods: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    required: bool = False
    dataset_file: str | None = None


@dataclass(frozen=True)
class WorkbookBlueprint:
    sheets: tuple[SheetBlueprint, ...]
    periods: tuple[str, ...]
    monthly_periods: tuple[str, ...]
    categories: tuple[str, ...]
    hierarchy: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def sheet_keys(self) -> tuple[str, ...]:
        return tuple(sheet.key for sheet in self.sheets)


def build_blueprint(records: Iterable[OCLRecord], *, source_dataset_files: Iterable[str] = (), has_rollforward_data: bool = False, supported_analyses: Iterable[str] = ()) -> WorkbookBlueprint:
    rows = tuple(records)
    annual_rows = tuple(row for row in rows if row.dimensions.get("record_usage") != "MONTHLY_RECORDS")
    monthly_rows = tuple(row for row in rows if row.dimensions.get("record_usage") == "MONTHLY_RECORDS")
    annual_in_scope = tuple(row for row in annual_rows if row.judgment.scope == Scope.IN_SCOPE)
    monthly_in_scope = tuple(row for row in monthly_rows if row.judgment.scope == Scope.IN_SCOPE)
    all_in_scope = annual_in_scope + monthly_in_scope
    periods = tuple(sorted({row.period for row in annual_in_scope}))
    monthly_periods = tuple(sorted({row.period for row in monthly_in_scope}))
    categories = tuple(sorted({row.judgment.category for row in all_in_scope if row.judgment.category}))
    hierarchy_sets: dict[str, set[str]] = {}
    for row in all_in_scope:
        if row.judgment.parent_category and row.judgment.category:
            hierarchy_sets.setdefault(row.judgment.parent_category, set()).add(row.judgment.category)
    hierarchy = {parent: tuple(sorted(children)) for parent, children in sorted(hierarchy_sets.items())}
    sheets: list[SheetBlueprint] = []
    if rows:
        sheets.append(SheetBlueprint("flat_file", "Flat File", "Auditable OCL record model with source-linked amounts.", required=True))
    if annual_in_scope:
        sheets.append(SheetBlueprint("balance_by_category", "Balance by Category", "Period-end OCL balance by actual hierarchy and period.", periods, categories, True))
    if monthly_rows:
        sheets.append(SheetBlueprint("monthly_flat", "Monthly Flat", "Monthly OCL record model.", monthly_periods, categories, True))
    if monthly_in_scope:
        sheets.append(SheetBlueprint("monthly_balance", "Monthly Balance", "Monthly OCL balance by actual category and month.", monthly_periods, categories))
    sheets.extend([
        SheetBlueprint("checks", "Checks", "Mandatory reconciliation and control results.", required=True),
        SheetBlueprint("mapping", "Mapping", "Visible reviewed and unresolved mapping decisions.", required=True),
        SheetBlueprint("unmapped", "UNMAPPED", "In-scope labels without a reviewed category.", required=True),
        SheetBlueprint("scope_excluded", "SCOPE_EXCLUDED", "Rows excluded from OCL with retained lineage.", required=True),
    ])
    if has_rollforward_data and all_in_scope:
        sheets.append(SheetBlueprint("rollforward", "Roll-forward", "Roll-forward supported by available movement data.", periods, categories))
    allowed_analyses = {
        "seasonality": ("Seasonality", "Seasonality supported by reconciled monthly data."),
        "concentration": ("Concentration", "Concentration supported by available dimensions."),
        "aging": ("Aging", "Aging supported by source aging fields."),
    }
    for key in supported_analyses:
        if key in allowed_analyses:
            title, purpose = allowed_analyses[key]
            sheets.append(SheetBlueprint(key, title, purpose, periods or monthly_periods, categories))
    used_titles = {sheet.title.casefold() for sheet in sheets}
    for index, filename in enumerate(source_dataset_files, start=1):
        title = _source_title(filename, index, used_titles)
        used_titles.add(title.casefold())
        sheets.append(SheetBlueprint(f"source_{index}", title, f"Protected standardized source copy: {filename}", required=True, dataset_file=filename))
    return WorkbookBlueprint(tuple(sheets), periods, monthly_periods, categories, hierarchy)


def _source_title(filename: str, index: int, used: set[str]) -> str:
    stem = "".join(character if character.isalnum() else "_" for character in Path(filename).stem).strip("_") or str(index)
    base = ("SRC_" + stem)[:31]
    candidate = base
    suffix = 2
    while candidate.casefold() in used:
        marker = f"_{suffix}"
        candidate = base[: 31 - len(marker)] + marker
        suffix += 1
    return candidate
