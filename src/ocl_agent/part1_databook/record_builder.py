"""Deterministic construction of OCL records from a confirmed semantic handoff."""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from ocl_agent.part1_databook.input_contract import StandardizedPackage
from ocl_agent.part1_databook.judgments import JudgmentStore
from ocl_agent.part1_databook.semantic_handoff import (
    DatasetBinding,
    DatasetUsage,
    SemanticHandoff,
    row_matches_usage_filter,
)
from ocl_agent.schemas import OCLRecord, SourceReference

@dataclass(frozen=True)
class BuildIssue:
    dataset_file: str
    csv_row: int
    source_record_id: str
    issue_type: str
    message: str

@dataclass(frozen=True)
class RecordBuildResult:
    records: tuple[OCLRecord, ...]
    issues: tuple[BuildIssue, ...]
    input_rows_by_dataset: dict[str, int]
    excluded_rows_by_dataset: dict[str, int] = field(default_factory=dict)

    @property
    def unresolved_row_count(self) -> int:
        return len(self.issues)


def build_ocl_records(package: StandardizedPackage, handoff: SemanticHandoff, judgments: JudgmentStore) -> RecordBuildResult:
    records: list[OCLRecord] = []
    issues: list[BuildIssue] = []
    input_counts: dict[str, int] = {}
    excluded_counts: dict[str, int] = {}
    for binding in handoff.record_bindings():
        dataset_records, dataset_issues, count, excluded = _build_dataset(
            package.root / binding.file, binding, judgments
        )
        records.extend(dataset_records)
        issues.extend(dataset_issues)
        input_counts[binding.file] = count
        excluded_counts[binding.file] = excluded
    return RecordBuildResult(tuple(records), tuple(issues), input_counts, excluded_counts)


def _build_dataset(
    path: Path,
    binding: DatasetBinding,
    judgments: JudgmentStore,
) -> tuple[list[OCLRecord], list[BuildIssue], int, int]:
    fields = binding.fields
    assert fields.source_record_id and fields.period and fields.amount and fields.source_label
    records: list[OCLRecord] = []
    issues: list[BuildIssue] = []
    count = 0
    excluded = 0
    usage = _record_usage(binding)
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for csv_row, row in enumerate(reader, start=2):
            count += 1
            if not row_matches_usage_filter(row, binding, usage):
                excluded += 1
                continue
            source_record_id = str(row.get(fields.source_record_id, "") or "").strip()
            period = str(row.get(fields.period, "") or "").strip()
            source_label = str(row.get(fields.source_label, "") or "").strip()
            raw_amount = row.get(fields.amount)
            missing = []
            if not source_record_id: missing.append("source_record_id")
            if not period: missing.append("period")
            if not source_label: missing.append("source_label")
            if raw_amount is None or str(raw_amount).strip() == "": missing.append("amount")
            if missing:
                issues.append(BuildIssue(binding.file, csv_row, source_record_id, "MISSING_REQUIRED_VALUE", "Missing required standardized value(s): " + ", ".join(missing)))
                continue
            try:
                amount = Decimal(str(raw_amount).strip().replace(",", ""))
            except (InvalidOperation, ValueError):
                issues.append(BuildIssue(binding.file, csv_row, source_record_id, "INVALID_AMOUNT", f"Amount cannot be parsed as a decimal: {raw_amount!r}"))
                continue
            source = _source_reference(source_record_id)
            dimensions: dict[str, Any] = {"dataset_file": binding.file, "record_usage": usage.value, "standardized_csv_row": csv_row}
            for role, column in (("source_code", fields.source_code), ("entity", fields.entity), ("currency", fields.currency)):
                if column:
                    dimensions[role] = row.get(column)
            for column in binding.dimensions:
                dimensions[column] = row.get(column)
            records.append(OCLRecord(source=source, period=period, amount=amount, source_label=source_label, judgment=judgments.get(source_label, dimensions.get("source_code"), dimensions.get("entity")), dimensions=dimensions))
    return records, issues, count, excluded


def _record_usage(binding: DatasetBinding) -> DatasetUsage:
    return DatasetUsage.MONTHLY_RECORDS if DatasetUsage.MONTHLY_RECORDS in binding.usages else DatasetUsage.OCL_RECORDS


def _source_reference(value: str) -> SourceReference:
    source_file = source_sheet = None
    try:
        payload = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        payload = None
    if isinstance(payload, dict):
        source_file = _optional_text(payload.get("source_id"))
        source_sheet = _optional_text(payload.get("worksheet_name"))
    return SourceReference(source_record_id=value, source_file=source_file, source_sheet=source_sheet, source_cell=None)


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
