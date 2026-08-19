"""Deterministic bridge from the embedded standardized publication into OCL roles.

The embedded data-preparation fast path emits canonical dataset names and field
names. That gives enough direct evidence to create an OCL semantic handoff
without guessing from arbitrary client headings a second time.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path


def ensure_semantic_handoff(data_prep_output: Path, config_dir: Path) -> Path:
    data_prep_output = Path(data_prep_output)
    config_dir = Path(config_dir)
    config_dir.mkdir(parents=True, exist_ok=True)
    target = config_dir / "semantic_handoff.json"

    metadata = _read_json(data_prep_output / "databook_metadata.json")
    manifest = _read_json(data_prep_output / "execution_manifest.json")
    package_id = str(metadata.get("workflow_run_id") or manifest.get("execution_id") or data_prep_output.name)

    # A package-specific handoff must never leak into a different source package.
    if target.exists():
        existing = _read_json(target)
        if str(existing.get("package_id")) == package_id and str(existing.get("status", "")).upper() == "CONFIRMED":
            return target

    datasets = []
    available = {path.name for path in data_prep_output.glob("*.csv")}

    def add(file: str, usage: str, fields: dict[str, str], **extra) -> None:
        if file not in available:
            return
        item = {"file": file, "usages": [usage], "fields": fields, "dimensions": [], "notes": "Canonical integrated data-preparation output."}
        item.update(extra)
        datasets.append(item)

    record_fields = {
        "source_record_id": "Source_Record_ID",
        "period": "Period",
        "amount": "Amount",
        "source_label": "Source_Label",
        "source_code": "Source_Code",
        "entity": "Entity",
        "currency": "Currency",
    }
    add("ocl_annual.csv", "OCL_RECORDS", record_fields)
    add("ocl_monthly.csv", "MONTHLY_RECORDS", record_fields)
    movement_fields = dict(record_fields)
    movement_fields["movement_type"] = "Movement_Type"
    movement_rules = _movement_rules(data_prep_output / "ocl_movements.csv")
    add("ocl_movements.csv", "MOVEMENT_RECORDS", movement_fields, movement_rules=movement_rules)
    add("tb_control.csv", "TB_CONTROL", {"period": "Period", "amount": "Amount"})
    add("revenue_context.csv", "REVENUE_CONTEXT", {"period": "Period", "amount": "Amount"})
    add("payroll_context.csv", "PAYROLL_CONTEXT", {"period": "Period", "amount": "Amount"})

    annual_periods = _unique_values(data_prep_output / "ocl_annual.csv", "Period")
    monthly_periods = _unique_values(data_prep_output / "ocl_monthly.csv", "Period")
    movement_periods = _unique_values(data_prep_output / "ocl_movements.csv", "Period")

    monthly_to_annual = []
    for annual in annual_periods:
        year = _year_of(annual)
        candidates = [period for period in monthly_periods if _year_of(period) == year]
        if candidates:
            monthly_to_annual.append({"annual_period": annual, "monthly_period": sorted(candidates, key=_period_sort)[-1]})

    movement_to_annual = []
    for movement in movement_periods:
        year = _year_of(movement)
        candidates = [period for period in annual_periods if _year_of(period) == year]
        if candidates:
            movement_to_annual.append({"movement_period": movement, "annual_period": candidates[-1]})

    controls = _control_bindings(data_prep_output / "tb_control.csv")
    payload = {
        "handoff_version": "1.0",
        "status": "CONFIRMED",
        "package_id": package_id,
        "datasets": datasets,
        "unresolved_matters": [],
        "monthly_to_annual": monthly_to_annual,
        "movement_to_annual": movement_to_annual,
        "controls": controls,
        "confirmed_by": "INTEGRATED_CANONICAL_CONTRACT",
    }
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def _movement_rules(path: Path) -> dict[str, dict[str, object]]:
    if not path.exists():
        return {}
    rules: dict[str, dict[str, object]] = {}
    for value in _unique_values(path, "Movement_Type"):
        normalized = re.sub(r"[^a-z]+", " ", value.casefold()).strip()
        if normalized in {"opening", "opening balance", "brought forward", "beginning balance"}:
            rules[value] = {"role": "OPENING", "multiplier": 1}
        elif normalized in {"closing", "closing balance", "ending balance", "carried forward"}:
            rules[value] = {"role": "CLOSING", "multiplier": 1}
        elif any(token in normalized for token in ("utilis", "usage", "release", "payment", "paid", "settlement", "reversal")):
            rules[value] = {"role": "FLOW", "multiplier": -1}
        else:
            rules[value] = {"role": "FLOW", "multiplier": 1}
    return rules


def _control_bindings(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    values = _unique_values(path, "Control")
    normalized = {value: _norm(value) for value in values}
    controls: list[dict[str, object]] = []
    ocl = next((value for value, text in normalized.items() if text in {"ocl", "other current liabilities", "accrued liabilities", "accruals"}), None)
    if ocl:
        controls.append({
            "control_id": "chk_listing_vs_tb",
            "dataset_file": "tb_control.csv",
            "period_field": "Period",
            "amount_field": "Amount",
            "filters": {"Control": [ocl]},
        })
    current_liabilities = next((value for value, text in normalized.items() if "current liabil" in text and ("trade" in text or "financ" in text or "including" in text)), None)
    if current_liabilities:
        controls.append({
            "control_id": "chk_scope_reconciles",
            "dataset_file": "tb_control.csv",
            "period_field": "Period",
            "amount_field": "Amount",
            "filters": {"Control": [current_liabilities]},
        })
    return controls


def _unique_values(path: Path, field: str) -> list[str]:
    if not path.exists():
        return []
    result: list[str] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            value = str(row.get(field, "") or "").strip()
            if value and value not in result:
                result.append(value)
    return result


def _year_of(value: str) -> int | None:
    text = str(value).upper()
    match = re.search(r"(20\d{2})", text)
    if match:
        return int(match.group(1))
    match = re.search(r"FY\D*(\d{2})$", text)
    if match:
        return 2000 + int(match.group(1))
    return None


def _period_sort(value: str) -> tuple[int, int, str]:
    year = _year_of(value) or 0
    match = re.search(r"(?:20\d{2})[-_/](\d{1,2})", value)
    month = int(match.group(1)) if match else 12
    return year, month, value


def _norm(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).split())


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}
