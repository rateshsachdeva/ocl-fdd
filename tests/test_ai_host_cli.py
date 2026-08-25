from types import SimpleNamespace

import ocl_agent.ai_host_cli as ai_host_cli


def test_available_providers_are_detected_in_stable_order(monkeypatch):
    monkeypatch.setattr(
        ai_host_cli.shutil,
        "which",
        lambda name: f"/fake/{name}" if name in {"claude", "copilot"} else None,
    )
    assert ai_host_cli.available_providers() == ("claude", "copilot")


def test_provider_commands_use_noninteractive_modes():
    prompt = "complete checkpoint"
    assert ai_host_cli._command("codex", "codex", prompt) == [
        "codex",
        "exec",
        "--ephemeral",
        prompt,
    ]
    assert ai_host_cli._command("claude", "claude", prompt) == [
        "claude",
        "-p",
        prompt,
        "--allowedTools",
        "Read",
        "Write",
        "Edit",
    ]
    assert ai_host_cli._command("copilot", "copilot", prompt) == [
        "copilot",
        "-p",
        prompt,
        "-s",
        "--no-ask-user",
        "--allow-tool=read,write",
    ]


def test_auto_provider_falls_back_when_first_cli_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(ai_host_cli.shutil, "which", lambda name: f"/fake/{name}")
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=1 if command[0].endswith("codex") else 0)

    monkeypatch.setattr(ai_host_cli.subprocess, "run", fake_run)
    result = ai_host_cli.run_ai_host(
        {
            "next_actor": "AI_HOST",
            "next_action": "WRITE_FDD_PARTNER_ANALYSIS",
            "required_artifacts": [str(tmp_path / "analysis_interpretation.json")],
        },
        tmp_path,
        provider="auto",
    )

    assert result.success is True
    assert result.provider == "claude"
    assert result.attempted == ("codex", "claude")
    assert len(calls) == 2


def test_ai_host_prompt_preserves_financial_boundary():
    prompt = ai_host_cli._build_prompt(
        {
            "next_actor": "AI_HOST",
            "next_action": "UNDERSTAND_AND_PLAN",
            "required_artifacts": ["dataset_map.json", "processing_plan.json"],
        }
    )
    assert "Do NOT edit production code" in prompt
    assert "Do NOT invent or recalculate financial amounts" in prompt
    assert "Do NOT run python run_all.py yourself" in prompt
    assert "FDD partner" in prompt
