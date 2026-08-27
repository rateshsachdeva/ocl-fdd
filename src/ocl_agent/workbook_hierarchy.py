"""Reusable workbook hierarchy ordering and outline helpers.

These helpers affect presentation only.  They keep every economic detail row
in the workbook while presenting parent-first, collapsed Excel outlines.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Mapping


@dataclass(frozen=True)
class HierarchyEntry:
    label: str
    kind: str
    children: tuple[str, ...] = ()


def ordered_hierarchy(
    categories: Iterable[str],
    hierarchy: Mapping[str, tuple[str, ...]],
    latest_values: Mapping[str, Decimal],
) -> tuple[HierarchyEntry, ...]:
    """Return parent/standalone groups ordered by latest-period balance."""
    child_set = {child for children in hierarchy.values() for child in children}
    entries = [HierarchyEntry(parent, "parent", tuple(children)) for parent, children in hierarchy.items()]
    entries.extend(
        HierarchyEntry(category, "standalone")
        for category in categories
        if category not in child_set and category not in hierarchy
    )

    def score(entry: HierarchyEntry) -> Decimal:
        if entry.kind == "parent":
            return sum((latest_values.get(child, Decimal("0")) for child in entry.children), Decimal("0"))
        return latest_values.get(entry.label, Decimal("0"))

    return tuple(sorted(entries, key=lambda entry: (-score(entry), entry.label.casefold())))


def apply_collapsed_detail_group(sheet, parent_row: int, first_child_row: int, last_child_row: int) -> None:
    """Group detail beneath a visible parent and collapse it by default."""
    if first_child_row > last_child_row:
        return
    sheet.sheet_properties.outlinePr.summaryBelow = False
    sheet.sheet_properties.outlinePr.showSummaryRight = True
    for row in range(first_child_row, last_child_row + 1):
        dimension = sheet.row_dimensions[row]
        dimension.outlineLevel = max(1, dimension.outlineLevel)
        dimension.hidden = True
    sheet.row_dimensions[parent_row].collapsed = True


def copy_row_outline(source, source_row: int, target, target_row: int) -> None:
    """Carry an existing hierarchy outline to a formula-linked analysis row."""
    source_dimension = source.row_dimensions[source_row]
    target_dimension = target.row_dimensions[target_row]
    target_dimension.outlineLevel = source_dimension.outlineLevel
    target_dimension.hidden = source_dimension.hidden
    target_dimension.collapsed = source_dimension.collapsed
    target.sheet_properties.outlinePr.summaryBelow = False
