"""Dynamic workbook blueprint.

The blueprint determines *what* exists.  Rendering/styling determines *how* it
looks.  No sheet, period, category or analysis is created merely to preserve a
legacy layout.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class WorkbookBlueprint:
    sheets: tuple[SheetBlueprint, ...]
    periods: tuple[str, ...]
    categories: tuple[str, ...]
    hierarchy: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def sheet_keys(self) -> tuple[str, ...]:
        return tuple(sheet.key for sheet in self.sheets)


def build_blueprint(
    records: Iterable[OCLRecord],
    *,
    has_monthly_data: bool = False,
    has_rollforward_data: bool = False,
    supported_analyses: Iterable[str] = (),
) -> WorkbookBlueprint:
    rows = tuple(records)
    in_scope = tuple(row for row in rows if row.judgment.scope == Scope.IN_SCOPE)
    periods = tuple(sorted({row.period for row in in_scope}))
    categories = tuple(sorted({row.judgment.category for row in in_scope if row.judgment.category}))

    hierarchy_sets: dict[str, set[str]] = {}
    for row in in_scope:
        parent = row.judgment.parent_category
        child = row.judgment.category
        if parent and child:
            hierarchy_sets.setdefault(parent, set()).add(child)
    hierarchy = {parent: tuple(sorted(children)) for parent, children in sorted(hierarchy_sets.items())}

    sheets: list[SheetBlueprint] = [
        SheetBlueprint("checks", "Checks", "Mandatory reconciliation and control results.", required=True),
        SheetBlueprint("mapping", "Mapping", "Visible reviewed and unresolved mapping decisions.", required=True),
        SheetBlueprint("unmapped", "UNMAPPED", "In-scope labels without a reviewed category.", required=True),
        SheetBlueprint("scope_excluded", "SCOPE_EXCLUDED", "Rows excluded from OCL with retained lineage.", required=True),
    ]
    if in_scope:
        sheets.insert(0, SheetBlueprint("ocl_balance", "OCL Balance", "Dynamic OCL balance by actual hierarchy and period.", periods, categories, True))
    if has_monthly_data and in_scope:
        sheets.append(SheetBlueprint("monthly", "Monthly OCL", "Monthly OCL analysis supported by available monthly data.", periods, categories))
    if has_rollforward_data and in_scope:
        sheets.append(SheetBlueprint("rollforward", "Roll-forward", "Roll-forward analysis supported by available movement data.", periods, categories))

    allowed_analysis_keys = {
        "seasonality": ("Seasonality", "Seasonality analysis supported by reconciled monthly data."),
        "concentration": ("Concentration", "Concentration analysis supported by the available dimensions."),
        "aging": ("Aging", "Aging analysis supported by source aging fields."),
    }
    for key in supported_analyses:
        if key in allowed_analysis_keys:
            title, purpose = allowed_analysis_keys[key]
            sheets.append(SheetBlueprint(key, title, purpose, periods, categories))

    return WorkbookBlueprint(tuple(sheets), periods, categories, hierarchy)
