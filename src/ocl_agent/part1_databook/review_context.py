"""Compact machine-readable review context for the AI host.

This file reduces repeated workbook inspection. All amounts are deterministic
aggregations of the shared OCL record model; the AI host only interprets them.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from ocl_agent.part1_databook.input_contract import StandardizedPackage
from ocl_agent.part1_databook.semantic_handoff import SemanticHandoff
from ocl_agent.schemas import OCLRecord


def write_review_context(package: StandardizedPackage, handoff: SemanticHandoff, records: tuple[OCLRecord, ...], output_path: Path) -> Path:
    grouped: dict[tuple[str, str, str], dict[str, object]] = {}
    for row in records:
        code = _text(row.dimensions.get("source_code")) or ""
        entity = _text(row.dimensions.get("entity")) or ""
        key = (row.source_label, code, entity)
        item = grouped.setdefault(key, {"source_label": row.source_label, "source_code": code or None, "entity": entity or None, "period_amounts": {}, "datasets": set(), "sample_source_record_ids": [], "judgment": {"scope": row.judgment.scope.value, "category": row.judgment.category, "parent_category": row.judgment.parent_category, "management_view": row.judgment.management_view, "fdd_view": row.judgment.fdd_view, "normality": row.judgment.normality, "review_status": row.judgment.review_status.value, "reason": row.judgment.reason}})
        period_amounts = item["period_amounts"]
        current = Decimal(str(period_amounts.get(row.period, "0")))
        period_amounts[row.period] = str(current + row.amount)
        item["datasets"].add(str(row.dimensions.get("dataset_file") or ""))
        sample_ids = item["sample_source_record_ids"]
        if len(sample_ids) < 3 and row.source.source_record_id not in sample_ids:
            sample_ids.append(row.source.source_record_id)
    review_items = []
    for key in sorted(grouped, key=lambda value: tuple(part.casefold() for part in value)):
        item = grouped[key]
        item["datasets"] = sorted(value for value in item["datasets"] if value)
        item["period_amounts"] = dict(sorted(item["period_amounts"].items()))
        review_items.append(item)
    metadata = package.metadata_payload()
    payload = {"review_context_version": "1.0", "package_id": handoff.package_id, "dataset_metadata": [{"logical_dataset_id": item.get("logical_dataset_id"), "name": item.get("name"), "role": item.get("role"), "dataset_grain": item.get("dataset_grain"), "main_measures": item.get("main_measures", []), "key_dimensions": item.get("key_dimensions", [])} for item in metadata.get("logical_datasets", [])], "unresolved_upstream_questions": metadata.get("unresolved_questions", []), "semantic_unresolved_matters": list(handoff.unresolved_matters), "review_items": review_items}
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path


def _text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
