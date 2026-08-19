from decimal import Decimal

from ocl_agent.part1_databook.reconciliation import category_sum_control, not_applicable, reconcile_amounts
from ocl_agent.schemas import CheckStatus, OCLJudgment, OCLRecord, ReviewStatus, Scope, SourceReference


def make(amount: str, category: str | None) -> OCLRecord:
    return OCLRecord(
        SourceReference(f"SRC:{amount}:{category}"),
        "FY25",
        Decimal(amount),
        category or "unmapped",
        OCLJudgment(category or "unmapped", Scope.IN_SCOPE, category, review_status=ReviewStatus.REVIEWED),
    )


def test_tolerance_is_less_than_half_full_currency_unit():
    assert reconcile_amounts("x", Decimal("100"), Decimal("100.49")).status == CheckStatus.PASS
    assert reconcile_amounts("x", Decimal("100"), Decimal("100.50")).status == CheckStatus.FAIL


def test_unmapped_in_scope_balance_breaks_category_sum_control():
    result = category_sum_control([make("10", "Bonus"), make("2", None)])
    assert result.status == CheckStatus.FAIL
    assert result.difference == Decimal("-2")


def test_nonexistent_analysis_control_is_not_applicable():
    assert not_applicable("chk_rollforward", "No movement data").status == CheckStatus.NOT_APPLICABLE
