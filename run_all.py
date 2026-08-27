"""Main OCL workflow entry point.

Normal use:

    python run_all.py

Raw client files are read from references/source/. The workflow advances through
deterministic Python stages and automatically delegates AI_HOST reasoning
checkpoints to GitHub Copilot CLI when available/authenticated. No model API is
embedded in the financial Python core.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ocl_agent.ai_host_cli import run_ai_host
from ocl_agent.config import ensure_runtime_folders
from ocl_agent.end_to_end import run_end_to_end
from ocl_agent.final_qa import FinalQAError
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
    parser.add_argument("--part1-only", action="store_true", help="Stop after the reconciled styled databook is ready.")
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

    paths = ensure_runtime_folders()
    session_started = time.perf_counter()
    python_pass_times: list[float] = []
    ai_times: list[tuple[str, float]] = []

    def finish(code: int) -> int:
        _print_runtime_summary(session_started, python_pass_times, ai_times)
        return code

    if args.ai_host == "copilot":
        print("AI host: GitHub Copilot CLI")
        print("AI policy: Copilot runs only at explicit AI_HOST reasoning checkpoints; Python owns routine processing, calculations and rendering.")

    for ai_step in range(args.max_ai_steps + 1):
        pass_started = time.perf_counter()
        try:
            result = run_end_to_end(
                paths,
                data_prep_output=args.data_prep_output,
                part1_only=args.part1_only,
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

        if result.published_version is not None:
            print(f"Published deliverable version: v{result.published_version}")
        if result.databook:
            print(f"Databook: {result.databook}")
        if result.qa:
            print(f"Final QA: {result.qa.get('status')}")
        if args.part1_only:
            print("OCL databook: READY")
            return finish(0)
        print(f"Part 2 findings: {result.findings}")
        print(f"Part 3 management questions: {result.questions}")
        print("OCL workflow: READY")
        return finish(0 if result.state == "READY" else 2)

    print("OCL stopped safely: automatic workflow loop exhausted unexpectedly.")
    return finish(2)


def _print_result_summary(result) -> None:
    print(f"Workflow state: {result.state}")
    if result.data_prep_output:
        print(f"Published standardized data: {result.data_prep_output}")
    if result.runtime_config:
        print(f"Package review config: {result.runtime_config}")
    if result.checkpoint:
        print(f"Workflow checkpoint: {result.checkpoint}")
    if result.timings:
        print("Deterministic stage timings:")
        for stage, elapsed in result.timings.items():
            print(f"  {stage}: {_format_duration(elapsed)}")
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
