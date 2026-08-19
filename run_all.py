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
from ocl_agent.part1_databook.run import run_stage2
from ocl_agent.part1_databook.semantic_handoff import SemanticHandoffError


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the OCL FDD workflow.")
    parser.add_argument(
        "--data-prep-output",
        type=Path,
        help="Approved fdd-data-preparation output/latest directory.",
    )
    args = parser.parse_args()
    paths = ensure_runtime_folders()
    try:
        data_prep_output = discover_data_prep_output(paths, args.data_prep_output)
        result = run_stage2(data_prep_output, paths.config, paths.output)
    except (FileNotFoundError, ValueError, SemanticHandoffError) as error:
        print(f"OCL stopped safely: {error}")
        return 2

    print(f"Stage 2 state: {result.state}")
    print(f"Input review: {result.input_review}")
    if result.handoff_draft:
        print(f"Semantic handoff draft: {result.handoff_draft}")
        print("The AI host must confirm dataset usages and field roles in config/semantic_handoff.json, then rerun.")
        return 2
    if result.semantic_review:
        print(f"Semantic review: {result.semantic_review}")
        print(f"OCL records built: {len(result.build.records) if result.build else 0}")
        print(f"Unresolved source rows: {len(result.build.issues) if result.build else 0}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
