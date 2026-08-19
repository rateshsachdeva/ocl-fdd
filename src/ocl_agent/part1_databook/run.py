"""Part 1 entry point.

Stage 0 foundation validates the upstream standardized package and config.  The
engagement-specific semantic adapter that turns standardized rows into
`OCLRecord` objects will be added only after its contract is reviewed; this
avoids hard-coding trial-balance field names into the OCL core.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ocl_agent.part1_databook.input_contract import StandardizedPackage, discover_standardized_package
from ocl_agent.part1_databook.judgments import JudgmentStore, load_judgments


@dataclass(frozen=True)
class Part1FoundationResult:
    package: StandardizedPackage
    judgments: JudgmentStore


def prepare_foundation(standardized_output: Path, config_dir: Path) -> Part1FoundationResult:
    return Part1FoundationResult(
        package=discover_standardized_package(standardized_output),
        judgments=load_judgments(config_dir),
    )
