from decimal import Decimal

from ocl_agent.part2_analysis.diagnostics import diagnostic_analysis, diagnostic_findings
from ocl_agent.part3_qanda.engine import build_questions
from ocl_agent.schemas import AnalysisResult, OCLJudgment, OCLRecord, ReviewStatus, Scope, SourceReference


def _record(label, category, period, amount, usage="OCL_RECORDS", source_code=None, entity=None, item_identifier=None):
    return OCLRecord(SourceReference(f"{label}:{period}"), period, Decimal(str(amount)), label, OCLJudgment(label, Scope.IN_SCOPE, category, review_status=ReviewStatus.REVIEWED), {"record_usage": usage, "source_code": source_code, "entity": entity, "item_identifier": item_identifier})


def test_material_new_cliff_and_stale_patterns_create_focused_questions():
    records = [
        _record("New accrual", "Other", "FY24", 0, source_code="NEW"),
        _record("New accrual", "Other", "FY25", 150000, source_code="NEW"),
        _record("Settled accrual", "Other", "FY24", 180000, source_code="SETTLED"),
        _record("Settled accrual", "Other", "FY25", 0, source_code="SETTLED"),
    ]
    for period in ("2025-09", "2025-10", "2025-11", "2025-12"):
        records.append(_record("Old accrual", "Other", period, 125000, "MONTHLY_RECORDS", "OLD"))
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


def test_item_monthly_signals_use_source_code_and_remain_evidence_not_conclusions():
    records = []
    monthly = {
        "NEW": [0, 0, 0, 160000],
        "NIL": [180000, 180000, 180000, 0],
        "STALE": [125000, 125000, 125000, 125000],
        "BUILD": [20000, 20000, 20000, 220000],
        "CONC": [500000, 500000, 500000, 500000],
    }
    periods = ("2025-09", "2025-10", "2025-11", "2025-12")
    for code, values in monthly.items():
        for period, value in zip(periods, values):
            records.append(_record("Shared display label", "Other", period, value, "MONTHLY_RECORDS", code, "Entity A"))

    findings, tables = diagnostic_analysis(records)
    kinds = {item.finding_type for item in findings}
    table = next(item for item in tables if item.key == "item_monthly_signals")
    codes = {row[1] for row in table.rows}

    assert {"NEW_ITEM", "CLIFF", "STALE_BALANCE", "ITEM_UNUSUAL_BUILD", "ITEM_CONCENTRATION"} <= kinds
    assert {"NEW", "NIL", "STALE", "BUILD", "CONC"} <= codes
    assert all(item.metrics.get("evidence_status") == "SIGNAL_NOT_CONCLUSION" for item in findings)
    assert len({item.finding_id for item in findings}) == len(findings)


def test_explicit_stable_item_identifier_role_supports_item_analysis_without_source_code():
    records = [
        _record("Invoice accrual", "Other", "2025-11", 0, "MONTHLY_RECORDS", item_identifier="INV-7"),
        _record("Invoice accrual", "Other", "2025-12", 175000, "MONTHLY_RECORDS", item_identifier="INV-7"),
    ]

    findings, tables = diagnostic_analysis(records)

    assert {item.finding_type for item in findings} == {"NEW_ITEM", "ITEM_CONCENTRATION"}
    assert all(item.metrics["identifier_basis"] == "ITEM_IDENTIFIER" for item in findings)
    assert all(item.metrics["item_identifier"] == "INV-7" for item in findings)
    assert tables[0].rows[0][0:2] == ("ITEM_IDENTIFIER", "INV-7")


def test_shared_descriptive_label_without_stable_identifier_does_not_create_synthetic_item():
    records = [
        _record("Shared description", "Other", "2025-11", 0, "MONTHLY_RECORDS"),
        _record("Shared description", "Other", "2025-12", 175000, "MONTHLY_RECORDS"),
        _record("Shared description", "Other", "2025-11", 125000, "MONTHLY_RECORDS"),
        _record("Shared description", "Other", "2025-12", 125000, "MONTHLY_RECORDS"),
    ]

    findings, tables = diagnostic_analysis(records)

    assert findings == ()
    assert tables == ()


def test_annual_item_signal_is_unsupported_without_stable_identifier():
    records = [
        _record("Description only", "Other", "FY24", 0),
        _record("Description only", "Other", "FY25", 175000),
    ]

    assert diagnostic_analysis(records) == ((), ())
