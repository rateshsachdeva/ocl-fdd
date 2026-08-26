from decimal import Decimal

from ocl_agent.part2_analysis.extended import extended_analysis
from ocl_agent.schemas import MovementRecord, OCLJudgment, OCLRecord, ReviewStatus, Scope, SourceReference


def _judgment(category: str = "Bonus accrual"):
    return OCLJudgment(
        category,
        Scope.IN_SCOPE,
        category,
        fdd_view="working_capital",
        normality="normal",
        review_status=ReviewStatus.REVIEWED,
    )


def _monthly_records():
    values = [100000, 105000, 110000, 115000, 120000, 125000, 130000, 135000, 140000, 180000, 220000, 400000]
    return tuple(
        OCLRecord(
            SourceReference(f"m{month}"),
            f"2025-{month:02d}",
            Decimal(value),
            "Bonus accrual",
            _judgment(),
            {"record_usage": "MONTHLY_RECORDS"},
        )
        for month, value in enumerate(values, start=1)
    )


def _annual_mix_records():
    return (
        OCLRecord(SourceReference("a1"), "FY24", Decimal("800000"), "Bonus accrual", _judgment("Bonus accrual")),
        OCLRecord(SourceReference("a2"), "FY24", Decimal("200000"), "Professional fees", _judgment("Professional fees")),
        OCLRecord(SourceReference("a3"), "FY25", Decimal("400000"), "Bonus accrual", _judgment("Bonus accrual")),
        OCLRecord(SourceReference("a4"), "FY25", Decimal("600000"), "Professional fees", _judgment("Professional fees")),
    )


def test_extended_monthly_analysis_adds_run_rate_recurrence_and_coverage():
    findings, tables = extended_analysis(_monthly_records())
    keys = {table.key for table in tables}
    assert {
        "year_end_build",
        "normalization_reference",
        "recurrence_proxy",
        "persistent_accumulation",
        "analysis_coverage",
    }.issubset(keys)
    assert any(item.finding_type == "YEAR_END_BUILD" for item in findings)
    assert any(item.finding_type == "PERSISTENT_ACCUMULATION" for item in findings)

    coverage = next(table for table in tables if table.key == "analysis_coverage")
    status = {row[0]: row[1] for row in coverage.rows}
    assert status["Seasonality"] == "SUPPORTED"
    assert status["Year-end build / unwind"] == "SUPPORTED"
    assert status["Recurring patterns"] == "PARTIAL"
    assert status["Persistent accumulation / unwind"] == "SUPPORTED"
    assert status["Potential normalization"] == "REFERENCE_ONLY"
    assert status["Utilisation"] == "UNSUPPORTED"
    assert status["Adequacy"] == "UNSUPPORTED"
    assert status["Missing accruals"] == "UNSUPPORTED"
    assert status["Double counting"] == "UNSUPPORTED"


def test_annual_mix_shift_is_measured_and_can_create_notable_finding():
    findings, tables = extended_analysis(_annual_mix_records())
    table = next(item for item in tables if item.key == "mix_shift")
    fees = next(row for row in table.rows if row[0] == "Professional fees")
    assert fees[3] == 20.0
    assert fees[4] == 60.0
    assert fees[5] == 40.0
    assert fees[6] == "REVIEW"
    assert any(item.finding_type == "MIX_SHIFT" for item in findings)

    coverage = next(item for item in tables if item.key == "analysis_coverage")
    status = {row[0]: row[1] for row in coverage.rows}
    assert status["Composition / mix shift"] == "SUPPORTED"


def test_explicit_movements_support_utilisation_and_reversal_analysis():
    judgment = _judgment()
    movements = (
        MovementRecord(SourceReference("o"), "FY25", Decimal("500000"), "Bonus accrual", "OPENING", Decimal("1"), judgment),
        MovementRecord(SourceReference("a"), "FY25", Decimal("300000"), "Bonus accrual", "FLOW", Decimal("1"), judgment, {"raw_movement_type": "Addition"}),
        MovementRecord(SourceReference("r"), "FY25", Decimal("200000"), "Bonus accrual", "FLOW", Decimal("-1"), judgment, {"raw_movement_type": "Reversal"}),
        MovementRecord(SourceReference("c"), "FY25", Decimal("600000"), "Bonus accrual", "CLOSING", Decimal("1"), judgment),
    )
    findings, tables = extended_analysis(_monthly_records(), movements=movements)
    movement_table = next(table for table in tables if table.key == "movement_patterns")
    assert movement_table.rows[0][4] == Decimal("200000")
    assert movement_table.rows[0][5] == Decimal("200000")
    assert movement_table.rows[0][7] == 25.0
    assert any(item.finding_type == "REVERSAL_PATTERN" for item in findings)

    coverage = next(table for table in tables if table.key == "analysis_coverage")
    status = {row[0]: row[1] for row in coverage.rows}
    assert status["Utilisation"] == "SUPPORTED"
    assert status["Reversal patterns"] == "SUPPORTED"


def test_explicit_expense_context_adds_accrual_to_expense_ratio():
    context = {"expense": {"2025-12": Decimal("2000000")}}
    _findings, tables = extended_analysis(_monthly_records(), context=context)
    table = next(table for table in tables if table.key == "accrual_to_expense")
    assert table.rows == (("2025-12", Decimal("400000"), Decimal("2000000"), 20.0),)

    coverage = next(item for item in tables if item.key == "analysis_coverage")
    status = {row[0]: row[1] for row in coverage.rows}
    assert status["Accrual-to-expense ratio"] == "SUPPORTED"
