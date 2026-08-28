"""Explicit AI-host/human semantic handoff from standardized data into OCL.

Python validates the handoff but does not guess accounting meaning from arbitrary
column names. The AI host may prepare the handoff from upstream metadata and a
bounded input review; reviewed user configuration remains authoritative.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Mapping

from ocl_agent.part1_databook.input_contract import DatasetProfile, StandardizedPackage

class SemanticHandoffError(ValueError):
    pass

class DatasetUsage(StrEnum):
    OCL_RECORDS = "OCL_RECORDS"
    MONTHLY_RECORDS = "MONTHLY_RECORDS"
    MOVEMENT_RECORDS = "MOVEMENT_RECORDS"
    TB_CONTROL = "TB_CONTROL"
    SUPPORTING_EVIDENCE = "SUPPORTING_EVIDENCE"
    REVENUE_CONTEXT = "REVENUE_CONTEXT"
    PAYROLL_CONTEXT = "PAYROLL_CONTEXT"
    EXPENSE_CONTEXT = "EXPENSE_CONTEXT"
    IGNORE = "IGNORE"

RECORD_USAGES = {DatasetUsage.OCL_RECORDS, DatasetUsage.MONTHLY_RECORDS}

@dataclass(frozen=True)
class FieldBinding:
    source_record_id: str | None = None
    period: str | None = None
    amount: str | None = None
    source_label: str | None = None
    source_code: str | None = None
    item_identifier: str | None = None
    entity: str | None = None
    currency: str | None = None
    movement_type: str | None = None
    movement_multiplier: str | None = None

    def named_columns(self) -> tuple[str, ...]:
        return tuple(value for value in (
            self.source_record_id, self.period, self.amount, self.source_label,
            self.source_code, self.item_identifier, self.entity, self.currency, self.movement_type,
            self.movement_multiplier,
        ) if value)

@dataclass(frozen=True)
class DatasetBinding:
    file: str
    usages: tuple[DatasetUsage, ...]
    fields: FieldBinding
    dimensions: tuple[str, ...] = ()
    notes: str = ""
    usage_filters: dict[DatasetUsage, dict[str, tuple[str, ...]]] = field(default_factory=dict)

    def filters_for(self, usage: DatasetUsage) -> dict[str, tuple[str, ...]]:
        return self.usage_filters.get(usage, {})

@dataclass(frozen=True)
class PeriodAlignment:
    annual_period: str
    monthly_period: str


@dataclass(frozen=True)
class ControlBinding:
    """Exact source-backed control definition; no keyword guessing is allowed."""
    control_id: str
    dataset_file: str
    period_field: str
    amount_field: str
    filters: dict[str, tuple[str, ...]]
    whole_dataset: bool = False


@dataclass(frozen=True)
class SemanticHandoff:
    handoff_version: str
    status: str
    package_id: str
    datasets: tuple[DatasetBinding, ...]
    unresolved_matters: tuple[str, ...] = ()
    monthly_to_annual: tuple[PeriodAlignment, ...] = ()
    controls: tuple[ControlBinding, ...] = ()

    def record_bindings(self) -> tuple[DatasetBinding, ...]:
        return tuple(binding for binding in self.datasets if set(binding.usages) & RECORD_USAGES)


def package_id(package: StandardizedPackage) -> str:
    metadata = package.metadata_payload()
    if metadata.get("workflow_run_id"):
        return str(metadata["workflow_run_id"])
    manifest = package.manifest_payload()
    if manifest.get("execution_id"):
        return str(manifest["execution_id"])
    return package.root.name


def write_semantic_handoff_draft(
    package: StandardizedPackage,
    profiles: tuple[DatasetProfile, ...],
    output_path: Path,
) -> Path:
    """Write a non-executable draft; only exact canonical fields are prefilled."""
    datasets = []
    for profile in profiles:
        by_fold = {name.casefold(): name for name in profile.columns}
        fields = {
            "source_record_id": by_fold.get("source_record_id"),
            "period": by_fold.get("period"),
            "amount": by_fold.get("amount"),
            "source_label": by_fold.get("source_label"),
            "source_code": by_fold.get("source_code"),
            "item_identifier": by_fold.get("item_identifier") or by_fold.get("item_id"),
            "entity": by_fold.get("entity"),
            "currency": by_fold.get("currency"),
            "movement_type": by_fold.get("movement_type"),
        }
        datasets.append({
            "file": profile.path.name,
            "usages": [],
            "fields": fields,
            "dimensions": [],
            "usage_filters": {},
            "available_columns": list(profile.columns),
            "row_count": profile.row_count,
            "notes": "AI host: assign usages and confirm field roles from upstream metadata and current source evidence.",
        })
    payload = {
        "handoff_version": "1.0",
        "status": "DRAFT",
        "package_id": package_id(package),
        "datasets": datasets,
        "unresolved_matters": [],
        "monthly_to_annual": [],
        "controls": [],
    }
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path


def load_semantic_handoff(
    path: Path,
    package: StandardizedPackage,
    profiles: tuple[DatasetProfile, ...],
    *,
    require_confirmed: bool = True,
) -> SemanticHandoff:
    path = Path(path)
    if not path.exists():
        raise SemanticHandoffError(f"Semantic handoff does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SemanticHandoffError(f"Semantic handoff is not valid JSON: {error}") from error
    if not isinstance(payload, dict):
        raise SemanticHandoffError("Semantic handoff must be a JSON object.")

    version = str(payload.get("handoff_version", ""))
    if version != "1.0":
        raise SemanticHandoffError(f"Unsupported semantic handoff version: {version!r}")
    status = str(payload.get("status", "")).upper()
    if status not in {"DRAFT", "CONFIRMED"}:
        raise SemanticHandoffError("Semantic handoff status must be DRAFT or CONFIRMED.")
    if require_confirmed and status != "CONFIRMED":
        raise SemanticHandoffError("Semantic handoff is still DRAFT; the AI host must confirm it before OCL records are built.")

    current_package_id = package_id(package)
    bound_package_id = str(payload.get("package_id", ""))
    if bound_package_id != current_package_id:
        raise SemanticHandoffError(
            f"Semantic handoff belongs to package {bound_package_id!r}, not current package {current_package_id!r}."
        )

    profile_by_name = {profile.path.name: profile for profile in profiles}
    bindings: list[DatasetBinding] = []
    seen_files: set[str] = set()
    for index, item in enumerate(payload.get("datasets", []), start=1):
        if not isinstance(item, dict):
            raise SemanticHandoffError(f"Dataset binding #{index} must be an object.")
        filename = str(item.get("file", ""))
        if filename not in profile_by_name:
            raise SemanticHandoffError(f"Semantic handoff references an unknown standardized dataset: {filename!r}")
        if filename in seen_files:
            raise SemanticHandoffError(f"Semantic handoff contains duplicate dataset binding: {filename!r}")
        seen_files.add(filename)
        try:
            usages = tuple(DatasetUsage(str(value).upper()) for value in item.get("usages", []))
        except ValueError as error:
            raise SemanticHandoffError(f"Dataset {filename!r} contains an unsupported usage.") from error
        if DatasetUsage.IGNORE in usages and len(usages) > 1:
            raise SemanticHandoffError(f"Dataset {filename!r}: IGNORE cannot be combined with other usages.")
        raw_fields = item.get("fields") or {}
        if not isinstance(raw_fields, dict):
            raise SemanticHandoffError(f"Dataset {filename!r}: fields must be an object.")
        fields = FieldBinding(**{key: _clean_optional(raw_fields.get(key)) for key in FieldBinding.__dataclass_fields__})
        dimensions = tuple(str(value) for value in item.get("dimensions", []) if str(value).strip())
        if len(set(dimensions)) != len(dimensions):
            raise SemanticHandoffError(f"Dataset {filename!r}: dimensions contain duplicates.")

        available = set(profile_by_name[filename].columns)
        referenced = set(fields.named_columns()) | set(dimensions)
        missing = sorted(referenced - available)
        if missing:
            raise SemanticHandoffError(f"Dataset {filename!r} references missing columns: {', '.join(missing)}")
        overlap = sorted(set(fields.named_columns()) & set(dimensions))
        if overlap:
            raise SemanticHandoffError(f"Dataset {filename!r}: role fields cannot also be dimensions: {', '.join(overlap)}")
        if set(usages) & RECORD_USAGES:
            missing_roles = [name for name in ("source_record_id", "period", "amount", "source_label") if not getattr(fields, name)]
            if missing_roles:
                raise SemanticHandoffError(
                    f"Dataset {filename!r} is used for OCL records but is missing required field roles: {', '.join(missing_roles)}"
                )
        if DatasetUsage.MOVEMENT_RECORDS in usages:
            missing_roles = [name for name in ("source_record_id", "period", "amount", "source_label", "movement_type") if not getattr(fields, name)]
            if missing_roles:
                raise SemanticHandoffError(
                    f"Dataset {filename!r} is used for movements but is missing roles: {', '.join(missing_roles)}"
                )
        usage_filters = _parse_usage_filters(filename, item.get("usage_filters", {}), usages, available)
        bindings.append(DatasetBinding(filename, usages, fields, dimensions, str(item.get("notes", "")), usage_filters))

    alignments: list[PeriodAlignment] = []
    seen_annual: set[str] = set()
    for item in payload.get("monthly_to_annual", []):
        if not isinstance(item, dict):
            raise SemanticHandoffError("monthly_to_annual entries must be objects.")
        annual = str(item.get("annual_period", "")).strip()
        monthly = str(item.get("monthly_period", "")).strip()
        if not annual or not monthly:
            raise SemanticHandoffError("monthly_to_annual requires annual_period and monthly_period.")
        if annual in seen_annual:
            raise SemanticHandoffError(f"Duplicate annual period in monthly_to_annual: {annual!r}")
        seen_annual.add(annual)
        alignments.append(PeriodAlignment(annual, monthly))

    control_bindings: list[ControlBinding] = []
    seen_control_ids: set[str] = set()
    binding_by_file = {binding.file: binding for binding in bindings}
    supported_controls = {"chk_listing_vs_tb", "chk_scope_reconciles"}
    for item in payload.get("controls", []):
        if not isinstance(item, dict):
            raise SemanticHandoffError("controls entries must be objects.")
        control_id = str(item.get("control_id", "")).strip()
        dataset_file = str(item.get("dataset_file", "")).strip()
        period_field = str(item.get("period_field", "")).strip()
        amount_field = str(item.get("amount_field", "")).strip()
        if control_id not in supported_controls:
            raise SemanticHandoffError(f"Unsupported source-backed control: {control_id!r}")
        if control_id in seen_control_ids:
            raise SemanticHandoffError(f"Duplicate control binding: {control_id!r}")
        seen_control_ids.add(control_id)
        if dataset_file not in profile_by_name:
            raise SemanticHandoffError(f"Control {control_id!r} references unknown dataset {dataset_file!r}.")
        dataset_binding = binding_by_file.get(dataset_file)
        if dataset_binding is None or DatasetUsage.TB_CONTROL not in dataset_binding.usages:
            raise SemanticHandoffError(
                f"Control {control_id!r} dataset {dataset_file!r} must be explicitly assigned TB_CONTROL usage."
            )
        raw_filters = item.get("filters") or {}
        if not isinstance(raw_filters, dict):
            raise SemanticHandoffError(f"Control {control_id!r}: filters must be an object.")
        whole_dataset = bool(item.get("whole_dataset")) or str(item.get("population") or "").upper() == "WHOLE_DATASET"
        filters: dict[str, tuple[str, ...]] = {}
        for column, values in raw_filters.items():
            if isinstance(values, str):
                normalized_values = (values,)
            elif isinstance(values, list):
                normalized_values = tuple(str(value) for value in values)
            else:
                raise SemanticHandoffError(
                    f"Control {control_id!r}: filter values for {column!r} must be a string or list of strings."
                )
            if not normalized_values:
                raise SemanticHandoffError(f"Control {control_id!r}: filter {column!r} has no values.")
            filters[str(column)] = normalized_values
        if not filters and not whole_dataset:
            raise SemanticHandoffError(
                f"Control {control_id!r} requires explicit filters or whole_dataset=true."
            )
        available = set(profile_by_name[dataset_file].columns)
        referenced = {period_field, amount_field, *filters}
        missing = sorted(value for value in referenced if not value or value not in available)
        if missing:
            raise SemanticHandoffError(
                f"Control {control_id!r} references missing/blank columns: {', '.join(repr(value) for value in missing)}"
            )
        control_bindings.append(ControlBinding(control_id, dataset_file, period_field, amount_field, filters, whole_dataset))

    handoff = SemanticHandoff(
        version,
        status,
        bound_package_id,
        tuple(bindings),
        tuple(str(value) for value in payload.get("unresolved_matters", [])),
        tuple(alignments),
        tuple(control_bindings),
    )
    if require_confirmed and not handoff.record_bindings():
        raise SemanticHandoffError("Confirmed semantic handoff contains no dataset assigned to OCL_RECORDS or MONTHLY_RECORDS.")
    return handoff


def _clean_optional(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def row_matches_usage_filter(
    row: Mapping[str, Any],
    binding: DatasetBinding,
    usage: DatasetUsage,
) -> bool:
    """Return whether a standardized row matches one usage's exact-value filters."""
    return all(row.get(column) in allowed for column, allowed in binding.filters_for(usage).items())


