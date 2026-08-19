"""Extensible contracts for the FDD data-preparation workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ProfilingCapability(str, Enum):
    FULL = "FULL"
    DEFERRED_UNSUPPORTED = "DEFERRED_UNSUPPORTED"


class ProfilingStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    PROFILED = "PROFILED"
    UNSUPPORTED_DEFERRED = "UNSUPPORTED_DEFERRED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class SourceFile:
    source_id: str
    filename: str
    path: Path
    extension: str
    size: int
    modified_time: datetime
    sha256: str
    profiling_capability: ProfilingCapability = ProfilingCapability.FULL


@dataclass(slots=True)
class WorkbookProfile:
    source_id: str
    worksheet_profiles: list[WorksheetProfile] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    profiling_status: ProfilingStatus = ProfilingStatus.DISCOVERED
    worksheet_names: list[str] = field(default_factory=list)
    named_ranges: list[dict[str, str | None]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WorksheetProfile:
    source_id: str
    worksheet_name: str
    worksheet_index: int
    data_regions: list[DataRegionProfile] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    visibility: str = "visible"
    excel_max_row: int = 0
    excel_max_column: int = 0
    calculated_dimension: str | None = None
    meaningful_bounds: str | None = None
    populated_cell_count: int = 0
    formula_cell_count: int = 0
    merged_ranges: list[dict[str, str | None]] = field(default_factory=list)
    hidden_rows: list[int] = field(default_factory=list)
    hidden_columns: list[str] = field(default_factory=list)
    freeze_panes: str | None = None
    indentation_levels: list[int] = field(default_factory=list)
    indentation_examples: list[dict[str, Any]] = field(default_factory=list)
    number_formats: list[str] = field(default_factory=list)
    blank_row_count: int = 0
    blank_column_count: int = 0
    blank_rows: list[int] = field(default_factory=list)
    blank_columns: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DataRegionProfile:
    region_id: str
    source_id: str
    worksheet_name: str
    cell_range: str
    populated_cell_count: int | None = None
    observations: list[str] = field(default_factory=list)
    start_row: int | None = None
    end_row: int | None = None
    start_column: int | None = None
    end_column: int | None = None
    row_count: int | None = None
    column_count: int | None = None
    density: float | None = None
    detection_reason: str | None = None
    candidate_confidence: str = "STRUCTURAL_CANDIDATE"
    preamble_candidates: list[dict[str, Any]] = field(default_factory=list)
    context_preamble_blocks: list[dict[str, Any]] = field(default_factory=list)
    header_candidates: list[dict[str, Any]] = field(default_factory=list)
    footer_candidates: list[dict[str, Any]] = field(default_factory=list)
    likely_data_row_ranges: list[dict[str, Any]] = field(default_factory=list)
    repeated_header_rows: list[int] = field(default_factory=list)
    trailing_note_rows: list[int] = field(default_factory=list)
    column_profiles: list[dict[str, Any]] = field(default_factory=list)
    samples: list[dict[str, Any]] = field(default_factory=list)
