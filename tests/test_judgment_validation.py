from decimal import Decimal
from ocl_agent.part1_databook.judgment_validation import validate_judgment_completion
from ocl_agent.schemas import OCLJudgment, OCLRecord, ReviewStatus, Scope, SourceReference


def record(judgment):
    return OCLRecord(SourceReference('x'),'FY25',Decimal('1'),judgment.source_label,judgment,{'source_code':'100','entity':'A'})


def test_in_scope_requires_complete_reviewed_treatment():
    issues = validate_judgment_completion((record(OCLJudgment('A',Scope.IN_SCOPE,review_status=ReviewStatus.REVIEWED)),))
    assert {item.issue_type for item in issues} == {'MAPPING_MISSING','MANAGEMENT_VIEW_MISSING','FDD_VIEW_MISSING','NORMALITY_MISSING'}


def test_excluded_scope_does_not_require_category_or_wc_tags():
    assert validate_judgment_completion((record(OCLJudgment('A',Scope.TRADE_PAYABLE,review_status=ReviewStatus.REVIEWED)),)) == ()


def test_complete_in_scope_passes():
    judgment = OCLJudgment('A',Scope.IN_SCOPE,'Payroll','Employee accruals','working_capital','working_capital','normal',ReviewStatus.REVIEWED)
    assert validate_judgment_completion((record(judgment),)) == ()
