"""Main OCL workflow entry point."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ocl_agent.config import discover_data_prep_output, ensure_runtime_folders
from ocl_agent.part1_databook.run import run_part1
from ocl_agent.part1_databook.semantic_handoff import SemanticHandoffError
from ocl_agent.part2_analysis.run import run_analysis
from ocl_agent.part3_qanda.run import run_qanda
from ocl_agent.part4_report.run import run_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the OCL FDD workflow.")
    parser.add_argument("--data-prep-output", type=Path, help="Approved fdd-data-preparation output/latest directory.")
    parser.add_argument("--part1-only", action="store_true", help="Stop after the reconciled databook is ready.")
    args = parser.parse_args()
    paths = ensure_runtime_folders()
    try:
        result = run_part1(discover_data_prep_output(paths, args.data_prep_output), paths.config, paths.output)
    except (FileNotFoundError, ValueError, SemanticHandoffError) as error:
        print(f"OCL stopped safely: {error}")
        return 2
    print(f"Part 1 state: {result.state}")
    print(f"Input review: {result.input_review}")
    if result.handoff_draft:
        print(f"Semantic handoff draft: {result.handoff_draft}")
        print("AI host action: confirm dataset usages and field roles in config/semantic_handoff.json, then rerun.")
        return 2
    if result.semantic_review:
        print(f"Semantic review: {result.semantic_review}")
    if result.review_context:
        print(f"Review context: {result.review_context}")
    if result.state == "AWAITING_JUDGMENT_REVIEW":
        print(f"Judgment issues: {len(result.judgment_issues)}")
        print("AI host action: update reviewable config without overwriting existing human decisions; reviewed status is required before publication.")
        return 2
    if result.state == "AWAITING_CONTROL_ALIGNMENT":
        blocking = [control.control_id for control in result.controls if control.status.value in {"FAIL", "REVIEW_REQUIRED"}]
        print("Blocking controls: " + ", ".join(blocking))
        return 2
    if not result.databook or not result.build or not result.handoff:
        return 2
    print(f"Databook: {result.databook}")
    if args.part1_only:
        print("Part 1 databook: READY")
        return 0
    analysis = run_analysis(result.build.records, result.databook, package=result.package, handoff=result.handoff)
    print(f"Part 2 findings: {len(analysis.findings)}")
    questions = run_qanda(analysis, result.databook)
    print(f"Part 3 management questions: {len(questions)}")
    report = run_report(analysis, questions, paths.output)
    print(f"Report: {report}")
    print("OCL workflow: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
