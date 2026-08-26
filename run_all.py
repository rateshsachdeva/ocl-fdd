"""Main OCL workflow entry point.

Normal final-engagement use:

    python run_all.py

Optional one-source reusable-learning use:

    python run_all.py --learn-source Finance_Pack.xlsx

Raw client files are read from references/source/. The workflow advances through
deterministic Python stages and automatically delegates AI_HOST reasoning
checkpoints to GitHub Copilot CLI when available/authenticated. No model API is
embedded in the financial Python core.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ocl_agent.ai_host_cli import run_ai_host
from ocl_agent.config import RepoPaths, ensure_runtime_folders
from ocl_agent.data_prep_bridge import run_full_data_preparation
from ocl_agent.databook_display import apply_databook_display_preferences
from ocl_agent.end_to_end import run_end_to_end
from ocl_agent.final_qa import FinalQAError
from ocl_agent.output_versioning import publish_versioned_deliverables
from ocl_agent.part1_databook.input_contract import InputContractError
from ocl_agent.part1_databook.judgments import JudgmentError
from ocl_agent.part1_databook.semantic_handoff import SemanticHandoffError

AI_HOST_CHOICES = ("copilot", "external")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the complete OCL FDD skill.")
    parser.add_argument(
        "--data-prep-output",
        type=Path,
        help="Optional existing published fdd-data-preparation output/latest directory; normally omit this.",
    )
    parser.add_argument(
        "--learn-source",
        type=Path,
        help=(
            "Optional one-workbook learning mode. Process only this file from references/source, "
            "promote safe reusable data-understanding knowledge, and stop before OCL Excel/PPT creation."
        ),
    )
    parser.add_argument("--part1-only", action="store_true", help="Stop after the reconciled styled databook is ready.")
    parser.add_argument("--skip-report", action="store_true", help="Create the Excel databook but skip the secondary PowerPoint report.")
    parser.add_argument(
        "--ai-host",
        choices=AI_HOST_CHOICES,
        default="copilot",
        help=(
            "AI host for workflow reasoning checkpoints. Default is GitHub Copilot CLI. "
            "Use 'external' only when an already-open agent session will complete checkpoints manually."
        ),
    )
    parser.add_argument(
        "--max-ai-steps",
        type=int,
        default=12,
        help="Safety limit for automatic AI_HOST checkpoint continuations in one invocation.",
    )
    args = parser.parse_args()
    if args.max_ai_steps < 1:
        parser.error("--max-ai-steps must be at least 1")
    if args.learn_source is not None and args.data_prep_output is not None:
        parser.error("--learn-source cannot be combined with --data-prep-output")
    if args.learn_source is not None and (args.part1_only or args.skip_report):
        parser.error("--learn-source is already data-preparation-only and cannot be combined with --part1-only/--skip-report")

    paths = ensure_runtime_folders()
    session_started = time.perf_counter()
    python_pass_times: list[float] = []
    ai_times: list[tuple[str, float]] = []

    if args.ai_host == "copilot":
        print("AI host: GitHub Copilot CLI")
        print("AI policy: Copilot runs only at explicit AI_HOST reasoning checkpoints; Python owns routine processing, calculations and rendering.")

    if args.learn_source is not None:
        return _run_learning_source(
            paths,
            args.learn_source,
            ai_host=args.ai_host,
            max_ai_steps=args.max_ai_steps,
            session_started=session_started,
            python_pass_times=python_pass_times,
            ai_times=ai_times,
        )

    def finish(code: int) -> int:
        _print_runtime_summary(session_started, python_pass_times, ai_times)
        return code

    for ai_step in range(args.max_ai_steps + 1):
        pass_started = time.perf_counter()
        try:
            result = run_end_to_end(
                paths,
                data_prep_output=args.data_prep_output,
                part1_only=args.part1_only,
                skip_report=args.skip_report,
            )
        except (FileNotFoundError, ValueError, RuntimeError, InputContractError, JudgmentError, SemanticHandoffError, FinalQAError) as error:
            elapsed = time.perf_counter() - pass_started
            python_pass_times.append(elapsed)
            print(f"Python workflow pass {len(python_pass_times)} stopped after {_format_duration(elapsed)}.")
            print(f"OCL stopped safely: {error}")
            return finish(2)

        elapsed = time.perf_counter() - pass_started
        python_pass_times.append(elapsed)
        print(
            f"Python workflow pass {len(python_pass_times)} completed in {_format_duration(elapsed)} "
            f"-> {result.state}"
        )
        _print_result_summary(result)

        if result.coordination:
            actor = str(result.coordination.get("next_actor") or "").upper()
            action = str(result.coordination.get("next_action") or "UNKNOWN")

            if actor == "AI_HOST":
                if args.ai_host == "external":
                    print(f"AI host action: {action}. Complete the referenced artifacts and rerun.")
                    return finish(0)
                if ai_step >= args.max_ai_steps:
                    print(
                        f"OCL stopped safely after {args.max_ai_steps} automatic AI steps. "
                        "Review the latest workflow coordination before continuing."
                    )
                    return finish(2)

                print(
                    f"Starting Copilot AI checkpoint {len(ai_times) + 1}: {action}. "
                    "No deterministic calculation is being delegated to AI.",
                    flush=True,
                )
                ai_started = time.perf_counter()
                host_result = run_ai_host(result.coordination, ROOT)
                ai_elapsed = time.perf_counter() - ai_started
                ai_times.append((action, ai_elapsed))
                print(
                    f"Copilot AI checkpoint {len(ai_times)} finished in {_format_duration(ai_elapsed)}: {action}",
                    flush=True,
                )

                if not host_result.success:
                    print(f"Automatic GitHub Copilot host unavailable or failed: {host_result.message}")
                    if "authentication" in host_result.message.casefold() or "no authentication information" in host_result.message.casefold():
                        print("One-time setup required: run `copilot login --web-flow`, complete GitHub sign-in, then rerun `python run_all.py`.")
                    else:
                        print("Run `copilot --version` to confirm GitHub Copilot CLI is installed and callable, then rerun `python run_all.py`.")
                    print(f"AI host action remains: {action}. No workflow artifact was accepted, so the financial workflow has not advanced incorrectly.")
                    return finish(0)

                print("GitHub Copilot completed the AI_HOST checkpoint. Resuming deterministic workflow...")
                continue

            if actor == "HUMAN":
                print(f"Human review required: {action}. Review only the identified judgment/approval matters, then rerun.")
                return finish(0)

            print(f"Workflow coordination requires review: {action or actor or 'UNKNOWN'}")
            return finish(0)

        published = None
        if result.databook and result.state in {"READY", "DATABOOK_READY"}:
            try:
                handoff = result.part1.handoff if result.part1 is not None else None
                apply_databook_display_preferences(result.databook, handoff)
                published = publish_versioned_deliverables(
                    result.databook,
                    result.report,
                    paths.output,
                )
            except OSError as error:
                print(f"OCL stopped safely: completed outputs could not be finalized/versioned: {error}")
                return finish(2)
            print(f"Published deliverable version: v{published.version}")

        databook_path = published.databook if published is not None else result.databook
        report_path = published.report if published is not None else result.report

        if databook_path:
            print(f"Databook: {databook_path}")
        if result.qa:
            print(f"Final QA: {result.qa.get('status')}")
        if args.part1_only:
            print("OCL databook: READY")
            return finish(0)
        print(f"Part 2 findings: {result.findings}")
        print(f"Part 3 management questions: {result.questions}")
        if report_path:
            print(f"Report: {report_path}")
        print("OCL workflow: READY")
        return finish(0 if result.state == "READY" else 2)

    print("OCL stopped safely: automatic workflow loop exhausted unexpectedly.")
    return finish(2)


def _run_learning_source(
    paths: RepoPaths,
    requested_source: Path,
    *,
    ai_host: str,
    max_ai_steps: int,
    session_started: float,
    python_pass_times: list[float],
    ai_times: list[tuple[str, float]],
) -> int:
    """Learn reusable source-understanding knowledge from exactly one source file."""
    def finish(code: int) -> int:
        _print_runtime_summary(session_started, python_pass_times, ai_times)
        return code

    try:
        source_file = _resolve_learning_source(paths.source, requested_source)
        staged_source = _stage_learning_source(source_file, paths.source)
    except (FileNotFoundError, ValueError, OSError) as error:
        print(f"Learning run stopped safely: {error}")
        return finish(2)

    work_root = ROOT / "work" / "data_prep"
    resume_command = _learning_resume_command(requested_source, ai_host)
    print(f"Learning mode: {source_file.relative_to(paths.source.resolve()).as_posix()}")
    print("Purpose: understand this source and retain safe reusable knowledge only; no OCL Excel/PPT will be built.")

    for ai_step in range(max_ai_steps + 1):
        pass_started = time.perf_counter()
        try:
            result = run_full_data_preparation(ROOT, staged_source, work_root)
        except (FileNotFoundError, ValueError, RuntimeError) as error:
            elapsed = time.perf_counter() - pass_started
            python_pass_times.append(elapsed)
            print(f"Learning Python pass {len(python_pass_times)} stopped after {_format_duration(elapsed)}.")
            print(f"Learning run stopped safely: {error}")
            return finish(2)

        elapsed = time.perf_counter() - pass_started
        python_pass_times.append(elapsed)
        print(
            f"Learning Python pass {len(python_pass_times)} completed in {_format_duration(elapsed)} "
            f"-> {result.state}"
        )
        for warning in result.warnings:
            print(f"Warning: {warning}")

        if result.ready:
            print(f"Published standardized learning package: {result.standardized_output}")
            print("Learning source: COMPLETE")
            print("Safe reusable knowledge has been promoted. No final OCL databook/report was created.")
            print("When all desired sources have been learned, run `python run_all.py` with the full source set for the final engagement.")
            return finish(0)

        if result.state == "DATA_PREP_FAILED":
            print("Learning run failed safely; no incomplete learning was promoted.")
            return finish(2)

        coordination = dict(result.coordination or {})
        if coordination:
            coordination["resume_command"] = resume_command
            print("Workflow coordination:")
            print(json.dumps(coordination, indent=2, default=str))
            actor = str(coordination.get("next_actor") or "").upper()
            action = str(coordination.get("next_action") or "UNKNOWN")

            if actor == "AI_HOST":
                if ai_host == "external":
                    print(f"AI host action: {action}. Complete the referenced artifact(s), then run: {resume_command}")
                    return finish(0)
                if ai_step >= max_ai_steps:
                    print(
                        f"Learning run stopped safely after {max_ai_steps} automatic AI steps. "
                        "Review the latest workflow coordination before continuing."
                    )
                    return finish(2)

                print(f"Starting Copilot learning checkpoint {len(ai_times) + 1}: {action}.", flush=True)
                ai_started = time.perf_counter()
                host_result = run_ai_host(coordination, ROOT)
                ai_elapsed = time.perf_counter() - ai_started
                ai_times.append((action, ai_elapsed))
                print(
                    f"Copilot learning checkpoint {len(ai_times)} finished in {_format_duration(ai_elapsed)}: {action}",
                    flush=True,
                )
                if not host_result.success:
                    print(f"Automatic GitHub Copilot host unavailable or failed: {host_result.message}")
                    print(f"Learning action remains: {action}. Rerun with: {resume_command}")
                    return finish(0)
                print("GitHub Copilot completed the learning checkpoint. Resuming deterministic data preparation...")
                continue

            if actor == "HUMAN":
                print(f"Human review required during learning: {action}. Complete only the identified matter, then run: {resume_command}")
                return finish(0)

            print(f"Learning coordination requires review: {action or actor or 'UNKNOWN'}")
            return finish(0)

        print("Learning run stopped safely: data preparation is not ready and provided no continuation instruction.")
        return finish(2)

    print("Learning run stopped safely: automatic workflow loop exhausted unexpectedly.")
    return finish(2)


def _resolve_learning_source(source_root: Path, requested: Path) -> Path:
    source_root = Path(source_root).resolve()
    requested = Path(requested)

    if requested.is_absolute():
        candidate = requested.resolve()
    else:
        candidate = (source_root / requested).resolve()
        if not candidate.is_file() and len(requested.parts) == 1:
            matches = [
                path.resolve()
                for path in source_root.rglob(requested.name)
                if path.is_file() and not path.name.startswith("~$")
            ]
            if len(matches) == 1:
                candidate = matches[0]
            elif len(matches) > 1:
                raise ValueError(
                    f"More than one source is named {requested.name!r}; pass its path relative to references/source."
                )

    try:
        candidate.relative_to(source_root)
    except ValueError as error:
        raise ValueError("--learn-source must point to a file inside references/source.") from error
    if not candidate.is_file():
        raise FileNotFoundError(f"Learning source was not found: {requested}")
    if candidate.name.startswith("~$"):
        raise ValueError("Excel temporary/lock files cannot be used as learning sources.")
    return candidate


def _stage_learning_source(source_file: Path, source_root: Path) -> Path:
    """Copy one immutable source to an isolated gitignored learning package."""
    source_file = Path(source_file).resolve()
    source_root = Path(source_root).resolve()
    relative = source_file.relative_to(source_root).as_posix()
    digest = hashlib.sha256()
    digest.update(relative.encode("utf-8"))
    digest.update(b"\0")
    with source_file.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    stage = ROOT / "work" / "data_prep" / "learning_sources" / digest.hexdigest()[:16] / "source"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True, exist_ok=False)
    shutil.copy2(source_file, stage / source_file.name)
    return stage


def _learning_resume_command(requested_source: Path, ai_host: str) -> str:
    source_text = str(requested_source).replace('"', '\\"')
    command = f'python run_all.py --learn-source "{source_text}"'
    if ai_host == "external":
        command += " --ai-host external"
    return command


def _print_result_summary(result) -> None:
    print(f"Workflow state: {result.state}")
    if result.data_prep_output:
        print(f"Published standardized data: {result.data_prep_output}")
    if result.runtime_config:
        print(f"Package review config: {result.runtime_config}")
    for warning in result.warnings:
        print(f"Warning: {warning}")
    if result.coordination:
        print("Workflow coordination:")
        print(json.dumps(result.coordination, indent=2, default=str))


def _print_runtime_summary(
    session_started: float,
    python_pass_times: list[float],
    ai_times: list[tuple[str, float]],
) -> None:
    total_elapsed = time.perf_counter() - session_started
    python_elapsed = sum(python_pass_times)
    ai_elapsed = sum(elapsed for _action, elapsed in ai_times)
    print("Runtime summary:")
    print(
        f"  Total elapsed: {_format_duration(total_elapsed)} | "
        f"Python workflow passes: {_format_duration(python_elapsed)} across {len(python_pass_times)} pass(es) | "
        f"Copilot AI: {_format_duration(ai_elapsed)} across {len(ai_times)} checkpoint(s)"
    )
    if ai_times:
        for index, (action, elapsed) in enumerate(ai_times, start=1):
            print(f"  AI {index}: {action} -> {_format_duration(elapsed)}")
    else:
        print("  AI usage: none for this invocation.")


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, remainder = divmod(seconds, 60)
    if minutes < 60:
        return f"{int(minutes)}m {remainder:.0f}s"
    hours, minutes = divmod(int(minutes), 60)
    return f"{hours}h {minutes}m {remainder:.0f}s"


if __name__ == "__main__":
    raise SystemExit(main())
