"""Focused OCL diagnostics used to create decision-useful material findings."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Iterable

from ocl_agent.part2_analysis.engine import ABSOLUTE_MATERIALITY, is_finding_material
from ocl_agent.schemas import AnalysisTable, Finding, OCLRecord, Scope

ITEM_CONCENTRATION_THRESHOLD = 25.0
STALE_MONTHS = 4


def diagnostic_findings(records: Iterable[OCLRecord]) -> tuple[Finding, ...]:
    findings, _tables = diagnostic_analysis(records)
    return findings


def diagnostic_analysis(
    records: Iterable[OCLRecord],
) -> tuple[tuple[Finding, ...], tuple[AnalysisTable, ...]]:
    rows = tuple(row for row in records if row.judgment.scope == Scope.IN_SCOPE and row.judgment.category)
    annual = [row for row in rows if row.dimensions.get("record_usage") != "MONTHLY_RECORDS"]
    monthly = [row for row in rows if row.dimensions.get("record_usage") == "MONTHLY_RECORDS"]
    item_findings, item_table = _monthly_item_signals(monthly)
    findings = [*_new_and_cliff(annual), *item_findings]
    return tuple(findings), ((item_table,) if item_table is not None else ())


def _new_and_cliff(records: list[OCLRecord]) -> list[Finding]:
    periods = sorted({row.period for row in records})
    if len(periods) < 2:
        return []
    previous, latest = periods[-2], periods[-1]
    balances: dict[tuple[tuple[str, str, str], str], Decimal] = defaultdict(lambda: Decimal("0"))
    labels: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    categories: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for row in records:
        key = _item_key(row)
        if key is None:
            continue
        balances[(key, row.period)] += row.amount
        labels[key].add(row.source_label)
        categories[key].add(str(row.judgment.category))
    results: list[Finding] = []
    for key in sorted(labels):
        label = " / ".join(sorted(labels[key]))
        category = " / ".join(sorted(categories[key]))
        old = balances[(key, previous)]
        new = balances[(key, latest)]
        if old == 0 and abs(new) >= ABSOLUTE_MATERIALITY:
            results.append(_item_finding("NEW_ITEM", key, label, category, previous, latest, old, new))
        elif new == 0 and abs(old) >= ABSOLUTE_MATERIALITY:
            results.append(_item_finding("CLIFF", key, label, category, previous, latest, old, new))
    return results


def _monthly_item_signals(
    records: list[OCLRecord],
) -> tuple[list[Finding], AnalysisTable | None]:
    periods = sorted({row.period for row in records})
    if len(periods) < 2:
        return [], None
    values: dict[tuple[tuple[str, str, str], str], Decimal] = defaultdict(lambda: Decimal("0"))
    labels: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    categories: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for row in records:
        key = _item_key(row)
        if key is None:
            continue
        values[(key, row.period)] += row.amount
        labels[key].add(row.source_label)
        categories[key].add(str(row.judgment.category))
    if not labels:
        return [], None

    previous, latest = periods[-2], periods[-1]
    latest_total = sum((abs(values[(key, latest)]) for key in labels), Decimal("0"))
    findings: list[Finding] = []
    table_rows: list[tuple[object, ...]] = []
    for key in sorted(labels):
        basis, identifier, entity = key
        label = " / ".join(sorted(labels[key]))
        category = " / ".join(sorted(categories[key]))
        old = values[(key, previous)]
        closing = values[(key, latest)]
        change = closing - old
        prior_periods = periods[-4:-1] if len(periods) >= 4 else ()
        prior_average = (
            sum((values[(key, period)] for period in prior_periods), Decimal("0")) / Decimal(len(prior_periods))
            if prior_periods
            else None
        )
        build = closing - prior_average if prior_average is not None else None
        build_pct = _safe_pct(build, prior_average) if build is not None and prior_average is not None else None
        share = None if latest_total == 0 else float((abs(closing) / latest_total) * Decimal("100"))
        signals: list[str] = []

        if old == 0 and abs(closing) >= ABSOLUTE_MATERIALITY:
            signals.append("NEW_BALANCE")
            findings.append(_item_finding("NEW_ITEM", key, label, category, previous, latest, old, closing))
        if closing == 0 and abs(old) >= ABSOLUTE_MATERIALITY:
            signals.append("FALL_TO_NIL")
            findings.append(_item_finding("CLIFF", key, label, category, previous, latest, old, closing))

        stale_tail = periods[-STALE_MONTHS:] if len(periods) >= STALE_MONTHS else ()
        stale_series = [values[(key, period)] for period in stale_tail]
        if (
            stale_tail
            and abs(stale_series[0]) >= ABSOLUTE_MATERIALITY
            and all(value == stale_series[0] for value in stale_series[1:])
        ):
            signals.append("STALE_BALANCE_PROXY")
            findings.append(_stale_finding(key, label, category, stale_tail, stale_series[0]))

        if build is not None and build != 0 and is_finding_material(build, build_pct):
            signals.append("UNUSUAL_BUILD")
            findings.append(_build_finding(key, label, category, prior_periods, latest, prior_average, closing, build, build_pct))

        if share is not None and share >= ITEM_CONCENTRATION_THRESHOLD and abs(closing) >= ABSOLUTE_MATERIALITY:
            signals.append("MATERIAL_ITEM_CONCENTRATION")
            findings.append(_concentration_finding(key, label, category, latest, closing, share))

        if signals:
            table_rows.append((
                basis,
                identifier,
                label,
                entity,
                category,
                previous,
                old,
                latest,
                closing,
                change,
                prior_average,
                build,
                build_pct,
                share,
                ", ".join(signals),
            ))
    table = AnalysisTable(
        "item_monthly_signals",
        "Item-level monthly balance evidence signals",
        (
            "Identifier Basis", "Item Identifier", "Source_Label", "Entity", "Category",
            "Previous Period", "Previous Balance", "Latest Period", "Latest Balance", "Latest Change",
            "Prior 3M Average", "Latest vs Prior 3M", "Build %", "Latest Absolute Share %", "Evidence Signals",
        ),
        tuple(table_rows),
    )
    return findings, table if table_rows else None


def _item_key(row: OCLRecord) -> tuple[str, str, str] | None:
    source_code = str(row.dimensions.get("source_code") or "").strip()
    item_identifier = str(row.dimensions.get("item_identifier") or "").strip()
    entity = str(row.dimensions.get("entity") or "").strip()
    if source_code:
        return "SOURCE_CODE", source_code, entity
    if item_identifier:
        return "ITEM_IDENTIFIER", item_identifier, entity
    return None


def _item_metrics(key, label: str, category: str) -> dict[str, object]:
    basis, identifier, entity = key
    return {
        "identifier_basis": basis,
        "item_identifier": identifier,
        "source_code": identifier if basis == "SOURCE_CODE" else None,
        "source_label": label,
        "entity": entity or None,
        "category": category,
        "materiality": "MATERIAL",
        "evidence_status": "SIGNAL_NOT_CONCLUSION",
    }


def _item_finding(kind, key, label, category, previous, latest, old, closing) -> Finding:
    metrics = _item_metrics(key, label, category)
    metrics.update({"previous_period": previous, "latest_period": latest})
    if kind == "NEW_ITEM":
        metrics["latest"] = str(closing)
        title = f"New balance: {label}"
        text = f"{label} is nil in {previous} and {closing:,.0f} in {latest}."
    else:
        metrics["previous"] = str(old)
        title = f"Balance reduced to nil: {label}"
        text = f"{label} is {old:,.0f} in {previous} and nil in {latest}."
    return Finding(_item_id(kind, key), title, text, (str(key[1]), previous, latest), kind, metrics, "MEDIUM")


def _stale_finding(key, label, category, periods, amount) -> Finding:
    metrics = _item_metrics(key, label, category)
    metrics.update({"amount": str(amount), "start_period": periods[0], "end_period": periods[-1], "months": len(periods)})
    return Finding(
        _item_id("STALE_BALANCE", key),
        f"Stale monthly balance proxy: {label}",
        f"{label} remains unchanged at {amount:,.0f} across the latest {len(periods)} monthly periods ({periods[0]} to {periods[-1]}).",
        (str(key[1]), periods[0], periods[-1]),
        "STALE_BALANCE",
        metrics,
        "MEDIUM",
    )


def _build_finding(key, label, category, baseline_periods, latest, average, closing, build, pct) -> Finding:
    metrics = _item_metrics(key, label, category)
    metrics.update({"period": latest, "baseline_periods": list(baseline_periods), "baseline_average": str(average), "closing": str(closing), "change": str(build), "change_pct": pct})
    direction = "build" if build > 0 else "unwind"
    return Finding(
        _item_id("ITEM_UNUSUAL_BUILD", key),
        f"Unusual monthly {direction}: {label}",
        f"{label} closes at {closing:,.0f} in {latest} versus a prior three-month average of {average:,.0f}, a {direction} of {abs(build):,.0f}" + (f" ({abs(pct):.1f}%)." if pct is not None else "."),
        (str(key[1]), *baseline_periods, latest),
        "ITEM_UNUSUAL_BUILD",
        metrics,
        "MEDIUM",
    )


def _concentration_finding(key, label, category, latest, closing, share) -> Finding:
    metrics = _item_metrics(key, label, category)
    metrics.update({"period": latest, "closing": str(closing), "share_pct": share})
    return Finding(
        _item_id("ITEM_CONCENTRATION", key),
        f"Material item concentration: {label}",
        f"{label} represents {share:.1f}% of the absolute in-scope monthly OCL balance at {latest}; this is an evidence signal, not an FDD treatment conclusion.",
        (str(key[1]), latest),
        "ITEM_CONCENTRATION",
        metrics,
        "MEDIUM",
    )


def _item_id(kind: str, key: tuple[str, str, str]) -> str:
    return f"F_{_slug(kind)}_{_slug('|'.join(key))}"


def _safe_pct(change: Decimal, base: Decimal) -> float | None:
    if base == 0:
        return None
    return float((change / abs(base)) * Decimal("100"))


def _slug(value: str) -> str:
    text = "".join(character if character.isalnum() else "_" for character in value.upper())
    return "_".join(part for part in text.split("_") if part)[:40] or "ITEM"
