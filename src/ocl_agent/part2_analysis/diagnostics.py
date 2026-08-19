"""Focused OCL diagnostics used to create decision-useful questions."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Iterable

from ocl_agent.schemas import Finding, OCLRecord, Scope


def diagnostic_findings(records: Iterable[OCLRecord]) -> tuple[Finding, ...]:
    rows = tuple(row for row in records if row.judgment.scope == Scope.IN_SCOPE and row.judgment.category)
    annual = [row for row in rows if row.dimensions.get("record_usage") != "MONTHLY_RECORDS"]
    monthly = [row for row in rows if row.dimensions.get("record_usage") == "MONTHLY_RECORDS"]
    findings = [*_new_and_cliff(annual), *_stale(monthly)]
    return tuple(findings)


def _new_and_cliff(records: list[OCLRecord]) -> list[Finding]:
    periods = sorted({row.period for row in records})
    if len(periods) < 2:
        return []
    previous, latest = periods[-2], periods[-1]
    balances: dict[tuple[str, str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    labels: dict[tuple[str, str], str] = {}
    for row in records:
        key = (row.source_label, str(row.judgment.category), row.period)
        balances[key] += row.amount
        labels[(row.source_label, str(row.judgment.category))] = row.source_label
    results: list[Finding] = []
    for label, category in sorted(labels):
        old = balances[(label, category, previous)]
        new = balances[(label, category, latest)]
        if old == 0 and new != 0:
            results.append(Finding(
                f"F_NEW_{_slug(label)}",
                f"New balance: {label}",
                f"{label} is nil in {previous} and {new:,.0f} in {latest}.",
                (label, previous, latest),
                "NEW_ITEM",
                {"source_label": label, "category": category, "previous_period": previous, "latest_period": latest, "latest": str(new)},
                "MEDIUM",
            ))
        elif old != 0 and new == 0:
            results.append(Finding(
                f"F_CLIFF_{_slug(label)}",
                f"Balance reduced to nil: {label}",
                f"{label} is {old:,.0f} in {previous} and nil in {latest}.",
                (label, previous, latest),
                "CLIFF",
                {"source_label": label, "category": category, "previous_period": previous, "latest_period": latest, "previous": str(old)},
                "MEDIUM",
            ))
    return results


def _stale(records: list[OCLRecord], *, minimum_months: int = 4) -> list[Finding]:
    periods = sorted({row.period for row in records})
    if len(periods) < minimum_months:
        return []
    values: dict[tuple[str, str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    labels: set[tuple[str, str]] = set()
    for row in records:
        category = str(row.judgment.category)
        values[(row.source_label, category, row.period)] += row.amount
        labels.add((row.source_label, category))
    tail = periods[-minimum_months:]
    results: list[Finding] = []
    for label, category in sorted(labels):
        series = [values[(label, category, period)] for period in tail]
        if series[0] != 0 and all(value == series[0] for value in series[1:]):
            results.append(Finding(
                f"F_STALE_{_slug(label)}",
                f"Stale balance pattern: {label}",
                f"{label} remains unchanged at {series[0]:,.0f} across the latest {minimum_months} available monthly periods ({tail[0]} to {tail[-1]}).",
                (label, tail[0], tail[-1]),
                "STALE_BALANCE",
                {"source_label": label, "category": category, "amount": str(series[0]), "start_period": tail[0], "end_period": tail[-1], "months": minimum_months},
                "MEDIUM",
            ))
    return results


def _slug(value: str) -> str:
    text = "".join(character if character.isalnum() else "_" for character in value.upper())
    return "_".join(part for part in text.split("_") if part)[:40] or "ITEM"
