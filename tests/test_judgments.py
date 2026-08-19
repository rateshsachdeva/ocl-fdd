from pathlib import Path

from ocl_agent.part1_databook.judgments import load_judgments
from ocl_agent.schemas import ReviewStatus, Scope


def test_unknown_label_is_visible_review_required(tmp_path: Path):
    store = load_judgments(tmp_path)
    judgment = store.get("Unseen accrual")
    assert judgment.scope == Scope.REVIEW_REQUIRED
    assert judgment.review_status == ReviewStatus.UNRESOLVED


def test_human_reviewed_config_is_loaded(tmp_path: Path):
    (tmp_path / "judgment_scope.csv").write_text(
        "source_label,scope,review_status,reason\nBonus accrual,IN_SCOPE,REVIEWED,Reviewed by team\n",
        encoding="utf-8",
    )
    (tmp_path / "mapping.csv").write_text(
        "source_label,category,parent_category,review_status,reason\nBonus accrual,Bonus,Employee accruals,REVIEWED,\n",
        encoding="utf-8",
    )
    store = load_judgments(tmp_path)
    judgment = store.get("  BONUS   ACCRUAL ")
    assert judgment.scope == Scope.IN_SCOPE
    assert judgment.category == "Bonus"
    assert judgment.parent_category == "Employee accruals"
