from pathlib import Path
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
    artifact = tmp_path / "analysis_interpretation.json"
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[0].endswith("claude"):
            artifact.write_text('{"status":"COMPLETED"}', encoding="utf-8")
            return SimpleNamespace(returncode=0, stdout="completed")
        return SimpleNamespace(returncode=1, stdout="failed")

    monkeypatch.setattr(ai_host_cli.subprocess, "run", fake_run)
    result = ai_host_cli.run_ai_host(
        {
            "next_actor": "AI_HOST",
            "next_action": "WRITE_FDD_PARTNER_ANALYSIS",
            "required_artifacts": [str(artifact)],
        },
        tmp_path,
        provider="auto",
    )

    assert result.success is True
    assert result.provider == "claude"
    assert result.attempted == ("codex", "claude")
    assert len(calls) == 2


def test_zero_exit_without_required_artifact_is_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(ai_host_cli.shutil, "which", lambda name: f"/fake/{name}" if name == "copilot" else None)

    def fake_run(command, **kwargs):
        return SimpleNamespace(returncode=0, stdout="Error: No authentication information found.")

    monkeypatch.setattr(ai_host_cli.subprocess, "run", fake_run)
    artifact = tmp_path / "dataset_map.json"
    result = ai_host_cli.run_ai_host(
        {
            "next_actor": "AI_HOST",
            "next_action": "UNDERSTAND_AND_PLAN",
            "required_artifacts": [str(artifact)],
        },
        tmp_path,
        provider="auto",
    )

    assert result.success is False
    assert result.provider == "copilot"
    assert "required artifact" in result.message
    assert "No authentication information found" in result.message


def test_preexisting_artifact_must_be_updated(monkeypatch, tmp_path):
    monkeypatch.setattr(ai_host_cli.shutil, "which", lambda name: f"/fake/{name}" if name == "codex" else None)
    artifact = tmp_path / "dataset_map.json"
    artifact.write_text("old", encoding="utf-8")

    monkeypatch.setattr(
        ai_host_cli.subprocess,
        "run",
        lambda command, **kwargs: SimpleNamespace(returncode=0, stdout="done"),
    )
    result = ai_host_cli.run_ai_host(
        {"required_artifact": str(artifact)},
        tmp_path,
        provider="codex",
    )

    assert result.success is False
    assert "not updated" in result.message


def test_relative_required_artifacts_are_resolved_from_repo_root(tmp_path: Path):
    paths = ai_host_cli._required_artifact_paths(
        {"required_artifacts": ["work/a.json", "work/a.json", "work/b.json"]},
        tmp_path,
    )
    assert paths == (
        (tmp_path / "work" / "a.json").resolve(),
        (tmp_path / "work" / "b.json").resolve(),
    )


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
