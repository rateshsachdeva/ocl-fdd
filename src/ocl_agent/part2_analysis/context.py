"""Optional contextual datasets for Part 2.

Revenue/payroll context is used only when the semantic handoff explicitly binds
period and amount fields. Missing context never blocks the OCL workflow.
"""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation

from ocl_agent.part1_databook.input_contract import StandardizedPackage
from ocl_agent.part1_databook.semantic_handoff import DatasetUsage, SemanticHandoff


def load_context(package: StandardizedPackage, handoff: SemanticHandoff) -> dict[str, dict[str, Decimal]]:
    result: dict[str, dict[str, Decimal]] = {}
    usage_keys = {
        DatasetUsage.REVENUE_CONTEXT: "revenue",
        DatasetUsage.PAYROLL_CONTEXT: "payroll",
    }
    for binding in handoff.datasets:
        matched = [usage for usage in usage_keys if usage in binding.usages]
        if not matched or not binding.fields.period or not binding.fields.amount:
            continue
        with (package.root / binding.file).open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                period = str(row.get(binding.fields.period, "") or "").strip()
                raw = str(row.get(binding.fields.amount, "") or "").strip()
                if not period or not raw:
                    continue
                try:
                    amount = Decimal(raw.replace(",", ""))
                except InvalidOperation:
                    continue
                for usage in matched:
                    key = usage_keys[usage]
                    bucket = result.setdefault(key, {})
                    bucket[period] = bucket.get(period, Decimal("0")) + amount
    return result
