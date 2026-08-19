"""Main OCL workflow entry point.

Normal use:

    python run_all.py

Raw client files are read from references/source/.  The full embedded
fdd-data-preparation workflow profiles them, delegates contextual Dataset Map /
Processing Plan reasoning to the active AI host, executes deterministically,
and publishes standardized data before OCL begins.
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

from ocl_agent.config import ensure_runtime_folders
from ocl_agent.end_to_end import run_end_to_end
from ocl_agent.final_qa import FinalQAError
from ocl_agent.part1_databook.input_contract import InputContractError
from ocl_agent.part1_databook.judgments import JudgmentError
from ocl_agent.part1_databook.semantic_handoff import SemanticHandoffError


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the complete OCL FDD skill.")
    parser.add_argument(
        "--data-prep-output",
        type=Path,
        help="Optional existing published fdd-data-preparation output/latest directory; normally omit this.",
    )
    parser.add_argument("--part1-only", action="store_true", help="Stop after the reconciled styled databook is ready.")
    parser.add_argument("--skip-report", action="store_true", help="Create the Excel databook but skip the secondary PowerPoint report.")
    args = parser.parse_args()
    paths = ensure_runtime_folders()

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
        actor = str(result.coordination.get("next_actor") or "").upper()
        action = result.coordination.get("next_action")
        if actor == "AI_HOST":
            print(f"AI host action: {action}. Complete the referenced artifacts and rerun; an agent host should continue automatically.")
        elif actor == "HUMAN":
            print(f"Human review required: {action}. Review only the identified judgment/approval matters, then rerun.")
        return 0

    if result.databook:
        print(f"Databook: {result.databook}")
    if result.qa:
        print(f"Final QA: {result.qa.get('status')}")
    if args.part1_only:
        print("OCL databook: READY")
        return 0
    print(f"Part 2 findings: {result.findings}")
    print(f"Part 3 management questions: {result.questions}")
    if result.report:
        print(f"Report: {result.report}")
    print("OCL workflow: READY")
    return 0 if result.state == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
