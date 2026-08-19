"""Shared contracts used by all four OCL parts.

The contracts intentionally avoid a fixed financial statement schema.  They
capture provenance, reviewed judgments, dynamic hierarchy and control results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any


class Scope(StrEnum):
    IN_SCOPE = "IN_SCOPE"
    TRADE_PAYABLE = "TRADE_PAYABLE"
    FINANCING = "FINANCING"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class ReviewStatus(StrEnum):
    REVIEWED = "REVIEWED"
    PROPOSED = "PROPOSED"
    UNRESOLVED = "UNRESOLVED"


class CheckStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True)
class SourceReference:
    source_record_id: str
    source_file: str | None = None
    source_sheet: str | None = None
    source_cell: str | None = None


@dataclass(frozen=True)
class OCLJudgment:
    source_label: str
    scope: Scope
    category: str | None = None
    parent_category: str | None = None
    management_view: str | None = None
    fdd_view: str | None = None
    normality: str | None = None
    review_status: ReviewStatus = ReviewStatus.UNRESOLVED
    reason: str | None = None


@dataclass(frozen=True)
class OCLRecord:
    source: SourceReference
    period: str
    amount: Decimal
    source_label: str
    judgment: OCLJudgment
    dimensions: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ControlResult:
    control_id: str
    status: CheckStatus
    actual: Decimal | None = None
    expected: Decimal | None = None
    difference: Decimal | None = None
    message: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Finding:
    finding_id: str
    title: str
    text: str
    evidence_references: tuple[str, ...] = ()


@dataclass(frozen=True)
class ManagementQuestion:
    question_id: str
    question: str
    rationale: str
    evidence_references: tuple[str, ...] = ()
