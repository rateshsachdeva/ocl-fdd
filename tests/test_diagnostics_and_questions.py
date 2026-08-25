from decimal import Decimal

from ocl_agent.part2_analysis.diagnostics import diagnostic_findings
from ocl_agent.part3_qanda.engine import build_questions
from ocl_agent.schemas import AnalysisResult, OCLJudgment, OCLRecord, ReviewStatus, Scope, SourceReference


def _record(label, category, period, amount, usage="OCL_RECORDS"):
    return OCLRecord(SourceReference(f"{label}:{period}"), period, Decimal(str(amount)), label, OCLJudgment(label, Scope.IN_SCOPE, category, review_status=ReviewStatus.REVIEWED), {"record_usage": usage})


def test_material_new_cliff_and_stale_patterns_create_focused_questions():
    records = [
        _record("New accrual", "Other", "FY24", 0),
        _record("New accrual", "Other", "FY25", 150000),
        _record("Settled accrual", "Other", "FY24", 180000),
        _record("Settled accrual", "Other", "FY25", 0),
    ]
    for period in ("2025-09", "2025-10", "2025-11", "2025-12"):
        records.append(_record("Old accrual", "Other", period, 125000, "MONTHLY_RECORDS"))
    findings = diagnostic_findings(records)
    kinds = {item.finding_type for item in findings}
    assert {"NEW_ITEM", "CLIFF", "STALE_BALANCE"} <= kinds
    questions = build_questions(AnalysisResult(findings, ()))
    text = " ".join(item.question for item in questions).casefold()
    assert "gave rise to the new new accrual balance" in text
    assert "settled, released or reversed" in text
    assert "remains a valid outstanding obligation" in text
    forbidden = ("purchase-price", "management's assessment", "provide supporting invoices", "provide the accrual roll-forward")
    assert not any(phrase in text for phrase in forbidden)


def test_immaterial_diagnostic_patterns_do_not_create_findings_or_questions():
    records = [
        _record("Small new accrual", "Other", "FY24", 0),
        _record("Small new accrual", "Other", "FY25", 50000),
        _record("Small settled accrual", "Other", "FY24", 80000),
        _record("Small settled accrual", "Other", "FY25", 0),
    ]
    for period in ("2025-09", "2025-10", "2025-11", "2025-12"):
        records.append(_record("Small old accrual", "Other", period, 75000, "MONTHLY_RECORDS"))
    findings = diagnostic_findings(records)
    assert findings == ()
    assert build_questions(AnalysisResult(findings, ())) == ()
