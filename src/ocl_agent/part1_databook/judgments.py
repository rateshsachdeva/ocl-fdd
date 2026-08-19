"""Load human-owned OCL meaning-layer configuration without overwriting it."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from ocl_agent.schemas import OCLJudgment, ReviewStatus, Scope


class JudgmentError(ValueError):
    pass


@dataclass(frozen=True)
class JudgmentStore:
    by_source_label: dict[str, OCLJudgment]

    def get(self, source_label: str) -> OCLJudgment:
        key = normalize_label(source_label)
        if key in self.by_source_label:
            return self.by_source_label[key]
        return OCLJudgment(
            source_label=source_label,
            scope=Scope.REVIEW_REQUIRED,
            review_status=ReviewStatus.UNRESOLVED,
            reason="No reviewed scope/mapping decision exists for this source label.",
        )


def normalize_label(value: str) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_judgments(config_dir: Path) -> JudgmentStore:
    config_dir = Path(config_dir)
    scope_rows = _read_csv(config_dir / "judgment_scope.csv")
    mapping_rows = _read_csv(config_dir / "mapping.csv")
    wc_rows = _read_csv(config_dir / "judgment_wc_debt.csv")

    scope_by_key = {normalize_label(row.get("source_label", "")): row for row in scope_rows if row.get("source_label")}
    mapping_by_key = {normalize_label(row.get("source_label", "")): row for row in mapping_rows if row.get("source_label")}
    wc_by_key = {normalize_label(row.get("source_label", "")): row for row in wc_rows if row.get("source_label")}

    result: dict[str, OCLJudgment] = {}
    for key in sorted(set(scope_by_key) | set(mapping_by_key) | set(wc_by_key)):
        scope_row = scope_by_key.get(key, {})
        mapping_row = mapping_by_key.get(key, {})
        wc_row = wc_by_key.get(key, {})
        raw_scope = (scope_row.get("scope") or "REVIEW_REQUIRED").strip().upper()
        try:
            scope = Scope(raw_scope)
        except ValueError as error:
            raise JudgmentError(f"Invalid scope {raw_scope!r} for {key!r}") from error
        status_text = (
            scope_row.get("review_status")
            or mapping_row.get("review_status")
            or wc_row.get("review_status")
            or "UNRESOLVED"
        ).strip().upper()
        try:
            review_status = ReviewStatus(status_text)
        except ValueError as error:
            raise JudgmentError(f"Invalid review status {status_text!r} for {key!r}") from error
        source_label = (
            scope_row.get("source_label")
            or mapping_row.get("source_label")
            or wc_row.get("source_label")
            or key
        )
        result[key] = OCLJudgment(
            source_label=source_label,
            scope=scope,
            category=(mapping_row.get("category") or "").strip() or None,
            parent_category=(mapping_row.get("parent_category") or "").strip() or None,
            management_view=(wc_row.get("management_view") or "").strip() or None,
            fdd_view=(wc_row.get("fdd_view") or "").strip() or None,
            normality=(wc_row.get("normality") or "").strip() or None,
            review_status=review_status,
            reason=(scope_row.get("reason") or mapping_row.get("reason") or wc_row.get("reason") or "").strip() or None,
        )
    return JudgmentStore(result)
