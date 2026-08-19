"""Main OCL workflow entry point.

Normal use is intentionally one command:

    python run_all.py

Raw client files are read from references/source/, prepared internally, analysed
and published as output/OCL_Databook.xlsx (plus the secondary PowerPoint report).
"""
from __future__ import annotations

import argparse
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
    parser.add_argument("--data-prep-output", type=Path, help="Optional existing standardized publication; normally omit this and use references/source/.")
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
        print(f"Prepared data: {result.data_prep_output}")
    for warning in result.warnings:
        print(f"Warning: {warning}")
    if result.part1 and result.part1.state != "DATABOOK_READY":
        print(f"Part 1 state: {result.part1.state}")
        if result.part1.semantic_review:
            print(f"Review: {result.part1.semantic_review}")
        blocking = [control.control_id for control in result.part1.controls if control.status.value in {"FAIL", "REVIEW_REQUIRED"}]
        if blocking:
            print("Blocking controls: " + ", ".join(blocking))
        return 2
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
