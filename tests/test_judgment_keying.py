from pathlib import Path
import pytest
from ocl_agent.part1_databook.judgments import JudgmentError, load_judgments
from ocl_agent.schemas import Scope


def test_code_specific_judgment_wins_over_generic(tmp_path: Path):
    (tmp_path/'judgment_scope.csv').write_text('source_label,source_code,entity,scope,review_status,reason\nAccrual,,,OUT_OF_SCOPE,REVIEWED,generic\nAccrual,100,,IN_SCOPE,REVIEWED,specific\n')
    store = load_judgments(tmp_path)
    assert store.get('Accrual','100').scope == Scope.IN_SCOPE
    assert store.get('Accrual','999').scope == Scope.OUT_OF_SCOPE


def test_duplicate_key_is_rejected(tmp_path: Path):
    (tmp_path/'mapping.csv').write_text('source_label,source_code,entity,category,parent_category,review_status,reason\nA,1,,X,,REVIEWED,\nA,1,,Y,,REVIEWED,\n')
    with pytest.raises(JudgmentError, match='Duplicate judgment key'):
        load_judgments(tmp_path)


def test_invalid_wc_domain_is_rejected(tmp_path: Path):
    (tmp_path/'judgment_wc_debt.csv').write_text('source_label,source_code,entity,management_view,fdd_view,normality,review_status,reason\nA,,,,sometimes,,REVIEWED,\n')
    with pytest.raises(JudgmentError, match='Invalid fdd_view'):
        load_judgments(tmp_path)
