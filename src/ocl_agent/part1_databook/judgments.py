"""Load human-owned OCL meaning-layer configuration without overwriting it."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from ocl_agent.schemas import OCLJudgment, ReviewStatus, Scope

JudgmentKey = tuple[str, str, str]
VALID_WC_VIEWS = {"working_capital", "debt_like", "neither"}
VALID_NORMALITY = {"normal", "one_off"}


class JudgmentError(ValueError):
    pass


def normalize_label(value: str) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def judgment_key(
    source_label: str,
    source_code: str | None = None,
    entity: str | None = None,
) -> JudgmentKey:
    return (_normalize(entity), _normalize(source_code), _normalize(source_label))


@dataclass(frozen=True)
class JudgmentStore:
    by_key: dict[JudgmentKey, OCLJudgment]

    @property
    def by_source_label(self) -> dict[str, OCLJudgment]:
        """Backwards-compatible view of generic label-only decisions."""
        return {
            key[2]: value
            for key, value in self.by_key.items()
            if not key[0] and not key[1]
        }

    def get(
        self,
        source_label: str,
        source_code: str | None = None,
        entity: str | None = None,
    ) -> OCLJudgment:
        label = _normalize(source_label)
        code = _normalize(source_code)
        entity_key = _normalize(entity)
        candidates = (
            (entity_key, code, label),
            ("", code, label),
            (entity_key, "", label),
            ("", "", label),
        )
        for key in candidates:
            if key in self.by_key:
                return self.by_key[key]
        return OCLJudgment(
            source_label=source_label,
            scope=Scope.REVIEW_REQUIRED,
            review_status=ReviewStatus.UNRESOLVED,
            reason="No reviewed scope/mapping decision exists for this source label/code/entity.",
            source_code=source_code,
            entity=entity,
        )


def load_judgments(config_dir: Path) -> JudgmentStore:
    config_dir = Path(config_dir)
    scope_rows = _index_rows(_read_csv(config_dir / "judgment_scope.csv"), "judgment_scope.csv")
    mapping_rows = _index_rows(_read_csv(config_dir / "mapping.csv"), "mapping.csv")
    wc_rows = _index_rows(_read_csv(config_dir / "judgment_wc_debt.csv"), "judgment_wc_debt.csv")

    result: dict[JudgmentKey, OCLJudgment] = {}
    for key in sorted(set(scope_rows) | set(mapping_rows) | set(wc_rows)):
        scope_row = scope_rows.get(key, {})
        mapping_row = mapping_rows.get(key, {})
        wc_row = wc_rows.get(key, {})

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
            or key[2]
        )
        source_code = _first_text(scope_row, mapping_row, wc_row, field="source_code")
        entity = _first_text(scope_row, mapping_row, wc_row, field="entity")

        result[key] = OCLJudgment(
            source_label=source_label,
            scope=scope,
            category=_optional(mapping_row.get("category")),
            parent_category=_optional(mapping_row.get("parent_category")),
            management_view=_wc_view(wc_row.get("management_view"), "management_view", key),
            fdd_view=_wc_view(wc_row.get("fdd_view"), "fdd_view", key),
            normality=_normality(wc_row.get("normality"), key),
            review_status=review_status,
            reason=_first_text(scope_row, mapping_row, wc_row, field="reason"),
            source_code=source_code,
            entity=entity,
        )
    return JudgmentStore(result)


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _index_rows(rows: list[dict[str, str]], filename: str) -> dict[JudgmentKey, dict[str, str]]:
    result: dict[JudgmentKey, dict[str, str]] = {}
    for row in rows:
        if not row.get("source_label"):
            continue
        key = judgment_key(row.get("source_label", ""), row.get("source_code"), row.get("entity"))
        if key in result:
            raise JudgmentError(f"Duplicate judgment key in {filename}: {key}")
        result[key] = row
    return result


def _wc_view(value: str | None, field: str, key: JudgmentKey) -> str | None:
    text = _normalize(value)
    if not text:
        return None
    if text not in VALID_WC_VIEWS:
        raise JudgmentError(f"Invalid {field} {value!r} for {key!r}")
    return text


def _normality(value: str | None, key: JudgmentKey) -> str | None:
    text = _normalize(value)
    if not text:
        return None
    if text not in VALID_NORMALITY:
        raise JudgmentError(f"Invalid normality {value!r} for {key!r}")
    return text


def _first_text(*rows: dict[str, str], field: str) -> str | None:
    for row in rows:
        value = _optional(row.get(field))
        if value:
            return value
    return None


def _optional(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize(value: str | None) -> str:
    return normalize_label(value or "")
