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


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the OCL FDD workflow.")
    parser.add_argument("--data-prep-output", type=Path, help="Approved fdd-data-preparation output/latest directory.")
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
        print("AI host action: update reviewable config without overwriting existing human decisions; user review is required before final publication.")
        return 2
    if result.state == "AWAITING_CONTROL_ALIGNMENT":
        blocking = [control.control_id for control in result.controls if control.status.value in {"FAIL", "REVIEW_REQUIRED"}]
        print("Blocking controls: " + ", ".join(blocking))
        return 2
    if result.databook:
        print(f"Databook: {result.databook}")
        print("Part 1 databook: READY")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
