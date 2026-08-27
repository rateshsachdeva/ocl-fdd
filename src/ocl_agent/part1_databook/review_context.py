"""Compact machine-readable review context for the AI host.

This file reduces repeated workbook inspection. All amounts are deterministic
aggregations of the shared OCL record model; the AI host only interprets them.
"""
from __future__ import annotations

import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from ocl_agent.part1_databook.input_contract import StandardizedPackage
from ocl_agent.part1_databook.judgments import normalize_label
from ocl_agent.part1_databook.semantic_handoff import SemanticHandoff
from ocl_agent.schemas import OCLJudgment, OCLRecord


def write_review_context(
    package: StandardizedPackage,
    handoff: SemanticHandoff,
    records: tuple[OCLRecord, ...],
    output_path: Path,
) -> Path:
    technical_groups = _technical_groups(records)
    review_items = [_technical_review_item(item) for item in technical_groups]
    economic_review_items = build_economic_review_items(records, technical_groups=technical_groups)
    ambiguous_group_count = sum(
        item["grouping_status"] == "AMBIGUOUS_BLANK_ENTITY"
        for item in economic_review_items
    )
    metadata = package.metadata_payload()
    payload = {
        "review_context_version": "1.1",
        "package_id": handoff.package_id,
        "dataset_metadata": [
            {
                "logical_dataset_id": item.get("logical_dataset_id"),
                "name": item.get("name"),
                "role": item.get("role"),
                "dataset_grain": item.get("dataset_grain"),
                "main_measures": item.get("main_measures", []),
                "key_dimensions": item.get("key_dimensions", []),
            }
            for item in metadata.get("logical_datasets", [])
        ],
        "unresolved_upstream_questions": metadata.get("unresolved_questions", []),
        "semantic_unresolved_matters": list(handoff.unresolved_matters),
        "technical_review_item_count": len(review_items),
        "economic_review_item_count": len(economic_review_items),
        "consolidated_technical_key_count": len(review_items) - len(economic_review_items),
        "ambiguous_group_count": ambiguous_group_count,
        "review_items": review_items,
        "economic_review_items": economic_review_items,
    }
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path


