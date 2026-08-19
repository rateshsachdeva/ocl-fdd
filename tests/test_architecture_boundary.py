from pathlib import Path


def test_ocl_never_reparses_raw_client_excel():
    root = Path(__file__).resolve().parents[1]
    end_to_end = (root / "src/ocl_agent/end_to_end.py").read_text(encoding="utf-8")
    bridge = (root / "src/ocl_agent/data_prep_bridge.py").read_text(encoding="utf-8")

    assert "integrated.py" not in end_to_end
    assert "robust.py" not in end_to_end
    assert "auto_semantics" not in end_to_end
    assert "auto_judgments" not in end_to_end
    assert "load_workbook" not in end_to_end
    assert "openpyxl" not in end_to_end
    assert "load_workbook" not in bridge
    assert "openpyxl" not in bridge

    assert not (root / "fdd-data-preparation/src/fdd_data/integrated.py").exists()
    assert not (root / "fdd-data-preparation/src/fdd_data/robust.py").exists()


def test_agent_hosts_are_told_to_continue_ai_checkpoints():
    root = Path(__file__).resolve().parents[1]
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    claude = (root / "CLAUDE.md").read_text(encoding="utf-8")
    copilot = (root / ".github/copilot-instructions.md").read_text(encoding="utf-8")

    for text in (agents, claude, copilot):
        assert "AI_HOST" in text
        assert "must_continue" in text
        assert "run_all.py" in text


def test_full_upstream_runtime_is_the_documented_production_path():
    root = Path(__file__).resolve().parents[1]
    skill = (root / "SKILL.md").read_text(encoding="utf-8")
    upstream_skill = (root / "fdd-data-preparation/SKILL.md").read_text(encoding="utf-8")

    assert "FULL fdd-data-preparation" in skill
    assert "Dataset Map + Processing Plan" in skill
    assert "AI host" in upstream_skill
    assert "Deterministic Python" in upstream_skill
