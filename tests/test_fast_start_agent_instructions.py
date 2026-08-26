from pathlib import Path


def test_repo_agent_instructions_cover_builtin_fast_start():
    repo_root = Path(__file__).resolve().parents[1]
    agents = (repo_root / "AGENTS.md").read_text(encoding="utf-8")
    copilot = (repo_root / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")

    for text in (agents, copilot):
        assert "builtin_knowledge" in text
        assert "fast_start_mode" in text
        assert "Current source evidence" in text
        assert "targeted inspection" in text

    assert "benchmark expected results" in agents
    assert "benchmark golden answers" in copilot