def _parse_usage_filters(
    filename: str,
    raw_usage_filters: Any,
    usages: tuple[DatasetUsage, ...],
    available_columns: set[str],
) -> dict[DatasetUsage, dict[str, tuple[str, ...]]]:
    if not isinstance(raw_usage_filters, dict):
        raise SemanticHandoffError(f"Dataset {filename!r}: usage_filters must be an object.")
    if raw_usage_filters and DatasetUsage.IGNORE in usages:
        raise SemanticHandoffError(f"Dataset {filename!r}: IGNORE cannot have usage filters.")

    normalized: dict[DatasetUsage, dict[str, tuple[str, ...]]] = {}
    for raw_usage, raw_filters in raw_usage_filters.items():
        try:
            usage = DatasetUsage(str(raw_usage).upper())
        except ValueError as error:
            raise SemanticHandoffError(
                f"Dataset {filename!r}: usage_filters contains an unsupported usage {raw_usage!r}."
            ) from error
        if usage not in usages:
            raise SemanticHandoffError(
                f"Dataset {filename!r}: filter usage {usage.value!r} is not present in dataset usages."
            )
        if usage == DatasetUsage.IGNORE:
            raise SemanticHandoffError(f"Dataset {filename!r}: IGNORE cannot have usage filters.")
        if not isinstance(raw_filters, dict):
            raise SemanticHandoffError(
                f"Dataset {filename!r}: filters for usage {usage.value!r} must be an object."
            )
        if not raw_filters:
            raise SemanticHandoffError(
                f"Dataset {filename!r}: filters for usage {usage.value!r} contain no columns."
            )

        filters: dict[str, tuple[str, ...]] = {}
        for raw_column, raw_values in raw_filters.items():
            column = str(raw_column)
            if column not in available_columns:
                raise SemanticHandoffError(
                    f"Dataset {filename!r}: usage filter references missing column {column!r}."
                )
            if isinstance(raw_values, str):
                values = (raw_values,)
            elif isinstance(raw_values, list) and all(isinstance(value, str) for value in raw_values):
                values = tuple(raw_values)
            else:
                raise SemanticHandoffError(
                    f"Dataset {filename!r}: filter values for {usage.value!r}/{column!r} "
                    "must be a string or list of strings."
                )
            if not values:
                raise SemanticHandoffError(
                    f"Dataset {filename!r}: filter {usage.value!r}/{column!r} has no values."
                )
            filters[column] = values
        normalized[usage] = filters
    return normalized
