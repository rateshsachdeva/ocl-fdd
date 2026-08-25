import json
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook, load_workbook

from ocl_agent.part2_analysis.ai_interpretation import (
    load_analysis_interpretation,
    write_analysis_request,
)
from ocl_agent.part2_analysis.ai_render import apply_partner_interpretation
from ocl_agent.schemas import AnalysisResult, AnalysisTable


def _analysis() -> AnalysisResult:
    return AnalysisResult(
        findings=(),
        tables=(
            AnalysisTable(
                "movement_review",
                "Latest annual movement review",
                ("Category", "FY24", "FY25", "Movement", "Movement %", "Databook Review", "Finding Eligible"),
                (("Bonus accrual", Decimal("300000"), Decimal("360000"), Decimal("60000"), 20.0, "REVIEW", ""),),
            ),
        ),
        annual_periods=("FY24", "FY25"),
        monthly_periods=(),
        latest_annual_period="FY25",
    )


def test_ai_partner_interpretation_can_use_table_evidence_without_deterministic_headline(tmp_path: Path):
    analysis = _analysis()
    request_path = tmp_path / "analysis_evidence.json"
    interpretation_path = tmp_path / "analysis_interpretation.json"
    instruction_path = tmp_path / "FDD_PARTNER_ANALYSIS.md"
    instruction_path.write_text("test", encoding="utf-8")
    write_analysis_request(
        analysis,
        request_path,
        required_artifact=interpretation_path,
        instruction_path=instruction_path,
    )
    request = json.loads(request_path.read_text(encoding="utf-8"))
    assert "table:movement_review:0" in request["valid_evidence_refs"]

    interpretation = {
        "status": "COMPLETED",
        "evidence_hash": request["evidence_hash"],
        "overall_assessment": "The available annual data shows no headline movement, although one category warrants follow-up for closing-balance representativeness.",
        "deal_issues": [],
        "key_findings": [
            {
                "id": "KF_01",
                "area": "Working capital & balance validity",
                "metric": "Annual movement",
                "period_item": "FY24-FY25 / Bonus accrual",
                "so_what": "The movement is below the headline threshold but should be understood before concluding on the normal closing level.",
                "evidence": "Bonus accrual increased from 300,000 to 360,000, a 20.0% movement.",
                "materiality": "NOTABLE",
                "ask_management": "Please explain the operational driver of the increase and expected settlement timing.",
                "linked_finding_id": None,
                "evidence_refs": ["table:movement_review:0"],
            }
        ],
        "management_questions": [
            {
                "id": "Q_01",
                "theme": "Working capital & balance validity",
                "question": "Please explain the operational driver of the increase in bonus accrual and expected settlement timing.",
                "evidence": "Bonus accrual increased by 20.0% between FY24 and FY25.",
                "priority": "MEDIUM",
                "linked_finding_id": None,
                "evidence_refs": ["table:movement_review:0"],
            }
        ],
    }
    interpretation_path.write_text(json.dumps(interpretation), encoding="utf-8")
    loaded = load_analysis_interpretation(interpretation_path, request_path)
    assert loaded["key_findings"][0]["materiality"] == "NOTABLE"


def test_ai_partner_render_never_leaves_deal_issues_key_findings_or_qanda_blank(tmp_path: Path):
    analysis = _analysis()
    workbook_path = tmp_path / "OCL_Databook.xlsx"
    wb = Workbook()
    wb.active.title = "Flat File"
    wb.save(workbook_path)

    interpretation = {
        "overall_assessment": "No material deal issue was identified from the available evidence.",
        "deal_issues": [],
        "key_findings": [
            {
                "id": "KF_01",
                "area": "Overall assessment",
                "metric": "Material deal issues",
                "period_item": "FY24-FY25",
                "so_what": "No material OCL deal issue was identified from the supplied evidence.",
                "evidence": "The available evidence did not support a headline OCL issue.",
                "materiality": "NO_MATERIAL_ISSUE",
                "ask_management": "",
                "linked_finding_id": None,
                "evidence_refs": ["table:movement_review:0"],
            }
        ],
        "management_questions": [],
    }
    questions = apply_partner_interpretation(workbook_path, analysis, interpretation)
    assert questions == ()

    wb = load_workbook(workbook_path, read_only=False)
    assert wb["Deal Issues"]["A4"].value == "No material deal issue identified from the available evidence"
    assert wb["Deal Issues"]["A5"].value
    assert wb["Key Findings"]["B8"].value == "KF_01"
    assert "No material management question" in wb["Q&A"]["D8"].value
    wb.close()
