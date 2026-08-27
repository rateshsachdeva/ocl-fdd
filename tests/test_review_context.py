import json
from decimal import Decimal
from pathlib import Path

from ocl_agent.part1_databook.input_contract import StandardizedPackage
from ocl_agent.part1_databook.judgments import JudgmentStore, judgment_key
from ocl_agent.part1_databook.review_context import (
    build_economic_review_items,
    write_review_context,
)
from ocl_agent.part1_databook.semantic_handoff import SemanticHandoff
from ocl_agent.schemas import OCLJudgment, OCLRecord, ReviewStatus, Scope, SourceReference


def _judgment(label: str) -> OCLJudgment:
    return OCLJudgment(
        label,
        Scope.IN_SCOPE,
        "Bonus",
        "Employee",
        "working_capital",
        "working_capital",
        "normal",
        ReviewStatus.REVIEWED,
        "Reviewed",
    )


def _record(
    source_record_id: str,
    *,
    label: str = "Bonus",
    code: str = "2100",
    entity: str | None = None,
    dataset: str = "annual.csv",
    usage: str = "OCL_RECORDS",
    period: str = "FY25",
    amount: str = "10",
) -> OCLRecord:
    return OCLRecord(
        SourceReference(source_record_id),
        period,
        Decimal(amount),
        label,
        _judgment(label),
        {
            "source_code": code,
            "entity": entity,
            "dataset_file": dataset,
            "record_usage": usage,
        },
    )


def _package(tmp_path: Path) -> StandardizedPackage:
    metadata = tmp_path / "databook_metadata.json"
    metadata.write_text(
        json.dumps(
            {
                "logical_datasets": [
                    {
                        "logical_dataset_id": "d1",
                        "name": "TB",
                        "role": "PRIMARY_DATA",
                        "dataset_grain": "Account x period",
                    }
                ]
            }
        )
    )
    return StandardizedPackage(tmp_path, (), metadata, None, None, None)


def test_blank_and_single_nonblank_entity_consolidate_but_technical_items_remain(tmp_path: Path):
    rows = (
        _record("annual", entity="Redwood", amount="100"),
        _record(
            "monthly",
            entity=None,
            dataset="monthly.csv",
            usage="MONTHLY_RECORDS",
            period="Dec-25",
            amount="90",
        ),
    )
    output = write_review_context(
        _package(tmp_path),
        SemanticHandoff("1.0", "CONFIRMED", "P", ()),
        rows,
        tmp_path / "context.json",
    )
    payload = json.loads(output.read_text())

    assert payload["technical_review_item_count"] == 2
    assert payload["economic_review_item_count"] == 1
    assert payload["consolidated_technical_key_count"] == 1
    assert payload["ambiguous_group_count"] == 0
    assert len(payload["review_items"]) == 2
    item = payload["economic_review_items"][0]
    assert item["recommended_config_entity"] is None
    assert item["represented_entities"] == ["Redwood"]
    assert item["represented_datasets"] == ["annual.csv", "monthly.csv"]
    assert item["represented_record_usages"] == ["MONTHLY_RECORDS", "OCL_RECORDS"]
    assert item["technical_key_count"] == 2
    assert len(item["technical_keys"]) == 2
    assert len(item["representations"]) == 2
    assert payload["dataset_metadata"][0]["dataset_grain"] == "Account x period"


def test_same_nonblank_entity_across_datasets_is_one_economic_item():
    rows = (
        _record("annual", entity="A", amount="100"),
        _record(
            "monthly",
            entity="A",
            dataset="monthly.csv",
            usage="MONTHLY_RECORDS",
            period="Dec-25",
            amount="90",
        ),
    )

    item = build_economic_review_items(rows)[0]

    assert item["technical_key_count"] == 1
    assert len(item["representations"]) == 2
    assert item["recommended_config_entity"] is None


def test_same_label_with_different_source_codes_stays_separate():
    rows = (
        _record("one", code="2100"),
        _record("two", code="2200"),
    )

    items = build_economic_review_items(rows)

    assert len(items) == 2
    assert {item["source_code"] for item in items} == {"2100", "2200"}


def test_multiple_nonblank_entities_stay_separate_and_blank_entity_is_ambiguous():
    rows = (
        _record("a", entity="Entity A"),
        _record("b", entity="Entity B"),
        _record("blank", entity=None),
    )

    items = build_economic_review_items(rows)

    assert len(items) == 3
    assert {item["recommended_config_entity"] for item in items} == {None, "Entity A", "Entity B"}
    assert all(len(item["represented_entities"]) <= 1 for item in items)
    ambiguous = next(item for item in items if item["grouping_status"] == "AMBIGUOUS_BLANK_ENTITY")
    assert ambiguous["technical_keys"] == [
        {"source_label": "Bonus", "source_code": "2100", "entity": None}
    ]
    assert ambiguous["candidate_nonblank_entities"] == ["Entity A", "Entity B"]


def test_annual_and_monthly_period_amounts_are_kept_in_separate_representations():
    rows = (
        _record("annual", entity="A", period="FY25", amount="100"),
        _record(
            "monthly-1",
            entity=None,
            dataset="monthly.csv",
            usage="MONTHLY_RECORDS",
            period="Dec-25",
            amount="40",
        ),
        _record(
            "monthly-2",
            entity=None,
            dataset="monthly.csv",
            usage="MONTHLY_RECORDS",
            period="Dec-25",
            amount="50",
        ),
    )

    item = build_economic_review_items(rows)[0]
    evidence = {
        (entry["dataset_file"], entry["record_usage"]): entry["period_amounts"]
        for entry in item["period_amounts"]
    }

    assert evidence == {
        ("annual.csv", "OCL_RECORDS"): {"FY25": "100"},
        ("monthly.csv", "MONTHLY_RECORDS"): {"Dec-25": "90"},
    }


def test_existing_blank_entity_code_and_label_fallback_still_resolves_both_entities():
    judgment = _judgment("Bonus")
    store = JudgmentStore({judgment_key("Bonus", "2100", None): judgment})

    assert store.get("Bonus", "2100", "Redwood") is judgment
    assert store.get("Bonus", "2100", None) is judgment
