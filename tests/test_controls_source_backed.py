import csv
from decimal import Decimal
from ocl_agent.part1_databook.controls import build_core_controls
from ocl_agent.part1_databook.input_contract import discover_standardized_package
from ocl_agent.part1_databook.record_builder import RecordBuildResult
from ocl_agent.part1_databook.semantic_handoff import ControlBinding, DatasetBinding, DatasetUsage, FieldBinding, PeriodAlignment, SemanticHandoff
from ocl_agent.schemas import CheckStatus, OCLJudgment, OCLRecord, ReviewStatus, Scope, SourceReference


def _reviewed_record(period='FY25', amount='10', usage='OCL_RECORDS'):
    judgment = OCLJudgment('A',Scope.IN_SCOPE,'Cat',None,'working_capital','working_capital','normal',ReviewStatus.REVIEWED)
    return OCLRecord(SourceReference(period),period,Decimal(amount),'A',judgment,{'record_usage':usage})


def test_missing_optional_controls_are_not_applicable():
    row = _reviewed_record()
    handoff = SemanticHandoff('1.0','CONFIRMED','P',(DatasetBinding('x.csv',(DatasetUsage.OCL_RECORDS,),FieldBinding()),))
    controls = {c.control_id:c for c in build_core_controls((row,),RecordBuildResult((row,),(),{'x.csv':1}),handoff,())}
    assert controls['chk_listing_vs_tb'].status == CheckStatus.NOT_APPLICABLE
    assert controls['chk_monthly_to_annual'].status == CheckStatus.NOT_APPLICABLE


def test_monthly_to_annual_uses_explicit_alignment():
    annual = _reviewed_record('FY25','10','OCL_RECORDS')
    monthly = _reviewed_record('Dec-25','10','MONTHLY_RECORDS')
    handoff = SemanticHandoff('1.0','CONFIRMED','P',(DatasetBinding('a.csv',(DatasetUsage.OCL_RECORDS,),FieldBinding()),DatasetBinding('m.csv',(DatasetUsage.MONTHLY_RECORDS,),FieldBinding())),(),(PeriodAlignment('FY25','Dec-25'),))
    controls = {c.control_id:c for c in build_core_controls((annual,monthly),RecordBuildResult((annual,monthly),(),{'a.csv':1,'m.csv':1}),handoff,())}
    assert controls['chk_monthly_to_annual'].status == CheckStatus.PASS


def test_source_backed_tb_control_uses_exact_filter(tmp_path):
    with (tmp_path/'tb.csv').open('w',newline='') as handle:
        writer = csv.DictWriter(handle,fieldnames=['Period','Line','Amount']); writer.writeheader(); writer.writerow({'Period':'FY25','Line':'OCL control','Amount':'10'}); writer.writerow({'Period':'FY25','Line':'Other','Amount':'999'})
    (tmp_path/'execution_manifest.json').write_text('{"final_execution_status":"COMPLETED","outputs_created":["tb.csv"]}')
    package = discover_standardized_package(tmp_path)
    row = _reviewed_record()
    handoff = SemanticHandoff('1.0','CONFIRMED',tmp_path.name,(DatasetBinding('tb.csv',(DatasetUsage.OCL_RECORDS,DatasetUsage.TB_CONTROL),FieldBinding()),),(),(),(ControlBinding('chk_listing_vs_tb','tb.csv','Period','Amount',{'Line':('OCL control',)}),))
    controls = {c.control_id:c for c in build_core_controls((row,),RecordBuildResult((row,),(),{'tb.csv':1}),handoff,(),package)}
    assert controls['chk_listing_vs_tb'].status == CheckStatus.PASS
    assert controls['chk_listing_vs_tb'].expected == Decimal('10')


def test_tb_usage_without_exact_binding_requires_review(tmp_path):
    (tmp_path/'tb.csv').write_text('Period,Amount\nFY25,10\n')
    (tmp_path/'execution_manifest.json').write_text('{"final_execution_status":"COMPLETED","outputs_created":["tb.csv"]}')
    package = discover_standardized_package(tmp_path)
    row = _reviewed_record()
    handoff = SemanticHandoff('1.0','CONFIRMED',tmp_path.name,(DatasetBinding('tb.csv',(DatasetUsage.OCL_RECORDS,DatasetUsage.TB_CONTROL),FieldBinding()),))
    controls = {c.control_id:c for c in build_core_controls((row,),RecordBuildResult((row,),(),{'tb.csv':1}),handoff,(),package)}
    assert controls['chk_listing_vs_tb'].status == CheckStatus.REVIEW_REQUIRED
