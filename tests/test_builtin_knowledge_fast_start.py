from pathlib import Path

from ocl_agent import ai_host_cli, data_prep_bridge


def test_builtin_knowledge_pack_exists_and_contains_benchmark_patterns():
    repo_root = Path(__file__).resolve().parents[1]
    knowledge = repo_root / data_prep_bridge.BUILTIN_KNOWLEDGE_RELATIVE
    text = knowledge.read_text(encoding="utf-8")
    for expected in (
        "Cat",
        "Map1",
        "Actual/Budget/Variance",
        "multiple logical datasets",
        "post-close settlement",
        "adequacy",
        "completeness",
        "duplicates",
        "SUPPORTED",
        "UNSUPPORTED",
    ):
        assert expected in text
    assert "Current source evidence" in text


def test_understand_and_plan_coordination_gets_fast_start_knowledge(tmp_path: Path):
    knowledge = tmp_path / data_prep_bridge.BUILTIN_KNOWLEDGE_RELATIVE
    knowledge.parent.mkdir(parents=True)
    knowledge.write_text("reference knowledge", encoding="utf-8")
    coordination = {"next_actor": "AI_HOST", "next_action": "UNDERSTAND_AND_PLAN"}
    data_prep_bridge._attach_builtin_planning_knowledge(coordination, tmp_path)
    assert coordination["builtin_knowledge"] == data_prep_bridge.BUILTIN_KNOWLEDGE_RELATIVE
    assert coordination["fast_start_mode"] is True
    assert "hypotheses" in coordination["knowledge_usage_rule"]


def test_other_ai_checkpoints_do_not_receive_dataset_fast_start_knowledge(tmp_path: Path):
    knowledge = tmp_path / data_prep_bridge.BUILTIN_KNOWLEDGE_RELATIVE
    knowledge.parent.mkdir(parents=True)
    knowledge.write_text("reference knowledge", encoding="utf-8")
    coordination = {"next_actor": "AI_HOST", "next_action": "WRITE_FDD_PARTNER_ANALYSIS"}
    data_prep_bridge._attach_builtin_planning_knowledge(coordination, tmp_path)
    assert "builtin_knowledge" not in coordination
    assert "fast_start_mode" not in coordination


def test_ai_host_prompt_enforces_fast_start_without_assuming_prior_patterns():
    prompt = ai_host_cli._build_prompt(
        {
            "next_actor": "AI_HOST",
            "next_action": "UNDERSTAND_AND_PLAN",
            "builtin_knowledge": data_prep_bridge.BUILTIN_KNOWLEDGE_RELATIVE,
            "fast_start_mode": True,
        }
    )
    assert "low-priority pattern library" in prompt
    assert "Do not rediscover a known pattern" in prompt
    assert "targeted inspection only" in prompt
    assert "prepared profile" in prompt
    assert "not as truth" in prompt


def test_builtin_knowledge_does_not_embed_benchmark_golden_answers():
    repo_root = Path(__file__).resolve().parents[1]
    text = (repo_root / data_prep_bridge.BUILTIN_KNOWLEDGE_RELATIVE).read_text(encoding="utf-8").casefold()
    for forbidden in ("expected_results.xlsx", "golden_truth", "€1.5m", "€0.9m"):
        assert forbidden.casefold() not in text
    assert "reference knowledge, not golden truth" in text
    assert "hypotheses to test, not conclusions to assume" in text
