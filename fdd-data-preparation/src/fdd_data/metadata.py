"""Deterministic publishing of AI-derived Dataset Map metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


METADATA_TYPES = {
    "DATASET_PURPOSE",
    "CURRENCY",
    "CURRENCY_BASIS",
    "UNIT_SCALE",
    "REPORTING_FREQUENCY",
    "PERIOD_START",
    "PERIOD_END",
    "FISCAL_YEAR",
    "CALENDAR_YEAR",
    "MONTH",
    "QUARTER",
    "FISCAL_YEAR_END",
    "ENTITY",
    "BUSINESS_UNIT",
    "GEOGRAPHY",
    "SCENARIO",
    "ACCOUNTING_REPORTING_BASIS",
    "MAIN_MEASURE",
    "KEY_DIMENSION",
    "DATASET_GRAIN",
    "OTHER_CONTEXT",
}
METADATA_STATUSES = {"EVIDENCED", "UNKNOWN", "UNRESOLVED"}
REPORTING_FREQUENCIES = {"DAILY", "WEEKLY", "MONTHLY", "QUARTERLY", "ANNUAL", "MIXED", "UNKNOWN"}
SCENARIOS = {"ACTUAL", "BUDGET", "FORECAST", "PRIOR_YEAR", "OTHER", "UNKNOWN"}


def publish_databook_metadata(
    dataset_map: dict[str, Any], workflow_run_id: str, output_path: Path
) -> dict[str, Any]:
    """Publish metadata strictly from the validated Dataset Map without reinterpretation."""
    logical_datasets = []
    for dataset in dataset_map.get("logical_datasets", []):
        metadata = dataset.get("metadata", [])
        logical_datasets.append({
            "logical_dataset_id": dataset.get("logical_dataset_id"),
            "name": dataset.get("name"),
            "role": dataset.get("role"),
            "dataset_grain": dataset.get("proposed_grain"),
            "grain_confidence": dataset.get("grain_confidence"),
            "metadata": metadata,
            "period_coverage": _metadata_for(metadata, {
                "PERIOD_START", "PERIOD_END", "FISCAL_YEAR", "CALENDAR_YEAR", "MONTH", "QUARTER", "FISCAL_YEAR_END", "REPORTING_FREQUENCY",
            }),
            "currency_unit_information": _metadata_for(metadata, {"CURRENCY", "CURRENCY_BASIS", "UNIT_SCALE"}),
            "entity_geography_information": _metadata_for(metadata, {"ENTITY", "BUSINESS_UNIT", "GEOGRAPHY"}),
            "scenarios": _metadata_for(metadata, {"SCENARIO"}),
            "main_measures": _metadata_for(metadata, {"MAIN_MEASURE"}),
            "key_dimensions": _metadata_for(metadata, {"KEY_DIMENSION"}),
            "unresolved_metadata": [item for item in metadata if item.get("status") in {"UNKNOWN", "UNRESOLVED"}],
        })
    document = {
        "metadata_version": "1.0",
        "workflow_run_id": workflow_run_id,
        "profile_run_id": dataset_map.get("run_info", {}).get("profile_run_id"),
        "source_package_summary": dataset_map.get("global_observations", {}).get("source_package_interpretation"),
        "logical_datasets": logical_datasets,
        "unresolved_questions": dataset_map.get("global_observations", {}).get("unresolved_questions", []),
    }
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return document


def _metadata_for(metadata: list[dict[str, Any]], metadata_types: set[str]) -> list[dict[str, Any]]:
    return [item for item in metadata if item.get("metadata_type") in metadata_types]