def build_economic_review_items(
    records: tuple[OCLRecord, ...],
    *,
    technical_groups: list[dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    """Group technical judgment keys at the safest existing review grain.

    A normalized source-code + source-label identity is consolidated only when
    it has at most one distinct nonblank entity. Multiple nonblank entities stay
    entity-specific, and any blank-entity representation remains visibly
    ambiguous instead of being attached to an arbitrary entity.
    """
    groups = technical_groups if technical_groups is not None else _technical_groups(records)
    by_identity: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for item in groups:
        by_identity[(str(item["normalized_code"]), str(item["normalized_label"]))].append(item)

    result: list[dict[str, object]] = []
    for identity in sorted(by_identity, key=lambda value: (value[1], value[0])):
        identity_groups = by_identity[identity]
        nonblank_entities: dict[str, list[dict[str, object]]] = defaultdict(list)
        blank_entity_groups: list[dict[str, object]] = []
        for item in identity_groups:
            normalized_entity = str(item["normalized_entity"])
            if normalized_entity:
                nonblank_entities[normalized_entity].append(item)
            else:
                blank_entity_groups.append(item)

        if len(nonblank_entities) <= 1:
            result.append(
                _economic_review_item(
                    identity_groups,
                    recommended_config_entity=None,
                    grouping_status=(
                        "CONSOLIDATED_REPRESENTATIONS"
                        if len(identity_groups) > 1
                        else "SINGLE_TECHNICAL_KEY"
                    ),
                    grouping_reason=(
                        "Blank-entity and the sole nonblank-entity technical representations "
                        "share one normalized source code and source label; the existing "
                        "blank-entity code+label judgment grain safely resolves both."
                        if len(identity_groups) > 1
                        else "Only one technical judgment key exists for this normalized source code and source label."
                    ),
                )
            )
            continue

        for normalized_entity in sorted(nonblank_entities):
            entity_groups = nonblank_entities[normalized_entity]
            result.append(
                _economic_review_item(
                    entity_groups,
                    recommended_config_entity=str(entity_groups[0]["entity"]),
                    grouping_status="ENTITY_SPECIFIC",
                    grouping_reason=(
                        "Multiple distinct nonblank entities use this normalized source code and source label, "
                        "so this economic review item remains entity-specific."
                    ),
                )
            )
        if blank_entity_groups:
            result.append(
                _economic_review_item(
                    blank_entity_groups,
                    recommended_config_entity=None,
                    grouping_status="AMBIGUOUS_BLANK_ENTITY",
                    grouping_reason=(
                        "Blank-entity technical representations share this source code and label with multiple "
                        "nonblank entities and cannot be safely assigned to one of them."
                    ),
                    candidate_nonblank_entities=sorted(
                        str(items[0]["entity"])
                        for items in nonblank_entities.values()
                    ),
                )
            )

    return sorted(
        result,
        key=lambda item: (
            normalize_label(str(item["source_label"])),
            normalize_label(str(item.get("source_code") or "")),
            normalize_label(str(item.get("recommended_config_entity") or "")),
            str(item["grouping_status"]),
        ),
    )


def _technical_groups(records: tuple[OCLRecord, ...]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str], dict[str, object]] = {}
    for row in records:
        code = _text(row.dimensions.get("source_code")) or ""
        entity = _text(row.dimensions.get("entity")) or ""
        key = (normalize_label(row.source_label), normalize_label(code), normalize_label(entity))
        item = grouped.setdefault(
            key,
            {
                "normalized_label": key[0],
                "normalized_code": key[1],
                "normalized_entity": key[2],
                "source_label": row.source_label,
                "source_code": code or None,
                "entity": entity or None,
                "judgments": {},
                "representations": {},
            },
        )
        judgment = _judgment_payload(row.judgment)
        judgment_key = json.dumps(judgment, sort_keys=True, ensure_ascii=False)
        item["judgments"][judgment_key] = judgment

        dataset = _text(row.dimensions.get("dataset_file")) or ""
        usage = _text(row.dimensions.get("record_usage")) or ""
        representation_key = (dataset, usage)
        representation = item["representations"].setdefault(
            representation_key,
            {
                "dataset_file": dataset or None,
                "record_usage": usage or None,
                "period_amounts": {},
                "sample_source_record_ids": [],
            },
        )
        period_amounts = representation["period_amounts"]
        current = Decimal(str(period_amounts.get(row.period, "0")))
        period_amounts[row.period] = str(current + row.amount)
        sample_ids = representation["sample_source_record_ids"]
        if len(sample_ids) < 3 and row.source.source_record_id not in sample_ids:
            sample_ids.append(row.source.source_record_id)

    return [
        grouped[key]
        for key in sorted(grouped, key=lambda value: (value[0], value[1], value[2]))
    ]


def _technical_review_item(item: dict[str, object]) -> dict[str, object]:
    period_amounts: dict[str, str] = {}
    datasets = set()
    usages = set()
    sample_ids: list[str] = []
    for representation in _sorted_representations(item):
        if representation["dataset_file"]:
            datasets.add(representation["dataset_file"])
        if representation["record_usage"]:
            usages.add(representation["record_usage"])
        for period, amount in representation["period_amounts"].items():
            current = Decimal(period_amounts.get(period, "0"))
            period_amounts[period] = str(current + Decimal(amount))
        for source_record_id in representation["sample_source_record_ids"]:
            if len(sample_ids) < 3 and source_record_id not in sample_ids:
                sample_ids.append(source_record_id)
    judgments = list(item["judgments"].values())
    return {
        "source_label": item["source_label"],
        "source_code": item["source_code"],
        "entity": item["entity"],
        "period_amounts": dict(sorted(period_amounts.items())),
        "datasets": sorted(datasets),
        "record_usages": sorted(usages),
        "sample_source_record_ids": sample_ids,
        "judgment": judgments[0],
    }


def _economic_review_item(
    groups: list[dict[str, object]],
    *,
    recommended_config_entity: str | None,
    grouping_status: str,
    grouping_reason: str,
    candidate_nonblank_entities: list[str] | None = None,
) -> dict[str, object]:
    exemplar = groups[0]
    technical_keys = [
        {
            "source_label": item["source_label"],
            "source_code": item["source_code"],
            "entity": item["entity"],
        }
        for item in groups
    ]
    representations = []
    datasets = set()
    usages = set()
    represented_entities = set()
    judgments: dict[str, dict[str, object]] = {}
    for item in groups:
        if item["entity"]:
            represented_entities.add(str(item["entity"]))
        for judgment_key, judgment in item["judgments"].items():
            judgments[str(judgment_key)] = judgment
        for representation in _sorted_representations(item):
            dataset = representation["dataset_file"]
            usage = representation["record_usage"]
            if dataset:
                datasets.add(dataset)
            if usage:
                usages.add(usage)
            representations.append(
                {
                    "source_label": item["source_label"],
                    "source_code": item["source_code"],
                    "entity": item["entity"],
                    "dataset_file": dataset,
                    "record_usage": usage,
                    "period_amounts": dict(sorted(representation["period_amounts"].items())),
                    "sample_source_record_ids": list(representation["sample_source_record_ids"]),
                }
            )
    unique_judgments = list(judgments.values())
    current_judgment = unique_judgments[0] if len(unique_judgments) == 1 else None
    return {
        "source_label": exemplar["source_label"],
        "source_code": exemplar["source_code"],
        "recommended_config_entity": recommended_config_entity,
        "represented_entities": sorted(represented_entities, key=normalize_label),
        "represented_datasets": sorted(datasets, key=normalize_label),
        "represented_record_usages": sorted(usages, key=normalize_label),
        "technical_key_count": len(technical_keys),
        "technical_keys": technical_keys,
        "representations": representations,
        "period_amounts": [
            {
                "dataset_file": item["dataset_file"],
                "record_usage": item["record_usage"],
                "entity": item["entity"],
                "period_amounts": item["period_amounts"],
            }
            for item in representations
        ],
        "current_judgment": current_judgment,
        "judgment_consistency": "CONSISTENT" if current_judgment is not None else "CONFLICTING",
        "grouping_status": grouping_status,
        "grouping_reason": grouping_reason,
        **(
            {"candidate_nonblank_entities": candidate_nonblank_entities}
            if candidate_nonblank_entities
            else {}
        ),
    }


def _sorted_representations(item: dict[str, object]) -> list[dict[str, object]]:
    representations = item["representations"]
    return [
        representations[key]
        for key in sorted(
            representations,
            key=lambda value: (normalize_label(value[0]), normalize_label(value[1])),
        )
    ]


def _judgment_payload(judgment: OCLJudgment) -> dict[str, object]:
    return {
        "scope": judgment.scope.value,
        "category": judgment.category,
        "parent_category": judgment.parent_category,
        "management_view": judgment.management_view,
        "fdd_view": judgment.fdd_view,
        "normality": judgment.normality,
        "review_status": judgment.review_status.value,
        "reason": judgment.reason,
    }


def _text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
