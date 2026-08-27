"""Optional contextual datasets for Part 2.

Revenue, payroll and expense context is used only when the semantic handoff
explicitly binds period and amount fields. Missing context never blocks the OCL
workflow and is surfaced as unsupported analysis rather than guessed.
"""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from typing import Iterable

from ocl_agent.part1_databook.input_contract import StandardizedPackage
from ocl_agent.part1_databook.semantic_handoff import DatasetUsage, SemanticHandoff, row_matches_usage_filter
from ocl_agent.schemas import AnalysisResult, AnalysisTable, OCLRecord, Scope


def load_context(package: StandardizedPackage, handoff: SemanticHandoff) -> dict[str, dict[str, Decimal]]:
    result: dict[str, dict[str, Decimal]] = {}
    usage_keys = {
        DatasetUsage.REVENUE_CONTEXT: "revenue",
        DatasetUsage.PAYROLL_CONTEXT: "payroll",
        DatasetUsage.EXPENSE_CONTEXT: "expense",
    }
    for binding in handoff.datasets:
        matched = [usage for usage in usage_keys if usage in binding.usages]
        if not matched or not binding.fields.period or not binding.fields.amount:
            continue
        with (package.root / binding.file).open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                period = str(row.get(binding.fields.period, "") or "").strip()
                raw = str(row.get(binding.fields.amount, "") or "").strip()
                if not period or not raw:
                    continue
                try:
                    amount = Decimal(raw.replace(",", ""))
                except InvalidOperation:
                    continue
                for usage in matched:
                    if not row_matches_usage_filter(row, binding, usage):
                        continue
                    key = usage_keys[usage]
                    bucket = result.setdefault(key, {})
                    bucket[period] = bucket.get(period, Decimal("0")) + amount
    return result


def enrich_with_context(analysis: AnalysisResult, records: Iterable[OCLRecord], context: dict[str, dict[str, Decimal]]) -> AnalysisResult:
    if not context or not analysis.annual_periods:
        return analysis
    totals: dict[str, Decimal] = {}
    for row in records:
        if row.dimensions.get("record_usage") == "MONTHLY_RECORDS" or row.judgment.scope != Scope.IN_SCOPE:
            continue
        totals[row.period] = totals.get(row.period, Decimal("0")) + row.amount
    rows = []
    for period in analysis.annual_periods:
        ocl = totals.get(period, Decimal("0"))
        revenue = context.get("revenue", {}).get(period)
        payroll = context.get("payroll", {}).get(period)
        expense = context.get("expense", {}).get(period)
        revenue_pct = None if revenue in {None, Decimal("0")} else float((ocl / abs(revenue)) * Decimal("100"))
        payroll_pct = None if payroll in {None, Decimal("0")} else float((ocl / abs(payroll)) * Decimal("100"))
        expense_pct = None if expense in {None, Decimal("0")} else float((ocl / abs(expense)) * Decimal("100"))
        rows.append((period, ocl, revenue, revenue_pct, payroll, payroll_pct, expense, expense_pct))
    table = AnalysisTable(
        "context_ratios",
        "OCL context ratios",
        ("Period", "OCL", "Revenue", "OCL / Revenue %", "Payroll", "OCL / Payroll %", "Expense Context", "OCL / Expense %"),
        tuple(rows),
    )
    return AnalysisResult(analysis.findings, (*analysis.tables, table), analysis.annual_periods, analysis.monthly_periods, analysis.latest_annual_period)
