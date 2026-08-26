"""Invoke GitHub Copilot CLI for AI_HOST workflow checkpoints.

The user's authenticated GitHub Copilot CLI performs contextual reasoning and
writes only the workflow artifacts requested by the coordination contract. No
model API is embedded in the financial Python core.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AIHostRunResult:
    provider: str | None
    attempted: tuple[str, ...]
    success: bool
    message: str


def copilot_available() -> bool:
    executable = shutil.which("copilot")
    return bool(executable and _probe_cli(executable))


def run_ai_host(coordination: dict[str, Any], repo_root: Path, *, timeout_seconds: int = 900) -> AIHostRunResult:
    repo_root = Path(repo_root).resolve()
    executable = shutil.which("copilot")
    if not executable or not _probe_cli(executable):
        return AIHostRunResult("copilot" if executable else None, ("copilot",) if executable else (), False, "GitHub Copilot CLI is not installed/runnable on PATH.")

    prompt = _build_prompt(coordination)
    required_artifacts = _required_artifact_paths(coordination, repo_root)
    before = {path: _artifact_state(path) for path in required_artifacts}
    command = _command(executable, prompt)
    try:
        completed = subprocess.run(command, cwd=repo_root, check=False, timeout=timeout_seconds, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return AIHostRunResult("copilot", ("copilot",), False, f"GitHub Copilot CLI timed out after {timeout_seconds} seconds.")
    except OSError as error:
        return AIHostRunResult("copilot", ("copilot",), False, f"GitHub Copilot CLI could not start: {error}")

    output_tail = _output_tail(completed.stdout)
    if completed.returncode != 0:
        detail = f"; {output_tail}" if output_tail else ""
        return AIHostRunResult("copilot", ("copilot",), False, f"GitHub Copilot CLI exited with code {completed.returncode}{detail}")

    if required_artifacts:
        after = {path: _artifact_state(path) for path in required_artifacts}
        missing = [str(path) for path, state in after.items() if state is None]
        unchanged = [str(path) for path in required_artifacts if after[path] is not None and before[path] == after[path]]
        if missing or unchanged:
            reasons: list[str] = []
            if missing:
                reasons.append("required artifact(s) were not created: " + ", ".join(missing))
            if unchanged:
                reasons.append("required artifact(s) were not updated: " + ", ".join(unchanged))
            reason = "; ".join(reasons)
            if output_tail:
                reason += f"; CLI output: {output_tail}"
            if "no authentication information" in (completed.stdout or "").casefold():
                reason += "; authenticate once with `copilot login --web-flow` and rerun"
            return AIHostRunResult("copilot", ("copilot",), False, reason)

    return AIHostRunResult("copilot", ("copilot",), True, "GitHub Copilot completed the AI_HOST checkpoint and produced the required artifact(s).")


def _probe_cli(executable: str, timeout_seconds: int = 8) -> bool:
    try:
        completed = subprocess.run([executable, "--version"], check=False, timeout=timeout_seconds, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    except (subprocess.TimeoutExpired, OSError):
        return False
    output = (completed.stdout or "").casefold()
    installer_prompt = "cannot find github copilot cli" in output or "install github copilot cli?" in output
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
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _output_tail(output: str | None, limit: int = 500) -> str:
    text = " ".join((output or "").strip().split())
    return text if len(text) <= limit else "..." + text[-limit:]


def _build_prompt(coordination: dict[str, Any]) -> str:
    payload = json.dumps(coordination, indent=2, default=str)
    return f"""You are the AI_HOST for the OCL FDD repository workflow.

Complete exactly one workflow checkpoint described by the coordination JSON below.

Rules:
- Work in the current repository, but do not browse it broadly.
- Read only the instruction, handoff, review context, prepared profile, knowledge evidence and other evidence explicitly referenced by the coordination payload or explicitly linked from those files.
- The parent Python workflow has already prepared the deterministic evidence needed for this checkpoint. Reason from those files directly.
- Create or update only the workflow artifact(s) required by the coordination/instructions.
- Do NOT run Python, shell commands, git commands, installers, network tools, or `python run_all.py` inside this AI checkpoint.
- Do NOT edit production code, tests, source workbooks, or raw files in references/source.
- Do NOT invent or recalculate financial amounts when Python owns the calculation.
- Preserve reviewed human judgments.
- When the action is UNDERSTAND_AND_PLAN and `builtin_knowledge` is present in coordination, read that file together with the prepared profile/samples before deeper inspection. Treat it as a low-priority pattern library, not as truth. Use it to recognize known workbook structures, ambiguous fields, likely supporting-dataset roles and evidence requirements quickly. Do not rediscover a known pattern through broad raw-file inspection when the current deterministic evidence already supports it.
- When `fast_start_mode` is true, prefer completing the Dataset Map + Processing Plan from the prepared profile, samples, reusable knowledge and built-in knowledge. Use targeted inspection only for a specific unresolved ambiguity that could materially change dataset grain, field meaning, source role, join keys or downstream processing. Do not inspect every file/month independently when deterministic evidence shows a common schema.
- When the action is UNDERSTAND_AND_PLAN, preserve source-present supporting FDD datasets when evidence shows they may support OCL analysis, including monthly P&L/expense data, detailed accrued-liability schedules, movement/reversal/settlement or subsequent-payment data, payroll/revenue context and account mapping. Preserve useful evidence fields such as dates, vendor/counterparty, document or obligation identifiers, descriptions, movement type, settlement/payment date, expected amount and related expense category when they exist. Do not discard supporting data merely because it is not the core annual OCL listing; describe its role in the Dataset Map / Processing Plan from the supplied evidence.
- If evidence is genuinely insufficient, write the required unresolved/blocking question artifact rather than trying to execute code yourself.
- If this is the FDD analysis checkpoint, think and write as an experienced FDD partner and follow FDD_PARTNER_ANALYSIS.md exactly.
- Do not stop to ask the user unless the referenced instruction explicitly says a genuine human judgment is required. This call is only for AI_HOST work.

Workflow coordination:
{payload}

When the required artifact(s) are complete and valid JSON/files have been written, exit successfully.
"""


def _command(executable: str, prompt: str) -> list[str]:
    return [executable, "-p", prompt, "-s", "--no-ask-user", "--allow-tool=read,write"]
