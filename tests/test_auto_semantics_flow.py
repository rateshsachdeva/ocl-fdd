import csv
import json
from pathlib import Path

from ocl_agent.auto_semantics import ensure_semantic_handoff
from ocl_agent.part1_databook.run import run_part1


def _write_csv(path: Path, headers, rows) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def _build_canonical_package(root: Path) -> Path:
    root.mkdir(parents=True)
    headers = ["Source_Record_ID", "Period", "Source_Label", "Source_Code", "Entity", "Amount"]
    rows = [
        ["SRC-1", "FY24", "Bonus accrual", "2100", "Entity A", "300000"],
        ["SRC-2", "FY25", "Bonus accrual", "2100", "Entity A", "450000"],
    ]
    _write_csv(root / "ocl_annual.csv", headers, rows)
    _write_csv(root / "revenue_context.csv", ["Period", "Revenue"], [["FY24", "5000000"], ["FY25", "5600000"]])
    outputs = ["ocl_annual.csv", "revenue_context.csv"]
    (root / "execution_manifest.json").write_text(
        json.dumps({"execution_id": "AUTO-SEM-001", "final_execution_status": "COMPLETED", "outputs_created": outputs}),
        encoding="utf-8",
    )
    (root / "databook_metadata.json").write_text(
        json.dumps({"workflow_run_id": "AUTO-SEM-001"}),
        encoding="utf-8",
    )
    return root


def _build_reviewed_config(root: Path) -> Path:
    root.mkdir(parents=True)
    _write_csv(
        root / "judgment_scope.csv",
        ["source_label", "source_code", "entity", "scope", "review_status", "reason"],
        [["Bonus accrual", "2100", "Entity A", "IN_SCOPE", "REVIEWED", "Operating accrual"]],
    )
    _write_csv(
        root / "mapping.csv",
        ["source_label", "source_code", "entity", "category", "parent_category", "review_status", "reason"],
        [["Bonus accrual", "2100", "Entity A", "Bonus accrual", "Employee accruals", "REVIEWED", ""]],
    )
    _write_csv(
        root / "judgment_wc_debt.csv",
        ["source_label", "source_code", "entity", "management_view", "fdd_view", "normality", "review_status", "reason"],
        [["Bonus accrual", "2100", "Entity A", "working_capital", "working_capital", "normal", "REVIEWED", ""]],
    )
    return root


def test_canonical_publication_skips_second_ai_semantic_checkpoint(tmp_path: Path):
    package = _build_canonical_package(tmp_path / "package")
    config = _build_reviewed_config(tmp_path / "config")
    output = tmp_path / "output"

    result = run_part1(package, config, output)

    assert result.state == "DATABOOK_READY"
    assert result.handoff is not None
    payload = json.loads((config / "semantic_handoff.json").read_text(encoding="utf-8"))
    assert payload["status"] == "CONFIRMED"
    assert payload["confirmed_by"] == "INTEGRATED_CANONICAL_CONTRACT"
    annual = next(item for item in payload["datasets"] if item["file"] == "ocl_annual.csv")
    assert annual["usages"] == ["OCL_RECORDS"]
    assert "currency" not in annual["fields"]
    revenue = next(item for item in payload["datasets"] if item["file"] == "revenue_context.csv")
    assert revenue["fields"] == {"period": "Period", "amount": "Revenue"}


def test_noncanonical_publication_keeps_explicit_semantic_review_fallback(tmp_path: Path):
    package = tmp_path / "package"
    package.mkdir()
    _write_csv(
        package / "custom_output.csv",
        ["Source_Record_ID", "Period", "Source_Label", "Amount"],
        [["SRC-1", "FY25", "Something", "100"]],
    )
    (package / "execution_manifest.json").write_text(
        json.dumps({"execution_id": "CUSTOM-001", "final_execution_status": "COMPLETED", "outputs_created": ["custom_output.csv"]}),
        encoding="utf-8",
    )
    config = tmp_path / "config"

    assert ensure_semantic_handoff(package, config) is None
    assert not (config / "semantic_handoff.json").exists()
