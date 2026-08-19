"""Explicit movement support for OCL roll-forward schedules.

Movement arithmetic is never guessed.  The package-specific semantic handoff may
include a `movement_rules` object on a MOVEMENT_RECORDS dataset.  Each exact
source movement value maps to a role and multiplier, for example:

    "movement_rules": {
      "Opening": {"role": "OPENING", "multiplier": 1},
      "Additions": {"role": "FLOW", "multiplier": 1},
      "Utilisation": {"role": "FLOW", "multiplier": -1},
      "Closing": {"role": "CLOSING", "multiplier": 1}
    }

The top-level `movement_to_annual` list explicitly aligns each movement period to
an annual/listing period.  Without those reviewed rules, movement data remains a
visible review requirement rather than being interpreted heuristically.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from ocl_agent.part1_databook.input_contract import StandardizedPackage
from ocl_agent.part1_databook.judgments import JudgmentStore
from ocl_agent.part1_databook.reconciliation import DEFAULT_TOLERANCE
from ocl_agent.part1_databook.semantic_handoff import DatasetUsage, SemanticHandoff
from ocl_agent.schemas import CheckStatus, ControlResult, MovementRecord, OCLRecord, ReviewStatus, Scope, SourceReference

ALLOWED_ROLES = {"OPENING", "FLOW", "CLOSING"}


@dataclass(frozen=True)
class MovementAlignment:
    movement_period: str
    annual_period: str


@dataclass(frozen=True)
class MovementBuildResult:
    records: tuple[MovementRecord, ...]
    issues: tuple[str, ...]
    alignments: tuple[MovementAlignment, ...]


def build_movements(package: StandardizedPackage, handoff: SemanticHandoff, judgments: JudgmentStore, handoff_path: Path) -> MovementBuildResult:
    movement_bindings = [binding for binding in handoff.datasets if DatasetUsage.MOVEMENT_RECORDS in binding.usages]
    if not movement_bindings:
        return MovementBuildResult((), (), ())
    payload = json.loads(Path(handoff_path).read_text(encoding="utf-8"))
    raw_datasets = {str(item.get("file")): item for item in payload.get("datasets", []) if isinstance(item, dict)}
    alignments = tuple(
        MovementAlignment(str(item.get("movement_period", "")).strip(), str(item.get("annual_period", "")).strip())
        for item in payload.get("movement_to_annual", []) if isinstance(item, dict)
    )
    issues: list[str] = []
    records: list[MovementRecord] = []
    for binding in movement_bindings:
        item = raw_datasets.get(binding.file, {})
        rules = item.get("movement_rules") or {}
        if not isinstance(rules, dict) or not rules:
            issues.append(f"{binding.file}: movement_rules are missing.")
            continue
        normalized_rules: dict[str, tuple[str, Decimal]] = {}
        for source_value, rule in rules.items():
            if isinstance(rule, str):
                role = rule.strip().upper()
                multiplier = Decimal("1")
            elif isinstance(rule, dict):
                role = str(rule.get("role", "")).strip().upper()
                try:
                    multiplier = Decimal(str(rule.get("multiplier", "1")))
                except InvalidOperation:
                    issues.append(f"{binding.file}: invalid multiplier for movement value {source_value!r}.")
                    continue
            else:
                issues.append(f"{binding.file}: invalid movement rule for {source_value!r}.")
                continue
            if role not in ALLOWED_ROLES:
                issues.append(f"{binding.file}: unsupported movement role {role!r} for {source_value!r}.")
                continue
            normalized_rules[str(source_value).strip().casefold()] = (role, multiplier)
        fields = binding.fields
        assert fields.source_record_id and fields.period and fields.amount and fields.source_label and fields.movement_type
        with (package.root / binding.file).open(newline="", encoding="utf-8-sig") as handle:
            for csv_row, row in enumerate(csv.DictReader(handle), start=2):
                raw_type = str(row.get(fields.movement_type, "") or "").strip()
                rule = normalized_rules.get(raw_type.casefold())
                if rule is None:
                    issues.append(f"{binding.file}:{csv_row}: movement type {raw_type!r} is not explicitly mapped.")
                    continue
                source_record_id = str(row.get(fields.source_record_id, "") or "").strip()
                period = str(row.get(fields.period, "") or "").strip()
                label = str(row.get(fields.source_label, "") or "").strip()
                try:
                    amount = Decimal(str(row.get(fields.amount, "") or "").strip().replace(",", ""))
                except InvalidOperation:
                    issues.append(f"{binding.file}:{csv_row}: movement amount is not numeric.")
                    continue
                source_code = str(row.get(fields.source_code, "") or "").strip() if fields.source_code else None
                entity = str(row.get(fields.entity, "") or "").strip() if fields.entity else None
                judgment = judgments.get(label, source_code, entity)
                if judgment.scope == Scope.REVIEW_REQUIRED or judgment.review_status != ReviewStatus.REVIEWED:
                    issues.append(f"{binding.file}:{csv_row}: movement label {label!r} does not have reviewed OCL judgment.")
                    continue
                role, multiplier = rule
                dimensions = {"dataset_file": binding.file, "standardized_csv_row": csv_row, "source_code": source_code, "entity": entity, "raw_movement_type": raw_type}
                records.append(MovementRecord(SourceReference(source_record_id), period, amount, label, role, multiplier, judgment, dimensions))
    if movement_bindings and not alignments:
        issues.append("movement_to_annual alignment is missing.")
    if any(not item.movement_period or not item.annual_period for item in alignments):
        issues.append("movement_to_annual contains blank period values.")
    return MovementBuildResult(tuple(records), tuple(issues), alignments)


def rollforward_control(movements: tuple[MovementRecord, ...], annual_records: tuple[OCLRecord, ...], alignments: tuple[MovementAlignment, ...], issues: tuple[str, ...]) -> ControlResult:
    if not movements and not issues:
        return ControlResult("chk_rollforward", CheckStatus.NOT_APPLICABLE, message="No movement dataset is available.")
    if issues:
        return ControlResult("chk_rollforward", CheckStatus.REVIEW_REQUIRED, message="Movement data requires explicit reviewed rules/alignment before roll-forward publication.", evidence={"issues": list(issues)[:100]})
    grouped: dict[tuple[str, str], dict[str, Decimal]] = {}
    for row in movements:
        if row.judgment.scope != Scope.IN_SCOPE or not row.judgment.category:
            continue
        bucket = grouped.setdefault((row.period, row.judgment.category), {"OPENING": Decimal("0"), "FLOW": Decimal("0"), "CLOSING": Decimal("0")})
        if row.movement_role == "FLOW":
            bucket["FLOW"] += row.signed_amount
        else:
            bucket[row.movement_role] += row.amount * row.multiplier
    breaks: list[dict[str, str]] = []
    for (period, category), values in sorted(grouped.items()):
        expected_closing = values["OPENING"] + values["FLOW"]
        difference = expected_closing - values["CLOSING"]
        if abs(difference) >= DEFAULT_TOLERANCE:
            breaks.append({"type": "ROLLFORWARD", "period": period, "category": category, "opening": str(values["OPENING"]), "flow": str(values["FLOW"]), "closing": str(values["CLOSING"]), "difference": str(difference)})
    annual: dict[tuple[str, str], Decimal] = {}
    for row in annual_records:
        if row.dimensions.get("record_usage") == "MONTHLY_RECORDS" or row.judgment.scope != Scope.IN_SCOPE or not row.judgment.category:
            continue
        annual[(row.period, row.judgment.category)] = annual.get((row.period, row.judgment.category), Decimal("0")) + row.amount
    for alignment in alignments:
        categories = {category for period, category in grouped if period == alignment.movement_period}
        for category in sorted(categories):
            closing = grouped[(alignment.movement_period, category)]["CLOSING"]
            listing = annual.get((alignment.annual_period, category), Decimal("0"))
            difference = closing - listing
            if abs(difference) >= DEFAULT_TOLERANCE:
                breaks.append({"type": "CLOSING_TO_LISTING", "movement_period": alignment.movement_period, "annual_period": alignment.annual_period, "category": category, "closing": str(closing), "listing": str(listing), "difference": str(difference)})
    return ControlResult("chk_rollforward", CheckStatus.PASS if not breaks else CheckStatus.FAIL, Decimal(len(breaks)), Decimal("0"), Decimal(len(breaks)), message="Explicit movement roll-forward and closing-to-listing reconciliation." if not breaks else "Movement roll-forward contains reconciliation breaks.", evidence={"breaks": breaks[:100]})


def embed_rollforward(databook_path: Path, movements: tuple[MovementRecord, ...]) -> None:
    if not movements:
        return
    workbook = load_workbook(databook_path)
    if "Roll-forward" in workbook.sheetnames:
        del workbook["Roll-forward"]
    sheet = workbook.create_sheet("Roll-forward")
    periods = sorted({row.period for row in movements})
    categories = sorted({str(row.judgment.category) for row in movements if row.judgment.scope == Scope.IN_SCOPE and row.judgment.category})
    sheet.append(["Category", "Period", "Opening", "Net movement", "Closing", "Calculated closing", "Difference"])
    grouped: dict[tuple[str, str], dict[str, Decimal]] = {}
    for row in movements:
        if row.judgment.scope != Scope.IN_SCOPE or not row.judgment.category:
            continue
        bucket = grouped.setdefault((row.period, str(row.judgment.category)), {"OPENING": Decimal("0"), "FLOW": Decimal("0"), "CLOSING": Decimal("0")})
        if row.movement_role == "FLOW":
            bucket["FLOW"] += row.signed_amount
        else:
            bucket[row.movement_role] += row.amount * row.multiplier
    for period in periods:
        for category in categories:
            if (period, category) not in grouped:
                continue
            values = grouped[(period, category)]
            sheet.append([category, period, values["OPENING"], values["FLOW"], values["CLOSING"], f"=C{sheet.max_row + 1}+D{sheet.max_row + 1}", f"=F{sheet.max_row + 1}-E{sheet.max_row + 1}"])
    sheet.freeze_panes = "A2"
    sheet.sheet_view.showGridLines = False
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for column in range(1, sheet.max_column + 1):
        sheet.column_dimensions[get_column_letter(column)].width = 18
    workbook.save(databook_path)
