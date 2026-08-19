"""Autonomous, reviewable OCL judgment defaults for the one-command workflow.

The objective is to let a complete skill run finish without forcing the user to
maintain config files before first use. Existing human-reviewed rows always win.
Autonomous rows carry package provenance and are refreshed when the source
package changes so stale engagement judgments cannot silently leak forward.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ORIGIN = "INTEGRATED_AUTONOMOUS"
SCOPE_HEADERS = ["source_label", "source_code", "entity", "scope", "review_status", "reason", "decision_origin", "package_id"]
MAPPING_HEADERS = ["source_label", "source_code", "entity", "category", "parent_category", "review_status", "reason", "decision_origin", "package_id"]
WC_HEADERS = ["source_label", "source_code", "entity", "management_view", "fdd_view", "normality", "review_status", "reason", "decision_origin", "package_id"]

TRADE_PAYABLE_TERMS = (
    "trade payable", "trade creditor", "accounts payable", "account payable", "supplier payable", "vendor payable",
)
FINANCING_TERMS = (
    "bank loan", "loan payable", "borrowings", "borrowing", "overdraft", "revolver", "revolving credit",
    "current debt", "short term debt", "short-term debt", "finance lease", "lease liability",
)
EMPLOYEE_TERMS = (
    "bonus", "holiday", "vacation", "payroll", "wage", "salary", "commission", "employee", "personnel",
    "social security", "pension", "benefit",
)
TAX_TERMS = ("vat", "gst", "sales tax", "payroll tax", "income tax", "withholding tax", "statutory")
PROFESSIONAL_TERMS = ("professional fee", "legal fee", "audit fee", "consulting fee", "advisory fee")
OCCUPANCY_TERMS = ("rent accrual", "accrued rent", "utilities", "utility accrual")


def ensure_autonomous_judgments(data_prep_output: Path, config_dir: Path) -> dict[str, int]:
    data_prep_output = Path(data_prep_output)
    config_dir = Path(config_dir)
    config_dir.mkdir(parents=True, exist_ok=True)
    package_id = _package_id(data_prep_output)
    keys = _source_keys(data_prep_output)

    # Preserve human rows and same-package autonomous rows; discard stale
    # autonomous defaults from prior source packages.
    scope_rows = _retain(_read(config_dir / "judgment_scope.csv"), package_id)
    mapping_rows = _retain(_read(config_dir / "mapping.csv"), package_id)
    wc_rows = _retain(_read(config_dir / "judgment_wc_debt.csv"), package_id)
    scope_index = {_key(row): row for row in scope_rows if row.get("source_label")}
    mapping_index = {_key(row): row for row in mapping_rows if row.get("source_label")}
    wc_index = {_key(row): row for row in wc_rows if row.get("source_label")}

    added = {"scope": 0, "mapping": 0, "wc_debt": 0}
    for source_label, source_code, entity in keys:
        key = _key({"source_label": source_label, "source_code": source_code, "entity": entity})
        scope = _scope_for(source_label)
        if key not in scope_index:
            row = {
                "source_label": source_label,
                "source_code": source_code,
                "entity": entity,
                "scope": scope,
                "review_status": "REVIEWED",
                "reason": "Autonomous initial scope based on the current source schedule; visible and overrideable in config/Mapping.",
                "decision_origin": ORIGIN,
                "package_id": package_id,
            }
            scope_rows.append(row)
            scope_index[key] = row
            added["scope"] += 1

        if key not in mapping_index:
            category = source_label if scope == "IN_SCOPE" else ""
            row = {
                "source_label": source_label,
                "source_code": source_code,
                "entity": entity,
                "category": category,
                "parent_category": _parent_for(source_label) if category else "",
                "review_status": "REVIEWED",
                "reason": "Source-present category retained dynamically; no legacy category list imposed.",
                "decision_origin": ORIGIN,
                "package_id": package_id,
            }
            mapping_rows.append(row)
            mapping_index[key] = row
            added["mapping"] += 1

        if key not in wc_index:
            row = {
                "source_label": source_label,
                "source_code": source_code,
                "entity": entity,
                "management_view": "working_capital" if scope == "IN_SCOPE" else "",
                "fdd_view": "working_capital" if scope == "IN_SCOPE" else "",
                "normality": "normal" if scope == "IN_SCOPE" else "",
                "review_status": "REVIEWED",
                "reason": "Conservative autonomous first-pass classification; no debt-like or one-off treatment is invented without direct evidence.",
                "decision_origin": ORIGIN,
                "package_id": package_id,
            }
            wc_rows.append(row)
            wc_index[key] = row
            added["wc_debt"] += 1

    _write(config_dir / "judgment_scope.csv", SCOPE_HEADERS, scope_rows)
    _write(config_dir / "mapping.csv", MAPPING_HEADERS, mapping_rows)
    _write(config_dir / "judgment_wc_debt.csv", WC_HEADERS, wc_rows)
    return added


def _retain(rows: list[dict[str, str]], package_id: str) -> list[dict[str, str]]:
    retained = []
    for row in rows:
        origin = str(row.get("decision_origin", "") or "").strip()
        bound_package = str(row.get("package_id", "") or "").strip()
        if origin == ORIGIN and bound_package and bound_package != package_id:
            continue
        retained.append(row)
    return retained


def _package_id(root: Path) -> str:
    for name, key in (("databook_metadata.json", "workflow_run_id"), ("execution_manifest.json", "execution_id")):
        path = root / name
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and payload.get(key):
                return str(payload[key])
    return root.name


def _source_keys(root: Path) -> list[tuple[str, str, str]]:
    result: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for name in ("ocl_annual.csv", "ocl_monthly.csv"):
        path = root / name
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                label = str(row.get("Source_Label", "") or "").strip()
                if not label:
                    continue
                item = (label, str(row.get("Source_Code", "") or "").strip(), str(row.get("Entity", "") or "").strip())
                normalized = tuple(part.casefold() for part in item)
                if normalized in seen:
                    continue
                seen.add(normalized)
                result.append(item)
    return result


def _scope_for(label: str) -> str:
    text = _norm(label)
    if any(term in text for term in TRADE_PAYABLE_TERMS):
        return "TRADE_PAYABLE"
    if any(term in text for term in FINANCING_TERMS):
        return "FINANCING"
    return "IN_SCOPE"


def _parent_for(label: str) -> str:
    text = _norm(label)
    if any(term in text for term in EMPLOYEE_TERMS):
        return "Employee-related accruals"
    if any(term in text for term in TAX_TERMS):
        return "Taxes and statutory liabilities"
    if any(term in text for term in PROFESSIONAL_TERMS):
        return "Professional fees"
    if any(term in text for term in OCCUPANCY_TERMS):
        return "Occupancy and utilities"
    return ""


def _norm(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).split())


def _key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        _norm(row.get("entity", "")),
        _norm(row.get("source_code", "")),
        _norm(row.get("source_label", "")),
    )


def _read(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _write(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
