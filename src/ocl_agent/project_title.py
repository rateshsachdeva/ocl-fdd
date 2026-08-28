"""Source-driven workbook identity with a neutral, reusable fallback."""
from __future__ import annotations

import re
from typing import Any

DEFAULT_PROJECT_TITLE = "Other Current Liabilities"
LEGACY_GENERIC_TITLE = "TargetCo - Other Current Liabilities"


def resolve_project_title(*, package=None, workbook=None) -> str:
    """Resolve an explicit engagement/company label without parsing raw files."""
    metadata = package.metadata_payload() if package is not None else {}
    explicit_title = _text(metadata.get("workbook_title"))
    if explicit_title:
        return explicit_title
    for key in ("engagement_label", "engagement_name", "company_name", "target_name"):
        label = _text(metadata.get(key))
        if label:
            return _with_subject(label)

    entities = {
        value
        for dataset in metadata.get("logical_datasets", [])
        if isinstance(dataset, dict)
        for item in dataset.get("metadata", [])
        if isinstance(item, dict)
        and str(item.get("metadata_type") or "").upper() in {"ENTITY", "ENGAGEMENT_LABEL", "COMPANY_NAME", "TARGET_NAME"}
        and str(item.get("status") or "").upper() == "EVIDENCED"
        and (value := _text(item.get("value")))
    }
    entities.update(_explicit_readme_labels(metadata))
    if len(entities) == 1:
        return _with_subject(next(iter(entities)))

    if workbook is not None:
        for name in (
            "Balance by Category", "Monthly Balance", "Roll-forward",
            "Analysis Summary", "Deal Issues", "Key Findings", "Q&A",
        ):
            if name not in workbook.sheetnames:
                continue
            existing = _text(workbook[name]["A1"].value)
            if existing and existing != LEGACY_GENERIC_TITLE and "other current liabilities" in existing.casefold():
                return existing
    return DEFAULT_PROJECT_TITLE


def _with_subject(label: str) -> str:
    if "other current liabilities" in label.casefold():
        return label
    return f"{label} - {DEFAULT_PROJECT_TITLE}"


def _explicit_readme_labels(metadata: dict[str, Any]) -> set[str]:
    """Recover only labels explicitly named by evidenced workbook-context metadata."""
    labels: set[str] = set()
    for dataset in metadata.get("logical_datasets", []):
        if not isinstance(dataset, dict):
            continue
        for item in dataset.get("metadata", []):
            if not isinstance(item, dict):
                continue
            if str(item.get("status") or "").upper() != "EVIDENCED":
                continue
            source_context = str(item.get("source_context") or "").casefold()
            if "read me" not in source_context and "readme" not in source_context:
                continue
            evidence = str(item.get("evidence") or "").strip()
            match = re.search(r"\bidentifies\s+(.+?)(?:,|\s+-\s+)", evidence, flags=re.IGNORECASE)
            if match and (label := _text(match.group(1))):
                labels.add(label)
    return labels


def _text(value: Any) -> str | None:
    if not isinstance(value, (str, int, float)):
        return None
    text = str(value).strip()
    return text or None
