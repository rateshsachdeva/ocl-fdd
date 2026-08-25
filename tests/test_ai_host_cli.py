from pathlib import Path
from types import SimpleNamespace

import ocl_agent.ai_host_cli as ai_host_cli


def _completed(returncode=0, stdout="version 1.0"):
    return SimpleNamespace(returncode=returncode, stdout=stdout)


def test_copilot_available_when_runnable(monkeypatch):
    monkeypatch.setattr(ai_host_cli.shutil, "which", lambda name: "/fake/copilot" if name == "copilot" else None)
    monkeypatch.setattr(ai_host_cli, "_probe_cli", lambda executable: True)
    assert ai_host_cli.copilot_available() is True


def test_copilot_installer_shim_is_not_treated_as_available(monkeypatch):
    monkeypatch.setattr(
        ai_host_cli.subprocess,
        "run",
        lambda *args, **kwargs: _completed(
            0,
            "Cannot find GitHub Copilot CLI\nInstall GitHub Copilot CLI? (y/N):",
        ),
    )
    assert ai_host_cli._probe_cli("copilot") is False


def test_probe_uses_utf8_safe_decoding(monkeypatch):
    captured = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return _completed(0, "Copilot CLI 1.0")

    monkeypatch.setattr(ai_host_cli.subprocess, "run", fake_run)
    assert ai_host_cli._probe_cli("copilot") is True
    assert captured["encoding"] == "utf-8"
    assert captured["errors"] == "replace"


def test_copilot_command_is_noninteractive_and_read_write_only():
    prompt = "complete checkpoint"
    assert ai_host_cli._command("copilot", prompt) == [
        "copilot",
        "-p",
        prompt,
        "-s",
        "--no-ask-user",
        "--allow-tool=read,write",
    ]


def test_zero_exit_without_required_artifact_is_failure_and_auth_hint(monkeypatch, tmp_path):
    monkeypatch.setattr(ai_host_cli.shutil, "which", lambda name: "/fake/copilot" if name == "copilot" else None)
    monkeypatch.setattr(ai_host_cli, "_probe_cli", lambda executable: True)

    def fake_run(command, **kwargs):
        return _completed(0, "Error: No authentication information found.")

    monkeypatch.setattr(ai_host_cli.subprocess, "run", fake_run)
    artifact = tmp_path / "dataset_map.json"
    result = ai_host_cli.run_ai_host(
        {
            "next_actor": "AI_HOST",
            "next_action": "UNDERSTAND_AND_PLAN",
            "required_artifacts": [str(artifact)],
        },
        tmp_path,
    )

    assert result.success is False
    assert result.provider == "copilot"
    assert "required artifact" in result.message
    assert "No authentication information found" in result.message
    assert "copilot login --web-flow" in result.message


def test_ai_host_uses_utf8_safe_decoding(monkeypatch, tmp_path):
    monkeypatch.setattr(ai_host_cli.shutil, "which", lambda name: "/fake/copilot" if name == "copilot" else None)
    monkeypatch.setattr(ai_host_cli, "_probe_cli", lambda executable: True)
    artifact = tmp_path / "dataset_map.json"
    captured = {}

    def fake_run(command, **kwargs):
        captured.update(kwargs)
        artifact.write_text('{"status":"COMPLETED"}', encoding="utf-8")
        return _completed(0, "completed \ufffd safely")

    monkeypatch.setattr(ai_host_cli.subprocess, "run", fake_run)
    result = ai_host_cli.run_ai_host({"required_artifacts": [str(artifact)]}, tmp_path)

    assert result.success is True
    assert captured["encoding"] == "utf-8"
    assert captured["errors"] == "replace"


def test_success_requires_required_artifact_to_be_created(monkeypatch, tmp_path):
    monkeypatch.setattr(ai_host_cli.shutil, "which", lambda name: "/fake/copilot" if name == "copilot" else None)
    monkeypatch.setattr(ai_host_cli, "_probe_cli", lambda executable: True)
    artifact = tmp_path / "analysis_interpretation.json"

    def fake_run(command, **kwargs):
        artifact.write_text('{"status":"COMPLETED"}', encoding="utf-8")
        return _completed(0, "completed")

    monkeypatch.setattr(ai_host_cli.subprocess, "run", fake_run)
    result = ai_host_cli.run_ai_host(
        {"required_artifacts": [str(artifact)]},
        tmp_path,
    )

    assert result.success is True
    assert result.provider == "copilot"
    assert result.attempted == ("copilot",)


def test_preexisting_artifact_must_be_updated(monkeypatch, tmp_path):
    monkeypatch.setattr(ai_host_cli.shutil, "which", lambda name: "/fake/copilot" if name == "copilot" else None)
    monkeypatch.setattr(ai_host_cli, "_probe_cli", lambda executable: True)
    artifact = tmp_path / "dataset_map.json"
    artifact.write_text("old", encoding="utf-8")

    monkeypatch.setattr(
        ai_host_cli.subprocess,
        "run",
        lambda command, **kwargs: _completed(0, "done"),
    )
    result = ai_host_cli.run_ai_host(
        {"required_artifact": str(artifact)},
        tmp_path,
    )

    assert result.success is False
    assert "not updated" in result.message


def test_every_required_artifact_must_be_created_or_updated(monkeypatch, tmp_path):
    monkeypatch.setattr(ai_host_cli.shutil, "which", lambda name: "/fake/copilot" if name == "copilot" else None)
    monkeypatch.setattr(ai_host_cli, "_probe_cli", lambda executable: True)
    dataset_map = tmp_path / "dataset_map.json"
    processing_plan = tmp_path / "processing_plan.json"
    approval_questions = tmp_path / "approval_questions.json"
    for artifact in (dataset_map, processing_plan, approval_questions):
        artifact.write_text("old", encoding="utf-8")

    def fake_run(command, **kwargs):
        dataset_map.write_text("new", encoding="utf-8")
        return _completed(0, "completed only one artifact")

    monkeypatch.setattr(ai_host_cli.subprocess, "run", fake_run)
    result = ai_host_cli.run_ai_host(
        {
            "required_artifacts": [
                str(dataset_map),
                str(processing_plan),
                str(approval_questions),
            ]
        },
        tmp_path,
    )

    assert result.success is False
    assert str(processing_plan) in result.message
    assert str(approval_questions) in result.message
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


def test_ai_host_prompt_preserves_financial_boundary_and_forbids_nested_execution():
    prompt = ai_host_cli._build_prompt(
        {
            "next_actor": "AI_HOST",
            "next_action": "UNDERSTAND_AND_PLAN",
            "required_artifacts": ["dataset_map.json", "processing_plan.json"],
        }
    )
    assert "Do NOT edit production code" in prompt
    assert "Do NOT invent or recalculate financial amounts" in prompt
    assert "already prepared the deterministic evidence" in prompt
    assert "Do NOT run Python, shell commands, git commands" in prompt
    assert "Do NOT run python run_all.py" not in prompt
    assert "FDD partner" in prompt
