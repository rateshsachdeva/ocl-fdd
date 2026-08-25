"""Invoke a locally installed coding-agent CLI for AI_HOST workflow checkpoints.

This keeps the repository vendor-neutral and avoids embedding model API calls.
The user's already-authenticated local CLI performs contextual reasoning and
writes only the workflow artifacts requested by the coordination contract.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROVIDERS = ("codex", "claude", "copilot")


@dataclass(frozen=True)
class AIHostRunResult:
    provider: str | None
    attempted: tuple[str, ...]
    success: bool
    message: str


def available_providers() -> tuple[str, ...]:
    """Return supported AI CLIs currently available on PATH."""
    return tuple(name for name in PROVIDERS if shutil.which(name))


def run_ai_host(
    coordination: dict[str, Any],
    repo_root: Path,
    *,
    provider: str = "auto",
    timeout_seconds: int = 900,
) -> AIHostRunResult:
    """Run one AI_HOST checkpoint through Codex, Claude Code or Copilot CLI.

    ``provider=auto`` tries installed providers in stable preference order. An
    explicit provider attempts only that CLI. The CLI is intentionally given a
    narrow prompt: read the referenced workflow evidence/instructions, write the
    requested workflow artifact(s), and do not run the root workflow itself.
    """
    repo_root = Path(repo_root).resolve()
    if provider not in {"auto", *PROVIDERS}:
        raise ValueError(f"Unsupported AI host provider: {provider}")

    candidates = list(available_providers()) if provider == "auto" else [provider]
    if not candidates:
        return AIHostRunResult(None, (), False, "No supported AI CLI is installed on PATH.")

    prompt = _build_prompt(coordination)
    attempted: list[str] = []
    errors: list[str] = []

    for name in candidates:
        executable = shutil.which(name)
        if not executable:
            errors.append(f"{name}: CLI not found on PATH")
            continue
        attempted.append(name)
        command = _command(name, executable, prompt)
        try:
            completed = subprocess.run(
                command,
                cwd=repo_root,
                check=False,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            errors.append(f"{name}: timed out after {timeout_seconds} seconds")
            if provider != "auto":
                break
            continue
        except OSError as error:
            errors.append(f"{name}: could not start ({error})")
            if provider != "auto":
                break
            continue

        if completed.returncode == 0:
            return AIHostRunResult(
                name,
                tuple(attempted),
                True,
                f"{name} completed the AI_HOST checkpoint.",
            )
        errors.append(f"{name}: exited with code {completed.returncode}")
        if provider != "auto":
            break

    return AIHostRunResult(
        attempted[-1] if attempted else None,
        tuple(attempted),
        False,
        "; ".join(errors) or "AI host did not complete the checkpoint.",
    )


def _build_prompt(coordination: dict[str, Any]) -> str:
    payload = json.dumps(coordination, indent=2, default=str)
    return f"""You are the AI_HOST for the OCL FDD repository workflow.

Complete exactly one workflow checkpoint described by the coordination JSON below.

Rules:
- Work in the current repository.
- Read AGENTS.md first.
- Read every referenced instruction, handoff, review context and evidence file needed for this checkpoint.
- Create or update only the workflow artifact(s) required by the coordination/instructions.
- Do NOT edit production code, tests, source workbooks, or raw files in references/source.
- Do NOT invent or recalculate financial amounts when Python owns the calculation.
- Preserve reviewed human judgments.
- If this is the FDD analysis checkpoint, think and write as an experienced FDD partner and follow FDD_PARTNER_ANALYSIS.md exactly.
- Do NOT run python run_all.py yourself; the parent Python process will resume the workflow after you exit.
- Do not stop to ask the user unless the referenced instruction explicitly says a genuine human judgment is required. This call is only for AI_HOST work.

Workflow coordination:
{payload}

When the required artifact(s) are complete and valid JSON/files have been written, exit successfully.
"""


def _command(provider: str, executable: str, prompt: str) -> list[str]:
    if provider == "codex":
        return [executable, "exec", "--ephemeral", prompt]
    if provider == "claude":
        return [
            executable,
            "-p",
            prompt,
            "--allowedTools",
            "Read",
            "Write",
            "Edit",
        ]
    if provider == "copilot":
        return [
            executable,
            "-p",
            prompt,
            "-s",
            "--no-ask-user",
            "--allow-tool=read,write",
        ]
    raise ValueError(f"Unsupported AI host provider: {provider}")
