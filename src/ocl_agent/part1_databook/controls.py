"""Independent Python controls for the shared OCL data model."""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation

from ocl_agent.part1_databook.input_contract import StandardizedPackage
from ocl_agent.part1_databook.judgment_validation import JudgmentIssue
from ocl_agent.part1_databook.reconciliation import DEFAULT_TOLERANCE, category_sum_control, not_applicable, reconcile_amounts
from ocl_agent.part1_databook.record_builder import RecordBuildResult
from ocl_agent.part1_databook.semantic_handoff import ControlBinding, DatasetUsage, SemanticHandoff
from ocl_agent.schemas import CheckStatus, ControlResult, OCLRecord, Scope


def build_core_controls(records: tuple[OCLRecord, ...], build: RecordBuildResult, handoff: SemanticHandoff, judgment_issues: tuple[JudgmentIssue, ...], package: StandardizedPackage | None = None, *, movement_control: ControlResult | None = None, continuity_control: ControlResult | None = None) -> tuple[ControlResult, ...]:
    controls: list[ControlResult] = [category_sum_control(records)]
    input_rows = sum(build.input_rows_by_dataset.values())
    excluded_rows = sum(build.excluded_rows_by_dataset.values())
    accounted = len(build.records) + len(build.issues) + excluded_rows
    controls.append(reconcile_amounts("chk_record_coverage", Decimal(accounted), Decimal(input_rows), message="Every standardized row read for a record usage becomes an OCL record, a visible build issue, or an explicit usage-filter exclusion."))

    usages = {usage for dataset in handoff.datasets for usage in dataset.usages}
    control_by_id = {item.control_id: item for item in handoff.controls}
    listing_binding = control_by_id.get("chk_listing_vs_tb")
    if listing_binding and package:
        controls.append(_source_control(records, package, listing_binding, scopes={Scope.IN_SCOPE}))
    elif DatasetUsage.TB_CONTROL in usages:
        controls.append(ControlResult("chk_listing_vs_tb", CheckStatus.REVIEW_REQUIRED, message="TB control data exists but the exact OCL control row/filter has not been explicitly bound."))
    else:
        controls.append(not_applicable("chk_listing_vs_tb", "No explicit TB control dataset is available in the standardized package."))

    scope_binding = control_by_id.get("chk_scope_reconciles")
    if scope_binding and package:
        controls.append(_source_control(records, package, scope_binding, scopes={Scope.IN_SCOPE, Scope.TRADE_PAYABLE, Scope.FINANCING}))
    else:
        unresolved_scope = sum(1 for row in records if row.judgment.scope == Scope.REVIEW_REQUIRED)
        controls.append(reconcile_amounts("chk_scope_reconciles", Decimal(unresolved_scope), Decimal(0), message="All candidate rows have an explicit scope. A source-backed current-liabilities control may be bound when available."))

    wc_missing = sum(1 for row in records if row.judgment.scope == Scope.IN_SCOPE and (not row.judgment.management_view or not row.judgment.fdd_view))
    controls.append(reconcile_amounts("chk_wcdebt_exhaustive", Decimal(wc_missing), Decimal(0), message="Every in-scope OCL record requires management and FDD WC/debt-like treatment."))

    if movement_control is not None:
        controls.append(movement_control)
    elif DatasetUsage.MOVEMENT_RECORDS in usages:
        controls.append(ControlResult("chk_rollforward", CheckStatus.REVIEW_REQUIRED, message="Movement data is present but explicit movement rules/alignment were not supplied."))
    else:
        controls.append(not_applicable("chk_rollforward", "No movement dataset is available."))

    controls.append(continuity_control or not_applicable("chk_continuity", "Period continuity requires an explicit expected period sequence; labels are not guessed."))
    controls.append(_monthly_to_annual_control(records, handoff, usages))

    if build.issues:
        controls.append(ControlResult("chk_semantic_build", CheckStatus.FAIL, Decimal(len(build.issues)), Decimal(0), Decimal(len(build.issues)), message="Invalid/blank required standardized values remain unresolved."))
    else:
        controls.append(reconcile_amounts("chk_semantic_build", Decimal(0), Decimal(0), message="No semantic record-build issues."))
    if judgment_issues:
        controls.append(ControlResult("chk_judgment_completion", CheckStatus.FAIL, Decimal(len(judgment_issues)), Decimal(0), Decimal(len(judgment_issues)), message="Required OCL judgments are incomplete or not reviewed."))
    else:
        controls.append(reconcile_amounts("chk_judgment_completion", Decimal(0), Decimal(0), message="Required OCL judgments are complete and reviewed."))
    return tuple(controls)


