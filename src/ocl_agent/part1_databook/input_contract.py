"""Validated handoff from fdd-data-preparation into OCL.

The OCL skill consumes approved standardized CSV outputs and their published
metadata. It does not rediscover or reshape raw client workbooks in the normal
workflow.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

AUDIT_CSV_NAMES = {"lineage.csv", "field_lineage.csv", "exclusions.csv", "processing_issues.csv"}
PUBLISHABLE_STATUSES = {"COMPLETED", "COMPLETED_WITH_WARNINGS"}


class InputContractError(ValueError):
    pass


@dataclass(frozen=True)
class DatasetProfile:
    path: Path
    columns: tuple[str, ...]
    row_count: int
    sample_rows: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class StandardizedPackage:
    root: Path
    datasets: tuple[Path, ...]
    metadata: Path | None
    execution_manifest: Path | None
    lineage: Path | None
    field_lineage: Path | None
    warnings: tuple[str, ...] = ()

    def metadata_payload(self) -> dict[str, Any]:
        return _read_json(self.metadata) if self.metadata else {}

    def manifest_payload(self) -> dict[str, Any]:
        return _read_json(self.execution_manifest) if self.execution_manifest else {}


def discover_standardized_package(root: Path) -> StandardizedPackage:
    root = Path(root).resolve()
    if not root.exists() or not root.is_dir():
        raise InputContractError(f"Standardized output directory does not exist: {root}")

    datasets = tuple(sorted(path for path in root.glob("*.csv") if path.name not in AUDIT_CSV_NAMES))
    if not datasets:
        raise InputContractError("No standardized CSV dataset was found in the approved publication directory.")

    manifest = root / "execution_manifest.json"
    metadata = root / "databook_metadata.json"
    lineage = root / "lineage.csv"
    field_lineage = root / "field_lineage.csv"
    warnings: list[str] = []

    if manifest.exists():
        payload = _read_json(manifest)
        status = payload.get("final_execution_status")
        if status not in PUBLISHABLE_STATUSES:
            raise InputContractError(f"Upstream execution is not publishable: {status!r}")
        created = {str(name) for name in payload.get("outputs_created", [])}
        if created:
            unexpected = sorted(path.name for path in datasets if path.name not in created)
            if unexpected:
                raise InputContractError(
                    "Standardized directory contains CSV data outputs not declared by the upstream execution manifest: "
                    + ", ".join(unexpected)
                )
    else:
        warnings.append("execution_manifest.json is missing; upstream completion status cannot be independently verified.")

    if not metadata.exists():
        warnings.append("databook_metadata.json is missing; semantic interpretation will rely on the explicit OCL handoff.")
    if not lineage.exists():
        warnings.append("lineage.csv is absent; record-level Source_Record_ID lineage must be preserved in the standardized dataset.")
    if not field_lineage.exists():
        warnings.append("field_lineage.csv is absent; field-level lineage is unavailable in this publication.")

    return StandardizedPackage(
        root=root,
        datasets=datasets,
        metadata=metadata if metadata.exists() else None,
        execution_manifest=manifest if manifest.exists() else None,
        lineage=lineage if lineage.exists() else None,
        field_lineage=field_lineage if field_lineage.exists() else None,
        warnings=tuple(warnings),
    )


def profile_dataset(path: Path, *, sample_limit: int = 8) -> DatasetProfile:
    """Read one standardized CSV once, keeping only a bounded sample in memory."""
    path = Path(path)
    if sample_limit < 0:
        raise ValueError("sample_limit must be non-negative")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise InputContractError(f"Standardized dataset has no header row: {path.name}")
        columns = tuple(str(name) for name in reader.fieldnames)
        if not columns or any(not name.strip() for name in columns):
            raise InputContractError(f"Standardized dataset has blank column names: {path.name}")
        if len(set(columns)) != len(columns):
            raise InputContractError(f"Standardized dataset has duplicate column names: {path.name}")
        sample: list[dict[str, str]] = []
        row_count = 0
        for row in reader:
            row_count += 1
            if len(sample) < sample_limit:
                sample.append({key: value for key, value in row.items()})
    return DatasetProfile(path, columns, row_count, tuple(sample))


def profile_package(package: StandardizedPackage, *, sample_limit: int = 8) -> tuple[DatasetProfile, ...]:
    return tuple(profile_dataset(path, sample_limit=sample_limit) for path in package.datasets)


def _read_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InputContractError(f"Unable to read valid JSON from {path.name}: {error}") from error
    if not isinstance(payload, dict):
        raise InputContractError(f"Expected a JSON object in {path.name}.")
    return payload
