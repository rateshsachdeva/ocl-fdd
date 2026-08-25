"""Invoke a locally installed coding-agent CLI for AI_HOST workflow checkpoints.

This keeps the repository vendor-neutral and avoids embedding model API calls.
The user's already-authenticated local CLI performs contextual reasoning and
writes only the workflow artifacts requested by the coordination contract.
"""
from __future__ import annotations

import hashlib
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
    """Return supported AI CLIs that are actually runnable, in stable order."""
    available: list[str] = []
    for name in PROVIDERS:
        executable = shutil.which(name)
        if executable and _probe_cli(executable):
            available.append(name)
    return tuple(available)


def run_ai_host(
    coordination: dict[str, Any],
    repo_root: Path,
    *,
    provider: str = "auto",
    timeout_seconds: int = 900,
) -> AIHostRunResult:
    """Run one AI_HOST checkpoint through Codex, Claude Code or Copilot CLI.

    ``provider=auto`` tries runnable providers in stable preference order. An
    explicit provider attempts only that CLI. A CLI run counts as successful
    only when it exits successfully *and* the checkpoint artifacts requested by
    the coordination contract were actually created or updated. This prevents a
    CLI bootstrap/authentication failure that returns exit code 0 from causing
    the root workflow to loop on the same AI checkpoint.
    """
    repo_root = Path(repo_root).resolve()
    if provider not in {"auto", *PROVIDERS}:
        raise ValueError(f"Unsupported AI host provider: {provider}")

    candidates = list(available_providers()) if provider == "auto" else [provider]
    if not candidates:
        return AIHostRunResult(None, (), False, "No runnable supported AI CLI was found on PATH.")

    prompt = _build_prompt(coordination)
    required_artifacts = _required_artifact_paths(coordination, repo_root)
    attempted: list[str] = []
    errors: list[str] = []

    for name in candidates:
        executable = shutil.which(name)
        if not executable:
            errors.append(f"{name}: CLI not found on PATH")
            continue

        attempted.append(name)
        before = {path: _artifact_state(path) for path in required_artifacts}
        command = _command(name, executable, prompt)
        try:
            completed = subprocess.run(
                command,
                cwd=repo_root,
                check=False,
                timeout=timeout_seconds,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
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

        output_tail = _output_tail(completed.stdout)
        if completed.returncode != 0:
            detail = f"; {output_tail}" if output_tail else ""
            errors.append(f"{name}: exited with code {completed.returncode}{detail}")
            if provider != "auto":
                break
            continue

        if required_artifacts:
            after = {path: _artifact_state(path) for path in required_artifacts}
            missing = [str(path) for path, state in after.items() if state is None]
            progressed = any(before[path] != after[path] for path in required_artifacts)
            if missing or not progressed:
                if missing:
                    reason = "required artifact(s) were not created: " + ", ".join(missing)
                else:
                    reason = "required artifact(s) were not updated"
                if output_tail:
                    reason += f"; CLI output: {output_tail}"
                errors.append(f"{name}: {reason}")
                if provider != "auto":
                    break
                continue

        return AIHostRunResult(
            name,
            tuple(attempted),
            True,
            f"{name} completed the AI_HOST checkpoint and produced the required artifact(s).",
        )

    return AIHostRunResult(
        attempted[-1] if attempted else None,
        tuple(attempted),
        False,
        "; ".join(errors) or "AI host did not complete the checkpoint.",
    )


def _probe_cli(executable: str, timeout_seconds: int = 8) -> bool:
    """Check that a PATH entry is a runnable CLI, not an installer/bootstrap shim."""
    try:
        completed = subprocess.run(
            [executable, "--version"],
            check=False,
            timeout=timeout_seconds,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    output = (completed.stdout or "").casefold()
    installer_prompt = (
        "cannot find github copilot cli" in output
        or "install github copilot cli?" in output
    )
    return completed.returncode == 0 and not installer_prompt


def _required_artifact_paths(coordination: dict[str, Any], repo_root: Path) -> tuple[Path, ...]:
    values: list[str] = []
    singular = coordination.get("required_artifact")
    if singular:
        values.append(str(singular))
    plural = coordination.get("required_artifacts")
    if isinstance(plural, (list, tuple)):
        values.extend(str(item) for item in plural if item)

    paths: list[Path] = []
    seen: set[Path] = set()
    for value in values:
        path = Path(value)
        if not path.is_absolute():
            path = repo_root / path
        path = path.resolve()
        if path not in seen:
            seen.add(path)
            paths.append(path)
    return tuple(paths)


def _artifact_state(path: Path) -> str | None:
    """Return a content fingerprint for a required artifact, or None if absent."""
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _output_tail(output: str | None, limit: int = 500) -> str:
    text = " ".join((output or "").strip().split())
    if len(text) <= limit:
        return text
    return "..." + text[-limit:]


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
