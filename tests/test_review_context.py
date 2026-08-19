import json
from decimal import Decimal
from pathlib import Path
from ocl_agent.part1_databook.input_contract import StandardizedPackage
from ocl_agent.part1_databook.review_context import write_review_context
from ocl_agent.part1_databook.semantic_handoff import SemanticHandoff
from ocl_agent.schemas import OCLJudgment, OCLRecord, ReviewStatus, Scope, SourceReference


def test_review_context_is_compact_and_aggregated(tmp_path: Path):
    metadata = tmp_path/'databook_metadata.json'
    metadata.write_text(json.dumps({'logical_datasets':[{'logical_dataset_id':'d1','name':'TB','role':'PRIMARY_DATA','dataset_grain':'Account x period'}]}))
    package = StandardizedPackage(tmp_path,(),metadata,None,None,None)
    judgment = OCLJudgment('Bonus',Scope.IN_SCOPE,'Bonus','Employee','working_capital','working_capital','normal',ReviewStatus.REVIEWED)
    rows = (OCLRecord(SourceReference('r1'),'FY25',Decimal('4'),'Bonus',judgment,{'source_code':'2100','entity':'A','dataset_file':'x.csv'}), OCLRecord(SourceReference('r2'),'FY25',Decimal('6'),'Bonus',judgment,{'source_code':'2100','entity':'A','dataset_file':'x.csv'}))
    output = write_review_context(package,SemanticHandoff('1.0','CONFIRMED','P',()),rows,tmp_path/'context.json')
    payload = json.loads(output.read_text())
    assert len(payload['review_items']) == 1
    assert payload['review_items'][0]['period_amounts']['FY25'] == '10'
    assert payload['dataset_metadata'][0]['dataset_grain'] == 'Account x period'
