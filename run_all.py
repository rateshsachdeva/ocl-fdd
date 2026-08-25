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
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ocl_agent.ai_host_cli import run_ai_host
from ocl_agent.config import ensure_runtime_folders
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

    paths = ensure_runtime_folders()
    if args.ai_host == "copilot":
        print("AI host: GitHub Copilot CLI")

    for ai_step in range(args.max_ai_steps + 1):
        try:
            result = run_end_to_end(
                paths,
                data_prep_output=args.data_prep_output,
                part1_only=args.part1_only,
                skip_report=args.skip_report,
            )
        except (FileNotFoundError, ValueError, RuntimeError, InputContractError, JudgmentError, SemanticHandoffError, FinalQAError) as error:
            print(f"OCL stopped safely: {error}")
            return 2

        _print_result_summary(result)

        if result.coordination:
            actor = str(result.coordination.get("next_actor") or "").upper()
            action = result.coordination.get("next_action")

            if actor == "AI_HOST":
                if args.ai_host == "external":
                    print(f"AI host action: {action}. Complete the referenced artifacts and rerun.")
                    return 0
                if ai_step >= args.max_ai_steps:
                    print(
                        f"OCL stopped safely after {args.max_ai_steps} automatic AI steps. "
                        "Review the latest workflow coordination before continuing."
                    )
                    return 2

                host_result = run_ai_host(result.coordination, ROOT)
                if not host_result.success:
                    print(f"Automatic GitHub Copilot host unavailable or failed: {host_result.message}")
                    if "authentication" in host_result.message.casefold() or "no authentication information" in host_result.message.casefold():
                        print("One-time setup required: run `copilot login --web-flow`, complete GitHub sign-in, then rerun `python run_all.py`.")
                    else:
                        print("Run `copilot --version` to confirm GitHub Copilot CLI is installed and callable, then rerun `python run_all.py`.")
                    print(f"AI host action remains: {action}. No workflow artifact was accepted, so the financial workflow has not advanced incorrectly.")
                    return 0

                print("GitHub Copilot completed the AI_HOST checkpoint. Resuming workflow...")
                continue

            if actor == "HUMAN":
                print(f"Human review required: {action}. Review only the identified judgment/approval matters, then rerun.")
                return 0

            print(f"Workflow coordination requires review: {action or actor or 'UNKNOWN'}")
            return 0

        published = None
        if result.databook and result.state in {"READY", "DATABOOK_READY"}:
            try:
                published = publish_versioned_deliverables(
                    result.databook,
                    result.report,
                    paths.output,
                )
            except OSError as error:
                print(f"OCL stopped safely: completed outputs could not be versioned: {error}")
                return 2
            print(f"Published deliverable version: v{published.version}")

        databook_path = published.databook if published is not None else result.databook
        report_path = published.report if published is not None else result.report

        if databook_path:
            print(f"Databook: {databook_path}")
        if result.qa:
            print(f"Final QA: {result.qa.get('status')}")
        if args.part1_only:
            print("OCL databook: READY")
            return 0
        print(f"Part 2 findings: {result.findings}")
        print(f"Part 3 management questions: {result.questions}")
        if report_path:
            print(f"Report: {report_path}")
        print("OCL workflow: READY")
        return 0 if result.state == "READY" else 2

    print("OCL stopped safely: automatic workflow loop exhausted unexpectedly.")
    return 2


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


if __name__ == "__main__":
    raise SystemExit(main())
