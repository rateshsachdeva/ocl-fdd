from pathlib import Path


def test_builtin_knowledge_contains_patterns_not_golden_truth_answers():
    repo_root = Path(__file__).resolve().parents[1]
    text = (repo_root / "fdd-data-preparation" / "knowledge_system" / "BUILTIN_FDD_SOURCE_KNOWLEDGE.md").read_text(encoding="utf-8")
    lowered = text.casefold()

    # Keep the pack as generic hypotheses. Benchmark-specific expected-result
    # labels/amounts belong in test fixtures, not in the runtime knowledge given
    # to the interpreting AI host.
    for forbidden in (
        "expected_results.xlsx",
        "golden_truth",
        "€1.5m",
        "€0.9m",
        "answer label",
    ):
        assert forbidden.casefold() not in lowered

    assert "reference knowledge, not golden truth" in lowered
    assert "hypotheses to test, not conclusions to assume" in lowered