def _source_control(records: tuple[OCLRecord, ...], package: StandardizedPackage, binding: ControlBinding, *, scopes: set[Scope]) -> ControlResult:
    expected_by_period: dict[str, Decimal] = {}
    evidence_rows: list[dict[str, object]] = []
    path = package.root / binding.dataset_file
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            for csv_row, row in enumerate(reader, start=2):
                if not binding.whole_dataset and not _matches_filters(row, binding.filters):
                    continue
                period = str(row.get(binding.period_field, "") or "").strip()
                raw_amount = str(row.get(binding.amount_field, "") or "").strip()
                if not period or not raw_amount:
                    return ControlResult(binding.control_id, CheckStatus.FAIL, message=f"Bound control row {binding.dataset_file}:{csv_row} has blank period/amount.")
                try:
                    amount = Decimal(raw_amount.replace(",", ""))
                except InvalidOperation:
                    return ControlResult(binding.control_id, CheckStatus.FAIL, message=f"Bound control amount is not numeric at {binding.dataset_file}:{csv_row}.")
                expected_by_period[period] = expected_by_period.get(period, Decimal("0")) + amount
                evidence_rows.append({"dataset": binding.dataset_file, "csv_row": csv_row, "period": period})
    except OSError as error:
        return ControlResult(binding.control_id, CheckStatus.FAIL, message=f"Unable to read bound control dataset: {error}")
    if not evidence_rows:
        return ControlResult(binding.control_id, CheckStatus.FAIL, message="Explicit control filter matched no standardized source rows.", evidence={"filters": binding.filters, "dataset": binding.dataset_file})
    actual_by_period: dict[str, Decimal] = {}
    for row in records:
        if row.dimensions.get("record_usage") == DatasetUsage.MONTHLY_RECORDS.value:
            continue
        if row.judgment.scope in scopes:
            actual_by_period[row.period] = actual_by_period.get(row.period, Decimal("0")) + row.amount
    periods = sorted(set(actual_by_period) | set(expected_by_period))
    mismatches: list[dict[str, str]] = []
    for period in periods:
        actual = actual_by_period.get(period, Decimal("0"))
        expected = expected_by_period.get(period, Decimal("0"))
        difference = actual - expected
        if abs(difference) >= DEFAULT_TOLERANCE:
            mismatches.append({"period": period, "actual": str(actual), "expected": str(expected), "difference": str(difference)})
    total_actual = sum(actual_by_period.values(), Decimal("0"))
    total_expected = sum(expected_by_period.values(), Decimal("0"))
    return ControlResult(binding.control_id, CheckStatus.PASS if not mismatches else CheckStatus.FAIL, total_actual, total_expected, total_actual - total_expected, message="Source-backed control reconciled by exact period and explicit filter." if not mismatches else "Source-backed control has period-level breaks.", evidence={"matched_source_rows": evidence_rows[:100], "mismatches": mismatches[:100]})


def _matches_filters(row: dict[str, str], filters: dict[str, tuple[str, ...]]) -> bool:
    for column, allowed in filters.items():
        value = str(row.get(column, "") or "").strip().casefold()
        if value not in {str(item).strip().casefold() for item in allowed}:
            return False
    return True


def _monthly_to_annual_control(records: tuple[OCLRecord, ...], handoff: SemanticHandoff, usages: set[DatasetUsage]) -> ControlResult:
    if DatasetUsage.MONTHLY_RECORDS not in usages or DatasetUsage.OCL_RECORDS not in usages:
        return not_applicable("chk_monthly_to_annual", "Both monthly and annual OCL records are required.")
    if not handoff.monthly_to_annual:
        return ControlResult("chk_monthly_to_annual", CheckStatus.REVIEW_REQUIRED, message="Monthly and annual records exist; year-end period alignment must be explicitly confirmed.")
    mismatches = _monthly_to_annual_mismatches(records, handoff)
    return ControlResult("chk_monthly_to_annual", CheckStatus.PASS if not mismatches else CheckStatus.FAIL, Decimal(len(mismatches)), Decimal(0), Decimal(len(mismatches)), message="Confirmed monthly year-end balances must equal annual closing balances by mapped OCL category.", evidence={"mismatches": mismatches[:100]})


def _monthly_to_annual_mismatches(records: tuple[OCLRecord, ...], handoff: SemanticHandoff) -> list[dict[str, str]]:
    annual: dict[tuple[str, str], Decimal] = {}
    monthly: dict[tuple[str, str], Decimal] = {}
    for row in records:
        if row.judgment.scope != Scope.IN_SCOPE or not row.judgment.category:
            continue
        key = (row.period, row.judgment.category)
        target = monthly if row.dimensions.get("record_usage") == DatasetUsage.MONTHLY_RECORDS.value else annual
        target[key] = target.get(key, Decimal("0")) + row.amount
    mismatches: list[dict[str, str]] = []
    for alignment in handoff.monthly_to_annual:
        categories = {category for period, category in annual if period == alignment.annual_period} | {category for period, category in monthly if period == alignment.monthly_period}
        for category in sorted(categories):
            annual_value = annual.get((alignment.annual_period, category), Decimal("0"))
            monthly_value = monthly.get((alignment.monthly_period, category), Decimal("0"))
            difference = monthly_value - annual_value
            if abs(difference) >= DEFAULT_TOLERANCE:
                mismatches.append({"annual_period": alignment.annual_period, "monthly_period": alignment.monthly_period, "category": category, "annual": str(annual_value), "monthly": str(monthly_value), "difference": str(difference)})
    return mismatches
