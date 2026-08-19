"""Canonical physical-field, source-row, and output-lineage identities."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable


SourceRowIdentity = tuple[str, str, str, int]


def source_field_id(
    source_id: str,
    worksheet_name: str,
    region_id: str,
    physical_column: int,
) -> str:
    """Return a stable opaque ID for one physical field in one source context."""
    identity = {
        "physical_column": physical_column,
        "region_id": region_id,
        "source_id": source_id,
        "worksheet_name": worksheet_name,
    }
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:16].upper()
    return f"FIELD_{digest}"


def source_row_identity(
    source_id: str,
    worksheet_name: str,
    region_id: str,
    physical_row: int,
) -> SourceRowIdentity:
    """Return the canonical identity of one physical source row."""
    return source_id, worksheet_name, region_id, physical_row


def source_row_payload(identity: SourceRowIdentity) -> dict[str, Any]:
    source_id, worksheet_name, region_id, physical_row = identity
    return {
        "physical_row": physical_row,
        "region_id": region_id,
        "source_id": source_id,
        "worksheet_name": worksheet_name,
    }


def output_record_id(
    source_row: SourceRowIdentity,
    generated_dimensions: dict[str, Any] | None = None,
) -> str:
    """Extend physical row identity with transformation-created dimensions."""
    payload = source_row_payload(source_row)
    payload["generated_dimensions"] = generated_dimensions or {}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def profile_field_index(profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index every profiled physical field and reject ambiguous duplicate IDs."""
    result: dict[str, dict[str, Any]] = {}
    for workbook in profile.get("workbook_profiles", []):
        for worksheet in workbook.get("worksheet_profiles", []):
            for region in worksheet.get("data_regions", []):
                for field in region.get("column_profiles", []):
                    field_id = field.get("field_id")
                    if not field_id:
                        continue
                    context = {
                        **field,
                        "source_id": workbook["source_id"],
                        "worksheet_name": worksheet["worksheet_name"],
                        "region_id": region["region_id"],
                    }
                    if field_id in result and result[field_id] != context:
                        raise ValueError(f"Profile contains a duplicate stable source field ID: {field_id}")
                    result[field_id] = context
    return result


def parse_output_record_id(value: Any) -> dict[str, Any]:
    try:
        parsed = json.loads(str(value))
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def lineage_source_rows(values: Iterable[Any]) -> set[SourceRowIdentity]:
    """Recover valid physical source-row identities from output record IDs."""
    rows: set[SourceRowIdentity] = set()
    for value in values:
        payload = parse_output_record_id(value)
        try:
            rows.add(source_row_identity(
                str(payload["source_id"]),
                str(payload["worksheet_name"]),
                str(payload["region_id"]),
                int(payload["physical_row"]),
            ))
        except (KeyError, TypeError, ValueError):
            continue
    return rows


__all__ = [
    "SourceRowIdentity",
    "lineage_source_rows",
    "output_record_id",
    "parse_output_record_id",
    "profile_field_index",
    "source_field_id",
    "source_row_identity",
    "source_row_payload",
]
