"""Deterministic evidence engine for Part 2.

This module calculates only from the reconciled Part 1 OCLRecord model.  It
creates compact evidence-backed observations; it does not fabricate business
explanations.  An AI host may later improve wording, but the numeric evidence is
owned by this module.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from statistics import pstdev
from typing import Iterable

from ocl_agent.schemas import AnalysisResult, AnalysisTable, Finding, OCLRecord, Scope

MONTHLY_USAGE = "MONTHLY_RECORDS"


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
        findings.extend(_annual_findings(annual_by_category, annual_periods, categories))
        findings.extend(_concentration_findings(annual_by_category, annual_periods, categories))
        findings.extend(_classification_findings(annual, annual_periods[-1]))
    if monthly_periods:
        tables.append(_monthly_summary_table(monthly_by_category, monthly_periods, categories))
        findings.extend(_monthly_variability_findings(monthly_by_category, monthly_periods, categories))
    return AnalysisResult(tuple(_deduplicate(findings)), tuple(tables), annual_periods, monthly_periods, annual_periods[-1] if annual_periods else None)


def _matrix(records, periods, categories):
    values: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    for row in records:
        values[(str(row.judgment.category), row.period)] += row.amount
    return {(category, period): values[(category, period)] for category in categories for period in periods}


def _annual_table(matrix, periods, categories) -> AnalysisTable:
    table_rows = [(category, *(matrix[(category, period)] for period in periods)) for category in categories]
    table_rows.append(("Total OCL", *(sum((matrix[(category, period)] for category in categories), Decimal("0")) for period in periods)))
    return AnalysisTable("annual_balance", "Annual OCL balance by category", ("Category", *periods), tuple(table_rows))


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


def _annual_findings(matrix, periods, categories) -> list[Finding]:
    if len(periods) < 2:
        return []
    previous, latest = periods[-2], periods[-1]
    previous_total = sum((matrix[(category, previous)] for category in categories), Decimal("0"))
    latest_total = sum((matrix[(category, latest)] for category in categories), Decimal("0"))
    change = latest_total - previous_total
    pct = _safe_pct(change, previous_total)
    results: list[Finding] = []
    if change != 0:
        results.append(Finding("F_TOTAL_CHANGE", "OCL balance movement", f"Total in-scope OCL moved from {previous_total:,.0f} in {previous} to {latest_total:,.0f} in {latest}, a change of {change:,.0f}" + (f" ({pct:.1f}%)." if pct is not None else "."), (previous, latest), "TOTAL_CHANGE", {"previous_period": previous, "latest_period": latest, "previous": str(previous_total), "latest": str(latest_total), "change": str(change), "change_pct": pct}, "HIGH" if pct is not None and abs(pct) >= 20 else "MEDIUM"))
    latest_abs_total = abs(latest_total)
    for category in categories:
        old = matrix[(category, previous)]
        new = matrix[(category, latest)]
        delta = new - old
        pct_change = _safe_pct(delta, old)
        material = latest_abs_total == 0 or abs(delta) >= latest_abs_total * Decimal("0.05")
        if delta != 0 and material and (pct_change is None or abs(pct_change) >= 20):
            results.append(Finding(f"F_MOVE_{_slug(category)}", f"Movement in {category}", f"{category} moved from {old:,.0f} in {previous} to {new:,.0f} in {latest}, a change of {delta:,.0f}" + (f" ({pct_change:.1f}%)." if pct_change is not None else "."), (category, previous, latest), "CATEGORY_MOVEMENT", {"category": category, "previous_period": previous, "latest_period": latest, "previous": str(old), "latest": str(new), "change": str(delta), "change_pct": pct_change}, "HIGH" if pct_change is not None and abs(pct_change) >= 50 else "MEDIUM"))
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
    if share < 35:
        return []
    return [Finding("F_CONCENTRATION", "OCL concentration", f"{category} represents {share:.1f}% of absolute in-scope OCL at {latest}, making it the largest category in the closing balance.", (category, latest), "CONCENTRATION", {"category": category, "period": latest, "share_pct": share, "absolute_value": str(value)}, "HIGH" if share >= 50 else "MEDIUM")]


def _monthly_variability_findings(matrix, periods, categories) -> list[Finding]:
    if len(periods) < 3:
        return []
    results: list[Finding] = []
    for category in categories:
        values = [matrix[(category, period)] for period in periods]
        average_abs = sum((abs(value) for value in values), Decimal("0")) / Decimal(len(values))
        if average_abs == 0:
            continue
        std_dev = Decimal(str(pstdev([float(value) for value in values])))
        cv = float(std_dev / average_abs)
        peak_index = max(range(len(values)), key=lambda index: abs(values[index]))
        peak = values[peak_index]
        peak_period = periods[peak_index]
        if cv >= 0.25:
            results.append(Finding(f"F_VOL_{_slug(category)}", f"Monthly variability in {category}", f"{category} shows material monthly variability across {len(periods)} available periods (coefficient of variation {cv:.2f}); the largest absolute month is {peak_period} at {peak:,.0f}.", (category, peak_period), "MONTHLY_VARIABILITY", {"category": category, "period_count": len(periods), "coefficient_of_variation": cv, "peak_period": peak_period, "peak_value": str(peak)}, "MEDIUM"))
    return results


def _classification_findings(records, latest_period: str) -> list[Finding]:
    latest = [row for row in records if row.period == latest_period]
    debt_like = sum((row.amount for row in latest if str(row.judgment.fdd_view or "").strip().casefold() == "debt_like"), Decimal("0"))
    one_off = sum((row.amount for row in latest if str(row.judgment.normality or "").strip().casefold() == "one_off"), Decimal("0"))
    results: list[Finding] = []
    if debt_like != 0:
        results.append(Finding("F_DEBT_LIKE", "Debt-like OCL classification", f"Items classified as debt-like total {debt_like:,.0f} at {latest_period} based on the reviewed OCL judgment layer.", (latest_period,), "DEBT_LIKE", {"period": latest_period, "amount": str(debt_like)}, "HIGH"))
    if one_off != 0:
        results.append(Finding("F_ONE_OFF", "One-off OCL items", f"Items classified as one-off/non-recurring total {one_off:,.0f} at {latest_period} based on reviewed normality judgments.", (latest_period,), "ONE_OFF", {"period": latest_period, "amount": str(one_off)}, "MEDIUM"))
    return results


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
