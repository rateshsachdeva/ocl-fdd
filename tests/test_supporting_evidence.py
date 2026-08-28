import csv
import json
from decimal import Decimal
from pathlib import Path

from ocl_agent.part1_databook.input_contract import discover_standardized_package
from ocl_agent.part1_databook.semantic_handoff import DatasetBinding, DatasetUsage, FieldBinding, SemanticHandoff
from ocl_agent.part2_analysis.ai_interpretation import write_analysis_request
from ocl_agent.part2_analysis.supporting_evidence import load_supporting_evidence_tables
from ocl_agent.schemas import AnalysisResult, AnalysisTable


def _write_csv(path: Path, headers, rows) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def test_supporting_evidence_reaches_ai_request_without_entering_foundation_totals(tmp_path: Path):
    package_root = tmp_path / "package"
    package_root.mkdir()
    _write_csv(package_root / "ocl_annual.csv", ["Source_Record_ID", "Period", "Source_Label", "Amount"], [["A1", "FY25", "Accrual", 500]])
    _write_csv(package_root / "support.csv", ["Source_Record_ID", "Period", "Amount", "Evidence_Type"], [["S1", "2025-12", 25, "Settlement"], ["S2", "2025-12", 75, "Invoice"]])
    (package_root / "execution_manifest.json").write_text(json.dumps({"execution_id": "SUP-1", "final_execution_status": "COMPLETED", "outputs_created": ["ocl_annual.csv", "support.csv"]}), encoding="utf-8")
    package = discover_standardized_package(package_root)
    handoff = SemanticHandoff(
        "1.0",
        "CONFIRMED",
        "SUP-1",
        (
            DatasetBinding("ocl_annual.csv", (DatasetUsage.OCL_RECORDS,), FieldBinding("Source_Record_ID", "Period", "Amount", "Source_Label")),
            DatasetBinding("support.csv", (DatasetUsage.SUPPORTING_EVIDENCE,), FieldBinding("Source_Record_ID", "Period", "Amount"), ("Evidence_Type",), "Supporting only"),
        ),
    )

    supporting = load_supporting_evidence_tables(package, handoff)
    foundation = AnalysisTable("annual_balance", "Foundation", ("Period", "Amount"), (("FY25", Decimal("500")),))
    request = write_analysis_request(AnalysisResult((), (foundation, *supporting)), tmp_path / "analysis_evidence.json", required_artifact=tmp_path / "analysis_interpretation.json", instruction_path=tmp_path / "instruction.md")
    payload = json.loads(request.read_text(encoding="utf-8"))
    tables = {item["key"]: item for item in payload["evidence"]["analysis_tables"]}

    assert tables["annual_balance"]["rows"] == [["FY25", "500"]]
    assert tables["supporting_evidence_summary"]["rows"][0][0:4] == ["support.csv", 2, 2, "FULL"]
    assert tables["supporting_evidence_support_csv"]["rows"][0][1:] == ["S1", "2025-12", "25", "Settlement"]
