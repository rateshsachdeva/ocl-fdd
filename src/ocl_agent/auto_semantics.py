"""Deterministic bridge from the standardized publication into OCL roles.

The integrated data-preparation path emits canonical dataset names and field
names. When that canonical contract is present, Python can carry the already
established meaning into OCL without asking AI to reinterpret the same data a
second time. Non-canonical publications deliberately fall back to the explicit
semantic-review path.
"""
from __future__ import annotations

import csv
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path


_REQUIRED_RECORD_FIELDS = {
    "source_record_id": "Source_Record_ID",
    "period": "Period",
    "amount": "Amount",
    "source_label": "Source_Label",
}
_OPTIONAL_RECORD_FIELDS = {
    "source_code": "Source_Code",
    "item_identifier": "Item_ID",
    "entity": "Entity",
    "currency": "Currency",
    "movement_multiplier": "Movement_Multiplier",
}


def ensure_semantic_handoff(data_prep_output: Path, config_dir: Path) -> Path | None:
    """Create a confirmed handoff only when the canonical publication proves it.

    Returns ``None`` when the standardized package does not expose the canonical
    OCL record contract. In that case the caller keeps the existing explicit AI
    semantic-review checkpoint rather than guessing from arbitrary names.
    """
    data_prep_output = Path(data_prep_output)
    config_dir = Path(config_dir)
    config_dir.mkdir(parents=True, exist_ok=True)
    target = config_dir / "semantic_handoff.json"

    metadata = _read_json(data_prep_output / "databook_metadata.json")
    manifest = _read_json(data_prep_output / "execution_manifest.json")
    package_id = str(metadata.get("workflow_run_id") or manifest.get("execution_id") or data_prep_output.name)

    if target.exists():
        existing = _read_json(target)
        if str(existing.get("package_id")) == package_id and str(existing.get("status", "")).upper() == "CONFIRMED":
            return target

    datasets: list[dict[str, object]] = []

    def add_record(file: str, usage: str, *, movement: bool = False) -> None:
        path = data_prep_output / file
        headers = _headers(path)
        required = dict(_REQUIRED_RECORD_FIELDS)
        if movement:
            required["movement_type"] = "Movement_Type"
            required["movement_multiplier"] = "Movement_Multiplier"
        if not headers or any(column not in headers for column in required.values()):
            return
        fields = dict(required)
        for role, column in _OPTIONAL_RECORD_FIELDS.items():
            if column in headers:
                fields[role] = column
        item: dict[str, object] = {
            "file": file,
            "usages": [usage],
            "fields": fields,
            "dimensions": [],
            "notes": "Canonical integrated data-preparation output; semantics carried forward deterministically.",
        }
        if movement:
            rules = _movement_rules(path)
            if not rules:
                return
            item["movement_rules"] = rules
        datasets.append(item)

    def add_context(file: str, usage: str, amount_candidates: tuple[str, ...]) -> None:
        path = data_prep_output / file
        headers = _headers(path)
        if not headers:
            return
        fields: dict[str, str] = {}
        if "Period" in headers:
            fields["period"] = "Period"
        amount = next((candidate for candidate in amount_candidates if candidate in headers), None)
        if amount:
            fields["amount"] = amount
        datasets.append({
            "file": file,
            "usages": [usage],
            "fields": fields,
            "dimensions": [],
            "notes": "Canonical optional context from integrated data preparation.",
        })

    add_record("ocl_annual.csv", "OCL_RECORDS")
    add_record("ocl_monthly.csv", "MONTHLY_RECORDS")
    add_record("ocl_movements.csv", "MOVEMENT_RECORDS", movement=True)

    tb_path = data_prep_output / "tb_control.csv"
    tb_headers = _headers(tb_path)
    if tb_headers:
        tb_fields: dict[str, str] = {}
        if "Period" in tb_headers:
            tb_fields["period"] = "Period"
        if "Amount" in tb_headers:
            tb_fields["amount"] = "Amount"
        datasets.append({
            "file": "tb_control.csv",
            "usages": ["TB_CONTROL"],
            "fields": tb_fields,
            "dimensions": [],
            "notes": "Canonical control dataset from integrated data preparation.",
        })

    add_context("revenue_context.csv", "REVENUE_CONTEXT", ("Amount", "Revenue"))
    add_context("payroll_context.csv", "PAYROLL_CONTEXT", ("Amount", "Payroll"))
    add_context("expense_context.csv", "EXPENSE_CONTEXT", ("Amount", "Expense"))
    _add_supporting_evidence(data_prep_output, datasets)

    if not any(set(item["usages"]) & {"OCL_RECORDS", "MONTHLY_RECORDS"} for item in datasets):
        return None

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

    controls = _control_bindings(tb_path)
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


def _headers(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        try:
            return {str(value).strip() for value in next(reader) if str(value).strip()}
        except StopIteration:
            return set()


def _movement_rules(path: Path) -> dict[str, dict[str, object]]:
    """Accept only the canonical movement roles published by data preparation."""
    if not path.exists():
        return {}
    rules: dict[str, dict[str, object]] = {}
    for value in _unique_values(path, "Movement_Type"):
        role = value.strip().upper()
        if role not in {"OPENING", "FLOW", "CLOSING"}:
            return {}
        rules[value] = {"role": role, "multiplier": 1}
    return rules


def _control_bindings(path: Path) -> list[dict[str, object]]:
    headers = _headers(path)
    if not path.exists() or not {"Period", "Amount"}.issubset(headers):
        return []
    if not _valid_control_rows(path):
        return []
    if "Control" not in headers:
        return [{
            "control_id": "chk_listing_vs_tb",
            "dataset_file": "tb_control.csv",
            "period_field": "Period",
            "amount_field": "Amount",
            "whole_dataset": True,
        }]
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


def _valid_control_rows(path: Path) -> bool:
    """Require a business period and numeric amount before auto-binding a control."""
    found = False
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            period = str(row.get("Period", "") or "").strip()
            raw_amount = str(row.get("Amount", "") or "").strip().replace(",", "")
            if not period or _year_of(period) is None or not raw_amount:
                return False
            try:
                Decimal(raw_amount)
            except InvalidOperation:
                return False
            found = True
    return found


def _add_supporting_evidence(data_prep_output: Path, datasets: list[dict[str, object]]) -> None:
    already_bound = {str(item.get("file")) for item in datasets}
    for path in sorted(Path(data_prep_output).glob("*.csv")):
        if path.name in already_bound or path.name in {"lineage.csv", "field_lineage.csv", "exclusions.csv", "processing_issues.csv"}:
            continue
        headers = _headers(path)
        if not headers or "Source_Record_ID" not in headers:
            continue
        fields: dict[str, str] = {"source_record_id": "Source_Record_ID"}
        for role, column in (
            ("period", "Period"),
            ("amount", "Amount"),
            ("source_label", "Source_Label"),
            ("source_code", "Source_Code"),
            ("entity", "Entity"),
            ("currency", "Currency"),
        ):
            if column in headers:
                fields[role] = column
        dimensions = sorted(headers - set(fields.values()))
        datasets.append({
            "file": path.name,
            "usages": ["SUPPORTING_EVIDENCE"],
            "fields": fields,
            "dimensions": dimensions,
            "notes": "Lineage-bound standardized supporting evidence; not part of OCL foundation totals.",
        })


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
