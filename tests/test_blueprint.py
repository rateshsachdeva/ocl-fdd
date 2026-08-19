from decimal import Decimal

from ocl_agent.part1_databook.workbook_blueprint import build_blueprint
from ocl_agent.schemas import OCLJudgment, OCLRecord, ReviewStatus, Scope, SourceReference


def record(label: str, category: str, parent: str, period: str) -> OCLRecord:
    return OCLRecord(
        source=SourceReference(f"SRC:{label}:{period}"),
        period=period,
        amount=Decimal("10"),
        source_label=label,
        judgment=OCLJudgment(label, Scope.IN_SCOPE, category, parent, review_status=ReviewStatus.REVIEWED),
    )


def test_blueprint_uses_only_actual_categories_periods_and_supported_analyses():
    blueprint = build_blueprint(
        [record("Bonus", "Bonus", "Employee accruals", "FY25"), record("Holiday", "Holiday pay", "Employee accruals", "FY24")],
        has_monthly_data=False,
        supported_analyses=["concentration"],
    )
    assert blueprint.categories == ("Bonus", "Holiday pay")
    assert blueprint.periods == ("FY24", "FY25")
    assert blueprint.hierarchy == {"Employee accruals": ("Bonus", "Holiday pay")}
    assert "concentration" in blueprint.sheet_keys()
    assert "aging" not in blueprint.sheet_keys()
    assert "monthly" not in blueprint.sheet_keys()
