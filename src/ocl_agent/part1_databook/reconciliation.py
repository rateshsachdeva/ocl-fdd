"""Reconciliation controls shared with the databook and independent tests."""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from ocl_agent.schemas import CheckStatus, ControlResult, OCLRecord, Scope

DEFAULT_TOLERANCE = Decimal("0.5")


def reconcile_amounts(
    control_id: str,
    actual: Decimal,
    expected: Decimal,
    *,
    tolerance: Decimal = DEFAULT_TOLERANCE,
    message: str = "",
) -> ControlResult:
    difference = actual - expected
    status = CheckStatus.PASS if abs(difference) < tolerance else CheckStatus.FAIL
    return ControlResult(control_id, status, actual, expected, difference, message)


def category_sum_control(records: Iterable[OCLRecord]) -> ControlResult:
    rows = tuple(records)
    in_scope_total = sum((row.amount for row in rows if row.judgment.scope == Scope.IN_SCOPE), Decimal("0"))
    mapped_total = sum(
        (row.amount for row in rows if row.judgment.scope == Scope.IN_SCOPE and row.judgment.category),
        Decimal("0"),
    )
    # Deliberately fails when in-scope rows remain unmapped; gaps stay visible.
    return reconcile_amounts(
        "chk_categories_sum",
        mapped_total,
        in_scope_total,
        message="Mapped OCL must equal total in-scope OCL; unmapped in-scope rows remain a visible gap.",
    )


def not_applicable(control_id: str, reason: str) -> ControlResult:
    return ControlResult(control_id, CheckStatus.NOT_APPLICABLE, message=reason)
