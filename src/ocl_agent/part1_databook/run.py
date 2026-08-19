"""Part 1 Stage 2 orchestration: standardized package -> semantic OCL review."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ocl_agent.part1_databook.input_contract import StandardizedPackage, discover_standardized_package, profile_package
from ocl_agent.part1_databook.judgments import JudgmentStore, load_judgments
from ocl_agent.part1_databook.record_builder import RecordBuildResult, build_ocl_records
from ocl_agent.part1_databook.review_workbook import write_input_review, write_semantic_review
from ocl_agent.part1_databook.semantic_handoff import SemanticHandoff, SemanticHandoffError, load_semantic_handoff, write_semantic_handoff_draft


@dataclass(frozen=True)
class Part1Stage2Result:
    state: str
    package: StandardizedPackage
    judgments: JudgmentStore
    input_review: Path
    handoff_draft: Path | None = None
    handoff: SemanticHandoff | None = None
    build: RecordBuildResult | None = None
    semantic_review: Path | None = None


def run_stage2(standardized_output: Path, config_dir: Path, output_dir: Path) -> Part1Stage2Result:
    package = discover_standardized_package(standardized_output)
    profiles = profile_package(package)
    judgments = load_judgments(config_dir)
    input_review = write_input_review(package, profiles, Path(output_dir) / "OCL_Input_Review.xlsx")
    handoff_path = Path(config_dir) / "semantic_handoff.json"
    if not handoff_path.exists():
        draft = write_semantic_handoff_draft(package, profiles, Path(output_dir) / "semantic_handoff_draft.json")
        return Part1Stage2Result("AWAITING_SEMANTIC_HANDOFF", package, judgments, input_review, handoff_draft=draft)
    handoff = load_semantic_handoff(handoff_path, package, profiles, require_confirmed=True)
    build = build_ocl_records(package, handoff, judgments)
    semantic_review = write_semantic_review(
        package, profiles, handoff, build, Path(output_dir) / "OCL_Stage2_Review.xlsx"
    )
    return Part1Stage2Result(
        "SEMANTIC_REVIEW_READY", package, judgments, input_review,
        handoff=handoff, build=build, semantic_review=semantic_review,
    )
