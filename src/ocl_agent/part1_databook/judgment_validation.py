"""Completion gate for OCL-specific human-reviewed judgments."""
from __future__ import annotations

from dataclasses import dataclass

from ocl_agent.schemas import OCLRecord, ReviewStatus, Scope


@dataclass(frozen=True)
class JudgmentIssue:
    source_label: str
    source_code: str | None
    entity: str | None
    issue_type: str
    message: str


def validate_judgment_completion(records: tuple[OCLRecord, ...]) -> tuple[JudgmentIssue, ...]:
    issues: list[JudgmentIssue] = []
    seen: set[tuple[str, str, str]] = set()
    for row in records:
        source_code = _text(row.dimensions.get("source_code"))
        entity = _text(row.dimensions.get("entity"))
        key = (
            row.source_label.casefold().strip(),
            (source_code or "").casefold(),
            (entity or "").casefold(),
        )
        if key in seen:
            continue
        seen.add(key)
        judgment = row.judgment

        if judgment.scope == Scope.REVIEW_REQUIRED:
            issues.append(
                JudgmentIssue(
                    row.source_label,
                    source_code,
                    entity,
                    "SCOPE_UNRESOLVED",
                    "Scope must be explicitly reviewed.",
                )
            )
            continue

        if judgment.review_status != ReviewStatus.REVIEWED:
            issues.append(
                JudgmentIssue(
                    row.source_label,
                    source_code,
                    entity,
                    "JUDGMENT_NOT_REVIEWED",
                    "Judgment is proposed/unresolved rather than reviewed.",
                )
            )

        if judgment.scope != Scope.IN_SCOPE:
            continue
        for value, issue_type, message in (
            (judgment.category, "MAPPING_MISSING", "In-scope OCL requires a reviewed category."),
            (
                judgment.management_view,
                "MANAGEMENT_VIEW_MISSING",
                "In-scope OCL requires management working-capital/debt-like treatment.",
            ),
            (
                judgment.fdd_view,
                "FDD_VIEW_MISSING",
                "In-scope OCL requires FDD working-capital/debt-like treatment.",
            ),
            (judgment.normality, "NORMALITY_MISSING", "In-scope OCL requires normal/one-off treatment."),
        ):
            if not value:
                issues.append(JudgmentIssue(row.source_label, source_code, entity, issue_type, message))
    return tuple(issues)


def _text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
