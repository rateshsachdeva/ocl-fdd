"""Evidence-aware extended OCL analysis.

This module adds FDD analyses that can be supported by the reconciled OCL model
without pretending unavailable evidence exists. Every analytical number remains
Python-owned; the AI partner layer only interprets the resulting tables/findings.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from statistics import median
from typing import Iterable

from ocl_agent.part2_analysis.engine import ABSOLUTE_MATERIALITY, is_databook_material, is_finding_material
from ocl_agent.schemas import AnalysisTable, Finding, MovementRecord, OCLRecord, Scope

MONTHLY_USAGE = "MONTHLY_RECORDS"


def extended_analysis(
    records: Iterable[OCLRecord],
    *,
    movements: Iterable[MovementRecord] = (),
    context: dict[str, dict[str, Decimal]] | None = None,
) -> tuple[tuple[Finding, ...], tuple[AnalysisTable, ...]]:
    rows = tuple(row for row in records if row.judgment.scope == Scope.IN_SCOPE and row.judgment.category)
    annual = tuple(row for row in rows if row.dimensions.get("record_usage") != MONTHLY_USAGE)
    monthly = tuple(row for row in rows if row.dimensions.get("record_usage") == MONTHLY_USAGE)
    movement_rows = tuple(row for row in movements if row.judgment.scope == Scope.IN_SCOPE and row.judgment.category)
    context = context or {}

    findings: list[Finding] = []
    tables: list[AnalysisTable] = []

    annual_periods = tuple(sorted({row.period for row in annual}))
    annual_categories = tuple(sorted({str(row.judgment.category) for row in annual if row.judgment.category}))
    annual_matrix = _matrix(annual, annual_periods, annual_categories)
    if len(annual_periods) >= 2:
        mix_table, mix_findings = _mix_shift(annual_matrix, annual_periods, annual_categories)
        tables.append(mix_table)
        findings.extend(mix_findings)

    monthly_periods = tuple(sorted({row.period for row in monthly}))
    categories = tuple(sorted({str(row.judgment.category) for row in monthly if row.judgment.category}))
    matrix = _matrix(monthly, monthly_periods, categories)

    if len(monthly_periods) >= 4:
        year_end, year_end_findings = _year_end_build(matrix, monthly_periods, categories)
        tables.append(year_end)
        findings.extend(year_end_findings)
    if len(monthly_periods) >= 12:
        tables.append(_normalization_reference(matrix, monthly_periods, categories))
        tables.append(_recurrence_proxy(matrix, monthly_periods, categories))
        accumulation_table, accumulation_findings = _persistent_accumulation(matrix, monthly_periods, categories)
        tables.append(accumulation_table)
        findings.extend(accumulation_findings)

    if movement_rows:
        movement_table, movement_findings = _movement_patterns(movement_rows)
        tables.append(movement_table)
        findings.extend(movement_findings)

    expense_table = _expense_ratio(rows, context.get("expense", {}))
    if expense_table is not None:
        tables.append(expense_table)

    tables.append(
        _coverage_table(
            rows,
            annual_periods,
            monthly_periods,
            movement_rows,
            context,
            expense_table is not None,
        )
    )
    return tuple(findings), tuple(tables)


def _matrix(records, periods, categories):
    values: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    for row in records:
        values[(str(row.judgment.category), row.period)] += row.amount
    return {(category, period): values[(category, period)] for category in categories for period in periods}


def _mix_shift(matrix, periods, categories) -> tuple[AnalysisTable, list[Finding]]:
    previous, latest = periods[-2], periods[-1]
    previous_total = sum((abs(matrix[(category, previous)]) for category in categories), Decimal("0"))
    latest_total = sum((abs(matrix[(category, latest)]) for category in categories), Decimal("0"))
    rows = []
    findings: list[Finding] = []
    for category in categories:
        previous_value = matrix[(category, previous)]
        latest_value = matrix[(category, latest)]
        previous_share = None if previous_total == 0 else float((abs(previous_value) / previous_total) * Decimal("100"))
        latest_share = None if latest_total == 0 else float((abs(latest_value) / latest_total) * Decimal("100"))
        change_pp = None if previous_share is None or latest_share is None else latest_share - previous_share
        review = bool(
            change_pp is not None
            and abs(change_pp) >= 10.0
            and abs(latest_value) >= ABSOLUTE_MATERIALITY
        )
        rows.append((category, previous_value, latest_value, previous_share, latest_share, change_pp, "REVIEW" if review else ""))
        if review and change_pp is not None and abs(change_pp) >= 15.0:
            direction = "increased" if change_pp > 0 else "decreased"
            findings.append(
                Finding(
                    f"F_MIX_{_slug(category)}",
                    f"Material OCL mix shift: {category}",
                    f"{category}'s share of absolute in-scope OCL {direction} by {abs(change_pp):.1f} percentage points from {previous} to {latest}; the latest balance is {latest_value:,.0f}.",
                    (category, previous, latest),
                    "MIX_SHIFT",
                    {
                        "category": category,
                        "previous_period": previous,
                        "latest_period": latest,
                        "previous_share_pct": previous_share,
                        "latest_share_pct": latest_share,
                        "share_change_pp": change_pp,
                        "latest": str(latest_value),
                        "materiality": "NOTABLE",
                    },
                    "MEDIUM",
                )
            )
    return AnalysisTable(
        "mix_shift",
        "OCL composition / mix shift",
        ("Category", previous, latest, "Previous Share %", "Latest Share %", "Share Change pp", "Review Flag"),
        tuple(rows),
    ), findings


def _year_end_build(matrix, periods, categories) -> tuple[AnalysisTable, list[Finding]]:
    latest = periods[-1]
    baseline_periods = periods[-4:-1]
    rows = []
    findings: list[Finding] = []
    for category in categories:
        baseline_values = [matrix[(category, period)] for period in baseline_periods]
        baseline = sum(baseline_values, Decimal("0")) / Decimal(len(baseline_values))
        closing = matrix[(category, latest)]
        build = closing - baseline
        pct = _safe_pct(build, baseline)
        flag = "REVIEW" if is_databook_material(build, pct) else ""
        rows.append((category, ", ".join(baseline_periods), baseline, closing, build, pct, flag))
        if build != 0 and is_finding_material(build, pct):
            direction = "build" if build > 0 else "unwind"
            findings.append(Finding(
                f"F_YE_BUILD_{_slug(category)}",
                f"Year-end {direction}: {category}",
                f"{category} closes at {closing:,.0f} in {latest} versus a prior three-month average of {baseline:,.0f}, a {direction} of {abs(build):,.0f}" + (f" ({abs(pct):.1f}%)." if pct is not None else "."),
                (category, *baseline_periods, latest),
                "YEAR_END_BUILD",
                {"category": category, "period": latest, "baseline_periods": list(baseline_periods), "baseline_average": str(baseline), "closing": str(closing), "change": str(build), "change_pct": pct, "materiality": "MATERIAL"},
                "HIGH" if pct is None or abs(pct) >= 50 else "MEDIUM",
            ))
    return AnalysisTable(
        "year_end_build",
        "Year-end build / unwind versus prior three-month run-rate",
        ("Category", "Baseline Periods", "Prior 3M Average", "Year End", "Build / (Unwind)", "Build %", "Review Flag"),
        tuple(rows),
    ), findings


def _normalization_reference(matrix, periods, categories) -> AnalysisTable:
    trailing = periods[-12:]
    rows = []
    for category in categories:
        values = [matrix[(category, period)] for period in trailing]
        average = sum(values, Decimal("0")) / Decimal(len(values))
        med = Decimal(str(median([float(value) for value in values])))
        latest = values[-1]
        difference = latest - average
        pct = _safe_pct(difference, average)
        rows.append((category, average, med, latest, difference, pct, "REFERENCE_ONLY"))
    return AnalysisTable(
        "normalization_reference",
        "Potential normalization reference (not an FDD adjustment)",
        ("Category", "12M Average", "12M Median", "Latest", "Latest vs Average", "Difference %", "Treatment"),
        tuple(rows),
    )


def _recurrence_proxy(matrix, periods, categories) -> AnalysisTable:
    trailing = periods[-12:]
    rows = []
    for category in categories:
        values = [matrix[(category, period)] for period in trailing]
        non_zero = sum(1 for value in values if value != 0)
        non_zero_pct = (non_zero / len(values)) * 100 if values else 0.0
        changes = [values[index] - values[index - 1] for index in range(1, len(values))]
        direction_changes = 0
        previous_sign = 0
        for change in changes:
            sign = 1 if change > 0 else -1 if change < 0 else 0
            if sign and previous_sign and sign != previous_sign:
                direction_changes += 1
            if sign:
                previous_sign = sign
        pattern = "PERSISTENT_BALANCE" if non_zero_pct >= 75 else "INTERMITTENT_BALANCE"
        rows.append((category, trailing[0], trailing[-1], non_zero, len(values), non_zero_pct, direction_changes, pattern))
    return AnalysisTable(
        "recurrence_proxy",
        "Recurring / persistent balance pattern proxy",
        ("Category", "Start", "End", "Non-zero Months", "Months Tested", "Non-zero %", "Direction Changes", "Pattern"),
        tuple(rows),
    )


def _persistent_accumulation(matrix, periods, categories) -> tuple[AnalysisTable, list[Finding]]:
    trailing = periods[-12:]
    rows = []
    findings: list[Finding] = []
    for category in categories:
        values = [matrix[(category, period)] for period in trailing]
        changes = [values[index] - values[index - 1] for index in range(1, len(values))]
        latest_direction = 1 if changes[-1] > 0 else -1 if changes[-1] < 0 else 0
        consecutive = 0
        if latest_direction:
            for change in reversed(changes):
                direction = 1 if change > 0 else -1 if change < 0 else 0
                if direction != latest_direction:
                    break
                consecutive += 1
        average = sum(values, Decimal("0")) / Decimal(len(values))
        latest = values[-1]
        change_vs_average = latest - average
        pct = _safe_pct(change_vs_average, average)
        pattern = ""
        if consecutive >= 3 and latest_direction > 0:
            pattern = "PERSISTENT_BUILD"
        elif consecutive >= 3 and latest_direction < 0:
            pattern = "PERSISTENT_UNWIND"
        flag = "REVIEW" if pattern and is_databook_material(change_vs_average, pct) else ""
        rows.append((category, trailing[0], trailing[-1], consecutive, pattern, average, latest, change_vs_average, pct, flag))
        if pattern and is_finding_material(change_vs_average, pct):
            description = "build" if latest_direction > 0 else "unwind"
            findings.append(
                Finding(
                    f"F_ACCUM_{_slug(category)}",
                    f"Persistent {description}: {category}",
                    f"{category} has moved in the same {description} direction for {consecutive} consecutive monthly movements and closes at {latest:,.0f} versus a trailing 12-month average of {average:,.0f}.",
                    (category, trailing[0], trailing[-1]),
                    "PERSISTENT_ACCUMULATION" if latest_direction > 0 else "PERSISTENT_UNWIND",
                    {
                        "category": category,
                        "period": trailing[-1],
                        "consecutive_movements": consecutive,
                        "latest": str(latest),
                        "average": str(average),
                        "change": str(change_vs_average),
                        "change_pct": pct,
                        "materiality": "MATERIAL",
                    },
                    "MEDIUM",
                )
            )
    return AnalysisTable(
        "persistent_accumulation",
        "Persistent build / unwind diagnostic",
        ("Category", "Start", "End", "Consecutive Movements", "Pattern", "12M Average", "Latest", "Latest vs Average", "Difference %", "Review Flag"),
        tuple(rows),
    ), findings


def _movement_patterns(movements: tuple[MovementRecord, ...]) -> tuple[AnalysisTable, list[Finding]]:
    grouped: dict[tuple[str, str], dict[str, Decimal]] = {}
    reversal_amounts: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    for row in movements:
        key = (str(row.judgment.category), row.period)
        bucket = grouped.setdefault(key, {
            "opening": Decimal("0"),
            "additions": Decimal("0"),
            "releases": Decimal("0"),
            "closing": Decimal("0"),
        })
        if row.movement_role == "OPENING":
            bucket["opening"] += row.signed_amount
        elif row.movement_role == "CLOSING":
            bucket["closing"] += row.signed_amount
        else:
            if row.signed_amount >= 0:
                bucket["additions"] += row.signed_amount
            else:
                bucket["releases"] += abs(row.signed_amount)
            raw_type = str(row.dimensions.get("raw_movement_type") or "").casefold()
            if "reversal" in raw_type or "reverse" in raw_type:
                reversal_amounts[key] += abs(row.signed_amount)

    rows = []
    findings: list[Finding] = []
    for (category, period), bucket in sorted(grouped.items(), key=lambda item: (item[0][1], item[0][0])):
        available = abs(bucket["opening"]) + abs(bucket["additions"])
        utilisation = None if available == 0 else float((bucket["releases"] / available) * Decimal("100"))
        reversal = reversal_amounts[(category, period)]
        rows.append((category, period, bucket["opening"], bucket["additions"], bucket["releases"], reversal, bucket["closing"], utilisation))
        if reversal != 0 and is_finding_material(reversal, None):
            findings.append(Finding(
                f"F_REVERSAL_{_slug(category)}_{_slug(period)}",
                f"Material reversal activity: {category}",
                f"Explicitly identified reversal movements total {reversal:,.0f} for {category} in {period}.",
                (category, period),
                "REVERSAL_PATTERN",
                {"category": category, "period": period, "reversal_amount": str(reversal), "materiality": "MATERIAL"},
                "MEDIUM",
            ))
    return AnalysisTable(
        "movement_patterns",
        "Utilisation / release and reversal patterns from explicit movement data",
        ("Category", "Period", "Opening", "Additions", "Releases / Utilisation", "Explicit Reversals", "Closing", "Utilisation %"),
        tuple(rows),
    ), findings


def _expense_ratio(records: tuple[OCLRecord, ...], expense: dict[str, Decimal]) -> AnalysisTable | None:
    if not expense:
        return None
    totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in records:
        totals[row.period] += row.amount
    rows = []
    for period in sorted(set(totals) & set(expense)):
        base = expense[period]
        ratio = None if base == 0 else float((totals[period] / abs(base)) * Decimal("100"))
        rows.append((period, totals[period], base, ratio))
    if not rows:
        return None
    return AnalysisTable(
        "accrual_to_expense",
        "OCL to explicitly linked expense context",
        ("Period", "OCL", "Expense Context", "OCL / Expense %"),
        tuple(rows),
    )


def _coverage_table(records, annual_periods, monthly_periods, movements, context, has_expense_ratio) -> AnalysisTable:
    has_annual_2 = len(annual_periods) >= 2
    has_monthly_3 = len(monthly_periods) >= 3
    has_monthly_4 = len(monthly_periods) >= 4
    has_monthly_12 = len(monthly_periods) >= 12
    has_movements = bool(movements)
    has_reviewed_debt = any(str(row.judgment.fdd_view or "").strip() for row in records)

    rows = [
        ("Annual / category movements", "SUPPORTED" if has_annual_2 else "UNSUPPORTED", "At least two annual OCL periods" if has_annual_2 else "Requires at least two annual OCL periods", "Latest year-on-year balance movement"),
        ("Composition / mix shift", "SUPPORTED" if has_annual_2 else "UNSUPPORTED", "At least two annual category balances" if has_annual_2 else "Requires at least two annual category periods", "Highlights material changes in category share of total OCL"),
        ("Seasonality", "SUPPORTED" if has_monthly_12 else "UNSUPPORTED", "At least 12 monthly OCL balances" if has_monthly_12 else "Requires at least 12 monthly OCL balances", "Year-end versus trailing run-rate"),
        ("Monthly volatility", "SUPPORTED" if has_monthly_3 else "UNSUPPORTED", "Monthly OCL balances" if has_monthly_3 else "Requires at least 3 monthly periods", "Balance variability"),
        ("Year-end build / unwind", "SUPPORTED" if has_monthly_4 else "UNSUPPORTED", "Latest month plus prior 3 months" if has_monthly_4 else "Requires at least 4 monthly periods", "Closing balance versus prior 3M run-rate"),
        ("Recurring patterns", "PARTIAL" if has_monthly_12 else "UNSUPPORTED", "12M balance persistence proxy" if has_monthly_12 else "Requires at least 12 monthly periods", "Does not prove economic recurrence without movement/obligation evidence"),
        ("Persistent accumulation / unwind", "SUPPORTED" if has_monthly_12 else "UNSUPPORTED", "12M monthly movement sequence" if has_monthly_12 else "Requires at least 12 monthly periods", "Flags repeated directional build/unwind; cause still requires evidence"),
        ("Potential normalization", "REFERENCE_ONLY" if has_monthly_12 else "UNSUPPORTED", "12M average/median reference" if has_monthly_12 else "Requires at least 12 monthly periods", "Not an FDD adjustment; partner judgment still required"),
        ("Accrual-to-expense ratio", "SUPPORTED" if has_expense_ratio else "UNSUPPORTED", "Explicit EXPENSE_CONTEXT with matching periods" if has_expense_ratio else "Requires explicitly linked expense/P&L context", "Interpret only to the extent the expense base is explicitly linked; no generic P&L proxy is assumed"),
        ("Utilisation", "SUPPORTED" if has_movements else "UNSUPPORTED", "Explicit movement roles and sign rules" if has_movements else "Requires movement/release/payment data", "Release/utilisation proxy from explicit movements"),
        ("Aged / stale accruals", "PARTIAL" if has_monthly_4 else "UNSUPPORTED", "Unchanged-balance stale proxy" if has_monthly_4 else "Requires monthly history; true aging requires dates", "Stale balance is not the same as invoice/obligation aging"),
        ("Reversal patterns", "SUPPORTED" if has_movements else "UNSUPPORTED", "Explicit movement type evidence" if has_movements else "Requires movement/reversal data", "Only explicitly identified reversals are assessed"),
        ("Debt-like treatment", "SUPPORTED" if has_reviewed_debt else "UNSUPPORTED", "Reviewed OCL judgment layer" if has_reviewed_debt else "Requires reviewed WC/debt-like judgments", "Human-reviewed classification remains authoritative"),
        ("Adequacy", "UNSUPPORTED", "Requires obligation/expense/settlement evidence beyond balance history", "Do not infer adequacy from balance movements alone"),
        ("Missing accruals", "UNSUPPORTED", "Requires completeness evidence such as subsequent payments, contracts, vendor/payroll or P&L support", "No unsupported completeness conclusion"),
        ("Double counting", "UNSUPPORTED", "Requires detailed obligation/vendor/payroll/invoice-level evidence", "No duplicate-liability conclusion from aggregate balances"),
    ]
    return AnalysisTable(
        "analysis_coverage",
        "FDD analysis coverage and evidence limitations",
        ("Analysis", "Status", "Evidence", "Limitation / Interpretation"),
        tuple(rows),
    )


def _safe_pct(change: Decimal, base: Decimal) -> float | None:
    if base == 0:
        return None
    return float((change / abs(base)) * Decimal("100"))


def _slug(value: str) -> str:
    text = "".join(character if character.isalnum() else "_" for character in str(value).upper())
    return "_".join(part for part in text.split("_") if part)[:40] or "ITEM"
