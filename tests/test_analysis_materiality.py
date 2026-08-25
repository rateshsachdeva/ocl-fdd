from decimal import Decimal

from ocl_agent.part2_analysis.engine import is_databook_material, is_finding_material


def test_two_level_materiality_matches_analysis_reference():
    # Broad databook review: >=100k OR >=10%.
    assert is_databook_material(Decimal("250000"), 13.5)
    assert is_databook_material(Decimal("25000"), 12.0)
    assert not is_databook_material(Decimal("25000"), 8.0)

    # Focused findings/Q&A: >=100k AND >=30%.
    assert not is_finding_material(Decimal("250000"), 13.5)
    assert is_finding_material(Decimal("250000"), 35.0)
    assert not is_finding_material(Decimal("50000"), 80.0)
