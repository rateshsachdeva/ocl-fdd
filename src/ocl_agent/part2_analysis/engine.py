"""Deterministic metrics engine for Part 2 OCL analysis.

Python owns every analytical number.  It computes balances, movements,
seasonality, concentration and reviewed classification totals once from the
reconciled Part 1 OCLRecord model.  Narrative interpretation may be refined by
an AI host, but AI must never change these numbers.

The workbook/reference architecture uses two materiality levels:
- databook review: absolute movement >= 100,000 OR percentage movement >= 10%;
- findings/Q&A: absolute movement >= 100,000 AND percentage movement >= 30%.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from statistics import pstdev
from typing import Iterable

from ocl_agent.schemas import AnalysisResult, AnalysisTable, Finding, OCLRecord, Scope

MONTHLY_USAGE = "MONTHLY_RECORDS"
ABSOLUTE_MATERIALITY = Decimal("100000")
DATABOOK_PERCENT_THRESHOLD = 10.0
FINDING_PERCENT_THRESHOLD = 30.0
SEASONALITY_REVIEW_THRESHOLD = 10.0


def analyse_records(records: Iterable[OCLRecord]) -> AnalysisResult:
    rows = tuple(row for row in records if row.judgment.scope == Scope.IN_SCOPE and row.judgment.category)
    annual = tuple(row for row in rows if row.dimensions.get("record_usage") != MONTHLY_USAGE)
    monthly = tuple(row for row in rows if row.dimensions.get("record_usage") == MONTHLY_USAGE)
    annual_periods = tuple(sorted({row.period for row in annual}))
    monthly_periods = tuple(sorted({row.period for row in monthly}))
    categories = tuple(sorted({str(row.judgment.category) for row in rows if row.judgment.category}))
    annual_by_category = _matrix(annual, annual_periods, categories)
    monthly_by_category = _matrix(monthly, monthly_periods, categories)
    findings: list[Finding] = []
    tables: list[AnalysisTable] = []

    if annual_periods:
        tables.append(_annual_table(annual_by_category, annual_periods, categories))
        if len(annual_periods) >= 2:
            tables.append(_movement_review_table(annual_by_category, annual_periods, categories))
        findings.extend(_annual_findings(annual_by_category, annual_periods, categories))
        findings.extend(_concentration_findings(annual_by_category, annual_periods, categories))
        findings.extend(_classification_findings(annual, annual_periods[-1]))

    if monthly_periods:
        tables.append(_monthly_summary_table(monthly_by_category, monthly_periods, categories))
        findings.extend(_monthly_variability_findings(monthly_by_category, monthly_periods, categories))
        if len(monthly_periods) >= 12:
            tables.append(_seasonality_table(monthly_by_category, monthly_periods, categories))
            findings.extend(_seasonality_findings(monthly_by_category, monthly_periods, categories))

    return AnalysisResult(
        tuple(_deduplicate(findings)),
        tuple(tables),
        annual_periods,
        monthly_periods,
        annual_periods[-1] if annual_periods else None,
    )


def is_databook_material(change: Decimal, pct_change: float | None) -> bool:
    """Broad review threshold: absolute >=100k OR percentage >=10%."""
    return abs(change) >= ABSOLUTE_MATERIALITY or (pct_change is not None and abs(pct_change) >= DATABOOK_PERCENT_THRESHOLD)


def is_finding_material(change: Decimal, pct_change: float | None) -> bool:
    """Focused finding threshold: absolute >=100k AND percentage >=30%."""
    if abs(change) < ABSOLUTE_MATERIALITY:
        return False
    return pct_change is None or abs(pct_change) >= FINDING_PERCENT_THRESHOLD


def _matrix(records, periods, categories):
    values: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    for row in records:
        values[(str(row.judgment.category), row.period)] += row.amount
    return {(category, period): values[(category, period)] for category in categories for period in periods}


def _annual_table(matrix, periods, categories) -> AnalysisTable:
    table_rows = [(category, *(matrix[(category, period)] for period in periods)) for category in categories]
    table_rows.append(("Total OCL", *(sum((matrix[(category, period)] for category in categories), Decimal("0")) for period in periods)))
    return AnalysisTable("annual_balance", "Annual OCL balance by category", ("Category", *periods), tuple(table_rows))


def _movement_review_table(matrix, periods, categories) -> AnalysisTable:
    previous, latest = periods[-2], periods[-1]
    rows = []
    for category in categories:
        old = matrix[(category, previous)]
        new = matrix[(category, latest)]
        change = new - old
        pct = _safe_pct(change, old)
        rows.append((
            category,
            old,
            new,
            change,
            pct,
            "REVIEW" if is_databook_material(change, pct) else "",
            "FINDING" if is_finding_material(change, pct) else "",
        ))
    return AnalysisTable(
        "movement_review",
        "Latest annual movement review",
        ("Category", previous, latest, "Movement", "Movement %", "Databook Review", "Finding Eligible"),
        tuple(rows),
    )


def _monthly_summary_table(matrix, periods, categories) -> AnalysisTable:
    table_rows = []
    for category in categories:
        values = [matrix[(category, period)] for period in periods]
        if not values:
            continue
        average = sum(values, Decimal("0")) / Decimal(len(values))
        std_dev = Decimal(str(pstdev([float(value) for value in values]))) if len(values) > 1 else Decimal("0")
        table_rows.append((category, average, min(values), max(values), std_dev, values[-1]))
    return AnalysisTable("monthly_statistics", "Monthly OCL statistics by category", ("Category", "Average", "Minimum", "Maximum", "Std_Dev", "Latest"), tuple(table_rows))


def _seasonality_table(matrix, periods, categories) -> AnalysisTable:
    trailing = periods[-12:]
    rows = []
    for category in categories:
        values = [matrix[(category, period)] for period in trailing]
        average = sum(values, Decimal("0")) / Decimal(len(values))
        year_end = values[-1]
        deviation_value = year_end - average
        deviation_pct = _safe_pct(deviation_value, average)
        peak_index = max(range(len(values)), key=lambda index: abs(values[index]))
        flag = ""
        if deviation_pct is not None and deviation_pct >= SEASONALITY_REVIEW_THRESHOLD:
            flag = "YEAR-END SPIKE"
        elif deviation_pct is not None and deviation_pct <= -SEASONALITY_REVIEW_THRESHOLD:
            flag = "YEAR-END DIP"
        rows.append((category, average, year_end, deviation_value, deviation_pct, trailing[peak_index], values[peak_index], flag))
    return AnalysisTable(
        "seasonality",
        "Year-end representativeness / seasonality",
        ("Category", "12M Average", "Year End", "Deviation", "Deviation %", "Peak Period", "Peak", "Flag"),
        tuple(rows),
    )


def _annual_findings(matrix, periods, categories) -> list[Finding]:
    if len(periods) < 2:
        return []
    previous, latest = periods[-2], periods[-1]
    previous_total = sum((matrix[(category, previous)] for category in categories), Decimal("0"))
    latest_total = sum((matrix[(category, latest)] for category in categories), Decimal("0"))
    change = latest_total - previous_total
    pct = _safe_pct(change, previous_total)
    results: list[Finding] = []
    if change != 0 and is_finding_material(change, pct):
        results.append(Finding(
            "F_TOTAL_CHANGE",
            "OCL balance movement",
            f"Total in-scope OCL moved from {previous_total:,.0f} in {previous} to {latest_total:,.0f} in {latest}, a change of {change:,.0f}" + (f" ({pct:.1f}%)." if pct is not None else "."),
            (previous, latest),
            "TOTAL_CHANGE",
            {"previous_period": previous, "latest_period": latest, "previous": str(previous_total), "latest": str(latest_total), "change": str(change), "change_pct": pct, "materiality": "MATERIAL"},
            "HIGH",
        ))
    for category in categories:
        old = matrix[(category, previous)]
        new = matrix[(category, latest)]
        delta = new - old
        pct_change = _safe_pct(delta, old)
        if delta != 0 and is_finding_material(delta, pct_change):
            results.append(Finding(
                f"F_MOVE_{_slug(category)}",
                f"Movement in {category}",
                f"{category} moved from {old:,.0f} in {previous} to {new:,.0f} in {latest}, a change of {delta:,.0f}" + (f" ({pct_change:.1f}%)." if pct_change is not None else "."),
                (category, previous, latest),
                "CATEGORY_MOVEMENT",
                {"category": category, "previous_period": previous, "latest_period": latest, "previous": str(old), "latest": str(new), "change": str(delta), "change_pct": pct_change, "materiality": "MATERIAL"},
                "HIGH" if pct_change is None or abs(pct_change) >= 50 else "MEDIUM",
            ))
    return results


def _concentration_findings(matrix, periods, categories) -> list[Finding]:
    if not periods or not categories:
        return []
    latest = periods[-1]
    total = sum((abs(matrix[(category, latest)]) for category in categories), Decimal("0"))
    if total == 0:
        return []
    ranked = sorted(((category, abs(matrix[(category, latest)])) for category in categories), key=lambda item: item[1], reverse=True)
    category, value = ranked[0]
    share = float((value / total) * Decimal("100"))
    if share < 35 or value < ABSOLUTE_MATERIALITY:
        return []
    return [Finding(
        "F_CONCENTRATION",
        "OCL concentration",
        f"{category} represents {share:.1f}% of absolute in-scope OCL at {latest}, making it the largest category in the closing balance.",
        (category, latest),
        "CONCENTRATION",
        {"category": category, "period": latest, "share_pct": share, "absolute_value": str(value), "materiality": "MATERIAL"},
        "HIGH" if share >= 50 else "MEDIUM",
    )]


def _monthly_variability_findings(matrix, periods, categories) -> list[Finding]:
    if len(periods) < 3:
        return []
    results: list[Finding] = []
    for category in categories:
        values = [matrix[(category, period)] for period in periods]
        average = sum(values, Decimal("0")) / Decimal(len(values))
        average_abs = sum((abs(value) for value in values), Decimal("0")) / Decimal(len(values))
        if average_abs == 0:
            continue
        std_dev = Decimal(str(pstdev([float(value) for value in values])))
        cv = float(std_dev / average_abs)
        peak_index = max(range(len(values)), key=lambda index: abs(values[index]))
        peak = values[peak_index]
        peak_period = periods[peak_index]
        peak_change = peak - average
        peak_pct = _safe_pct(peak_change, average)
        if cv >= 0.25 and is_finding_material(peak_change, peak_pct):
            results.append(Finding(
                f"F_VOL_{_slug(category)}",
                f"Monthly variability in {category}",
                f"{category} shows material monthly variability across {len(periods)} available periods; the largest absolute month is {peak_period} at {peak:,.0f} versus an average of {average:,.0f}.",
                (category, peak_period),
                "MONTHLY_VARIABILITY",
                {"category": category, "period_count": len(periods), "coefficient_of_variation": cv, "peak_period": peak_period, "peak_value": str(peak), "average": str(average), "change": str(peak_change), "change_pct": peak_pct, "materiality": "MATERIAL"},
                "MEDIUM",
            ))
    return results


def _seasonality_findings(matrix, periods, categories) -> list[Finding]:
    trailing = periods[-12:]
    latest = trailing[-1]
    results: list[Finding] = []
    for category in categories:
        values = [matrix[(category, period)] for period in trailing]
        average = sum(values, Decimal("0")) / Decimal(len(values))
        year_end = values[-1]
        change = year_end - average
        pct = _safe_pct(change, average)
        if is_finding_material(change, pct):
            direction = "above" if change > 0 else "below"
            results.append(Finding(
                f"F_SEASON_{_slug(category)}",
                f"Year-end representativeness: {category}",
                f"{category} closes at {year_end:,.0f} in {latest}, {abs(change):,.0f} ({abs(pct or 0):.1f}%) {direction} its trailing 12-month average of {average:,.0f}.",
                (category, latest),
                "SEASONALITY",
                {"category": category, "period": latest, "year_end": str(year_end), "average": str(average), "change": str(change), "change_pct": pct, "materiality": "MATERIAL"},
                "HIGH" if pct is not None and abs(pct) >= 50 else "MEDIUM",
            ))
    return results


def _classification_findings(records, latest_period: str) -> list[Finding]:
    latest = [row for row in records if row.period == latest_period]
    fdd_debt = sum((row.amount for row in latest if _is_debt_like(row.judgment.fdd_view)), Decimal("0"))
    management_debt = sum((row.amount for row in latest if _is_debt_like(row.judgment.management_view)), Decimal("0"))
    one_off = sum((row.amount for row in latest if str(row.judgment.normality or "").strip().casefold() == "one_off"), Decimal("0"))
    results: list[Finding] = []
    if abs(fdd_debt) >= ABSOLUTE_MATERIALITY:
        results.append(Finding(
            "F_DEBT_LIKE",
            "Debt-like OCL classification",
            f"Items classified as debt-like in the FDD view total {fdd_debt:,.0f} at {latest_period} based on the reviewed OCL judgment layer.",
            (latest_period,),
            "DEBT_LIKE",
            {"period": latest_period, "amount": str(fdd_debt), "management_amount": str(management_debt), "materiality": "MATERIAL"},
            "HIGH",
        ))
    gap = fdd_debt - management_debt
    if abs(gap) >= ABSOLUTE_MATERIALITY:
        results.append(Finding(
            "F_DEBT_LIKE_GAP",
            "FDD vs management debt-like gap",
            f"The FDD debt-like classification is {fdd_debt:,.0f} at {latest_period} versus {management_debt:,.0f} in management's view, a gap of {gap:,.0f} requiring factual reconciliation.",
            (latest_period,),
            "DEBT_LIKE_GAP",
            {"period": latest_period, "fdd_amount": str(fdd_debt), "management_amount": str(management_debt), "gap": str(gap), "materiality": "MATERIAL"},
            "HIGH",
        ))
    if abs(one_off) >= ABSOLUTE_MATERIALITY:
        results.append(Finding(
            "F_ONE_OFF",
            "One-off OCL items",
            f"Items classified as one-off/non-recurring total {one_off:,.0f} at {latest_period} based on reviewed normality judgments.",
            (latest_period,),
            "ONE_OFF",
            {"period": latest_period, "amount": str(one_off), "materiality": "MATERIAL"},
            "MEDIUM",
        ))
    return results


def _is_debt_like(value) -> bool:
    normalized = str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")
    return normalized in {"debt_like", "net_debt"}


def _safe_pct(change: Decimal, base: Decimal) -> float | None:
    if base == 0:
        return None
    return float((change / abs(base)) * Decimal("100"))


def _slug(value: str) -> str:
    text = "".join(character if character.isalnum() else "_" for character in value.upper())
    return "_".join(part for part in text.split("_") if part)[:40] or "ITEM"


def _deduplicate(findings: list[Finding]) -> list[Finding]:
    seen: set[str] = set()
    result: list[Finding] = []
    for finding in findings:
        if finding.finding_id not in seen:
            seen.add(finding.finding_id)
            result.append(finding)
    return result
