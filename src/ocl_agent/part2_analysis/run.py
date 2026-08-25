"""Part 2 - Python metrics plus formula-linked Excel analysis layer.

Python computes analytical numbers independently from the reconciled Part 1
model.  Excel analysis tabs then point back to the formula-driven foundation
schedules so a reviewer can trace every displayed figure.  Narrative text is
kept evidence-led; an AI host may improve the explanation but must never alter
calculated amounts or materiality decisions.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from openpyxl import load_workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from ocl_agent.part1_databook.input_contract import StandardizedPackage
from ocl_agent.part1_databook.semantic_handoff import SemanticHandoff
from ocl_agent.part2_analysis.context import enrich_with_context, load_context
from ocl_agent.part2_analysis.diagnostics import diagnostic_findings
from ocl_agent.part2_analysis.engine import (
    DATABOOK_PERCENT_THRESHOLD,
    analyse_records,
)
from ocl_agent.schemas import AnalysisResult, Finding, OCLRecord


ANALYSIS_SHEETS = ("Analysis Summary", "Seasonality", "Item Monthly Charts", "Deal Issues", "Key Findings")


def run_analysis(
    records: Iterable[OCLRecord],
    databook_path: Path,
    *,
    package: StandardizedPackage | None = None,
    handoff: SemanticHandoff | None = None,
) -> AnalysisResult:
    rows = tuple(records)
    base = analyse_records(rows)
    extra = diagnostic_findings(rows)
    seen = {item.finding_id for item in base.findings}
    result = AnalysisResult(
        (*base.findings, *(item for item in extra if item.finding_id not in seen)),
        base.tables,
        base.annual_periods,
        base.monthly_periods,
        base.latest_annual_period,
    )
    if package is not None and handoff is not None:
        result = enrich_with_context(result, rows, load_context(package, handoff))
    _embed_analysis(Path(databook_path), result)
    return result


def _embed_analysis(path: Path, result: AnalysisResult) -> None:
    workbook = load_workbook(path)
    for name in ANALYSIS_SHEETS:
        if name in workbook.sheetnames:
            del workbook[name]

    summary = workbook.create_sheet("Analysis Summary")
    _write_formula_linked_annual(summary, workbook)
    _write_formula_linked_monthly_stats(summary, workbook)
    if any(table.key == "context_ratios" for table in result.tables):
        summary.append(["Optional contextual ratios", "Calculated independently by Python for reporting; source-backed financial schedules remain formula-linked."])
        summary.append([])

    if "Monthly Balance" in workbook.sheetnames and workbook["Monthly Balance"].max_column >= 13:
        _write_seasonality(workbook)
        _write_monthly_charts(workbook)

    _write_deal_issues(workbook, result.findings)
    _write_key_findings(workbook, result.findings)

    for name in ANALYSIS_SHEETS:
        if name in workbook.sheetnames:
            _finish_sheet(workbook[name])
    workbook.save(path)


def _write_formula_linked_annual(summary, workbook) -> None:
    if "Balance by Category" not in workbook.sheetnames:
        return
    source = workbook["Balance by Category"]
    summary.append(["Annual OCL balance by category"])
    summary.cell(summary.max_row, 1).font = Font(bold=True)
    periods = [source.cell(1, column).value for column in range(2, source.max_column + 1)]
    add_movement = len(periods) >= 2
    header = ["Category", *periods]
    if add_movement:
        header.extend(["Movement", "Movement %", "Review Flag"])
    summary.append(header)
    prior_col = get_column_letter(source.max_column - 1) if add_movement else None
    latest_col = get_column_letter(source.max_column) if add_movement else None
    for source_row in range(2, source.max_row + 1):
        values = [f"='Balance by Category'!A{source_row}"]
        values.extend(f"='Balance by Category'!{get_column_letter(column)}{source_row}" for column in range(2, source.max_column + 1))
        if add_movement and prior_col and latest_col:
            target_row = summary.max_row + 1
            movement_col = get_column_letter(len(header) - 2)
            pct_col = get_column_letter(len(header) - 1)
            values.extend([
                f"='Balance by Category'!{latest_col}{source_row}-'Balance by Category'!{prior_col}{source_row}",
                f"=IFERROR({movement_col}{target_row}/ABS('Balance by Category'!{prior_col}{source_row}),\"\")",
                f'=IF(OR(ABS({movement_col}{target_row})>=100000,ABS({pct_col}{target_row})>={DATABOOK_PERCENT_THRESHOLD/100}),"REVIEW","")',
            ])
        summary.append(values)
    summary.append([])


def _write_formula_linked_monthly_stats(summary, workbook) -> None:
    if "Monthly Balance" not in workbook.sheetnames:
        return
    source = workbook["Monthly Balance"]
    if source.max_column < 2:
        return
    summary.append(["Monthly OCL statistics by category"])
    summary.cell(summary.max_row, 1).font = Font(bold=True)
    summary.append(["Category", "Average", "Minimum", "Maximum", "Std_Dev", "Latest"])
    last_column = get_column_letter(source.max_column)
    for source_row in range(2, source.max_row + 1):
        label = source.cell(source_row, 1).value
        if label in (None, ""):
            continue
        summary.append([
            f"='Monthly Balance'!A{source_row}",
            f"=AVERAGE('Monthly Balance'!B{source_row}:{last_column}{source_row})",
            f"=MIN('Monthly Balance'!B{source_row}:{last_column}{source_row})",
            f"=MAX('Monthly Balance'!B{source_row}:{last_column}{source_row})",
            f"=STDEV.P('Monthly Balance'!B{source_row}:{last_column}{source_row})",
            f"='Monthly Balance'!{last_column}{source_row}",
        ])
    summary.append([])


def _write_seasonality(workbook) -> None:
    source = workbook["Monthly Balance"]
    sheet = workbook.create_sheet("Seasonality")
    start_col = source.max_column - 11
    start_letter = get_column_letter(start_col)
    end_letter = get_column_letter(source.max_column)
    sheet.append(["Category", "12M Average", "Year End", "Deviation", "Deviation %", "Peak Period", "Peak", "Flag"])
    for source_row in range(2, source.max_row + 1):
        if source.cell(source_row, 1).value in (None, ""):
            continue
        row = sheet.max_row + 1
        data_range = f"'Monthly Balance'!{start_letter}{source_row}:{end_letter}{source_row}"
        header_range = f"'Monthly Balance'!{start_letter}$1:{end_letter}$1"
        sheet.append([
            f"='Monthly Balance'!A{source_row}",
            f"=AVERAGE({data_range})",
            f"='Monthly Balance'!{end_letter}{source_row}",
            f"=C{row}-B{row}",
            f'=IFERROR(C{row}/B{row}-1,"")',
            f"=INDEX({header_range},1,MATCH(MAX({data_range}),{data_range},0))",
            f"=MAX({data_range})",
            f'=IF(E{row}>={DATABOOK_PERCENT_THRESHOLD/100},"YEAR-END SPIKE",IF(E{row}<=-{DATABOOK_PERCENT_THRESHOLD/100},"YEAR-END DIP",""))',
        ])


def _write_monthly_charts(workbook) -> None:
    source = workbook["Monthly Balance"]
    sheet = workbook.create_sheet("Item Monthly Charts")
    periods = [source.cell(1, column).value for column in range(2, source.max_column + 1)]
    sheet.append(["Monthly amounts", *periods])
    amount_start = 2
    amount_rows: list[tuple[str, int, int]] = []
    for source_row in range(2, source.max_row + 1):
        label = source.cell(source_row, 1).value
        if label in (None, ""):
            continue
        target = sheet.max_row + 1
        sheet.append([f"='Monthly Balance'!A{source_row}", *[f"='Monthly Balance'!{get_column_letter(column)}{source_row}" for column in range(2, source.max_column + 1)]])
        amount_rows.append((str(label), source_row, target))

    sheet.append([])
    ltm_header_row = sheet.max_row + 1
    sheet.append(["LTM 12-month average", *periods])
    ltm_rows: dict[str, int] = {}
    for label, source_row, _amount_row in amount_rows:
        target = sheet.max_row + 1
        values = [f"='Monthly Balance'!A{source_row}"]
        for period_index, source_col in enumerate(range(2, source.max_column + 1), start=1):
            if period_index < 12:
                values.append("")
            else:
                first = get_column_letter(source_col - 11)
                last = get_column_letter(source_col)
                values.append(f"=AVERAGE('Monthly Balance'!{first}{source_row}:{last}{source_row})")
        sheet.append(values)
        ltm_rows[label] = target

    chart_anchor_row = sheet.max_row + 3
    for index, (label, _source_row, amount_row) in enumerate(amount_rows):
        ltm_row = ltm_rows[label]
        bar = BarChart()
        bar.type = "col"
        bar.height = 7
        bar.width = 16
        bar.title = label
        bar.y_axis.title = "Balance"
        bar.x_axis.title = "Period"
        categories = Reference(sheet, min_col=2, max_col=1 + len(periods), min_row=1)
        amount_data = Reference(sheet, min_col=2, max_col=1 + len(periods), min_row=amount_row, max_row=amount_row)
        bar.add_data(amount_data, from_rows=True)
        bar.set_categories(categories)
        line = LineChart()
        ltm_data = Reference(sheet, min_col=2, max_col=1 + len(periods), min_row=ltm_row, max_row=ltm_row)
        line.add_data(ltm_data, from_rows=True)
        bar += line
        sheet.add_chart(bar, f"A{chart_anchor_row + index * 15}")

    if amount_rows:
        sheet.row_dimensions[ltm_header_row].hidden = False


def _write_deal_issues(workbook, findings: tuple[Finding, ...]) -> None:
    sheet = workbook.create_sheet("Deal Issues")
    sheet.append(["Priority", "Deal Issue", "Formula-backed Figure", "Why It Matters", "Linked Finding"])
    for finding in findings:
        sheet.append([
            finding.priority,
            _deal_issue_title(finding),
            _finding_formula(workbook, finding),
            _so_what(finding),
            finding.finding_id,
        ])


def _write_key_findings(workbook, findings: tuple[Finding, ...]) -> None:
    sheet = workbook.create_sheet("Key Findings")
    sheet.append(["ID", "Area", "Metric", "Periods / Item", "Formula-backed Figure", "Evidence / What Changed", "So What", "Materiality", "Ask Management"])
    for finding in findings:
        sheet.append([
            finding.finding_id,
            _theme_for_finding(finding),
            finding.finding_type,
            ", ".join(finding.evidence_references),
            _finding_formula(workbook, finding),
            finding.text,
            _so_what(finding),
            str(finding.metrics.get("materiality") or "MATERIAL"),
            _ask_management(finding),
        ])


def _finding_formula(workbook, finding: Finding):
    metrics = finding.metrics
    category = metrics.get("category")
    latest = metrics.get("latest_period") or metrics.get("period")
    previous = metrics.get("previous_period")
    if "Balance by Category" in workbook.sheetnames:
        source = workbook["Balance by Category"]
        row = _find_row(source, category if category else "Total OCL")
        latest_col = _find_col(source, latest)
        previous_col = _find_col(source, previous)
        if row and latest_col and previous_col and finding.finding_type in {"TOTAL_CHANGE", "CATEGORY_MOVEMENT"}:
            return f"='Balance by Category'!{get_column_letter(latest_col)}{row}-'Balance by Category'!{get_column_letter(previous_col)}{row}"
        if row and latest_col and finding.finding_type in {"CONCENTRATION"}:
            return f"='Balance by Category'!{get_column_letter(latest_col)}{row}"
    if "Seasonality" in workbook.sheetnames and category and finding.finding_type == "SEASONALITY":
        row = _find_row(workbook["Seasonality"], category)
        if row:
            return f"='Seasonality'!D{row}"
    if "Flat File" in workbook.sheetnames and latest:
        flat = workbook["Flat File"]
        headers = {str(flat.cell(1, column).value): get_column_letter(column) for column in range(1, flat.max_column + 1)}
        amount = headers.get("Amount")
        period = headers.get("Period")
        scope = headers.get("Scope")
        fdd_view = headers.get("FDD_View")
        management_view = headers.get("Management_View")
        normality = headers.get("Normality")
        if amount and period and scope and fdd_view and finding.finding_type == "DEBT_LIKE":
            return f'=SUMIFS(\'Flat File\'!${amount}:${amount},\'Flat File\'!${period}:${period},"{latest}",\'Flat File\'!${scope}:${scope},"IN_SCOPE",\'Flat File\'!${fdd_view}:${fdd_view},"debt_like")'
        if amount and period and scope and fdd_view and management_view and finding.finding_type == "DEBT_LIKE_GAP":
            return f'=SUMIFS(\'Flat File\'!${amount}:${amount},\'Flat File\'!${period}:${period},"{latest}",\'Flat File\'!${scope}:${scope},"IN_SCOPE",\'Flat File\'!${fdd_view}:${fdd_view},"debt_like")-SUMIFS(\'Flat File\'!${amount}:${amount},\'Flat File\'!${period}:${period},"{latest}",\'Flat File\'!${scope}:${scope},"IN_SCOPE",\'Flat File\'!${management_view}:${management_view},"debt_like")'
        if amount and period and scope and normality and finding.finding_type == "ONE_OFF":
            return f'=SUMIFS(\'Flat File\'!${amount}:${amount},\'Flat File\'!${period}:${period},"{latest}",\'Flat File\'!${scope}:${scope},"IN_SCOPE",\'Flat File\'!${normality}:${normality},"one_off")'
    return ""


def _find_row(sheet, value) -> int | None:
    if value in (None, ""):
        return None
    wanted = str(value).strip().casefold()
    for row in range(2, sheet.max_row + 1):
        if str(sheet.cell(row, 1).value or "").strip().casefold() == wanted:
            return row
    return None


def _find_col(sheet, value) -> int | None:
    if value in (None, ""):
        return None
    wanted = str(value).strip().casefold()
    for column in range(1, sheet.max_column + 1):
        if str(sheet.cell(1, column).value or "").strip().casefold() == wanted:
            return column
    return None


def _theme_for_finding(finding: Finding) -> str:
    return {
        "DEBT_LIKE": "Net debt & equity value",
        "DEBT_LIKE_GAP": "Net debt & equity value",
        "ONE_OFF": "Quality of earnings",
        "SEASONALITY": "Seasonality & phasing",
        "MONTHLY_VARIABILITY": "Seasonality & phasing",
        "STALE_BALANCE": "Working capital & balance validity",
        "NEW_ITEM": "Completeness & balance validity",
        "CLIFF": "Quality of earnings",
        "CATEGORY_MOVEMENT": "Balance movements",
        "TOTAL_CHANGE": "Balance movements",
        "CONCENTRATION": "Balance composition",
    }.get(finding.finding_type, "Other OCL matters")


def _deal_issue_title(finding: Finding) -> str:
    return {
        "DEBT_LIKE": "Debt-like items within OCL",
        "DEBT_LIKE_GAP": "FDD vs management debt-like classification gap",
        "ONE_OFF": "One-off / non-recurring OCL items",
        "SEASONALITY": "Year-end balance may not be representative",
        "MONTHLY_VARIABILITY": "Material monthly volatility",
        "STALE_BALANCE": "Potential stale accrual",
        "NEW_ITEM": "New closing obligation",
        "CLIFF": "Balance released or settled to nil",
    }.get(finding.finding_type, finding.title)


def _so_what(finding: Finding) -> str:
    return {
        "DEBT_LIKE": "Could affect net debt / equity value depending on the agreed transaction definition; factual settlement profile should be evidenced.",
        "DEBT_LIKE_GAP": "The difference between management and FDD treatment is a potential deal-value reconciliation item.",
        "ONE_OFF": "May not represent the recurring level of operating liabilities and should be considered when assessing normalized working capital.",
        "SEASONALITY": "A year-end working-capital peg based only on the closing month may not represent the normal in-year level.",
        "MONTHLY_VARIABILITY": "A single balance-sheet date may not represent the underlying run-rate and phasing should be understood.",
        "STALE_BALANCE": "An unchanged liability may indicate a genuinely long-dated obligation or an accrual requiring reassessment.",
        "NEW_ITEM": "The obligation is new versus the prior period and its origin and expected settlement should be understood.",
        "CLIFF": "The reduction to nil may reflect settlement, release or reversal and can affect recurring earnings / working-capital interpretation.",
        "CATEGORY_MOVEMENT": "The movement is sufficiently large to warrant understanding the operational or accounting driver.",
        "TOTAL_CHANGE": "The overall OCL movement is material and should be reconciled to the principal category-level drivers.",
        "CONCENTRATION": "A large share of OCL sits in one category, increasing the importance of understanding its composition and settlement timing.",
    }.get(finding.finding_type, "The item is material to the OCL analysis and requires evidence-led interpretation.")


def _ask_management(finding: Finding) -> str:
    metrics = finding.metrics
    if finding.finding_type == "DEBT_LIKE_GAP":
        return "Please explain the factual basis for the difference between management's and the FDD debt-like classification, including expected settlement timing."
    if finding.finding_type == "SEASONALITY":
        return f"Please explain the operational reason the {metrics.get('category')} year-end balance differs materially from its trailing 12-month average."
    if finding.finding_type == "STALE_BALANCE":
        return f"Please confirm whether the unchanged {metrics.get('source_label')} balance remains a valid outstanding obligation and when it is expected to settle."
    if finding.finding_type == "NEW_ITEM":
        return f"Please explain the event or calculation that gave rise to the new {metrics.get('source_label')} balance."
    if finding.finding_type == "CLIFF":
        return f"Please explain whether the prior {metrics.get('source_label')} balance was settled, released or reversed and the basis for that treatment."
    if finding.finding_type == "CATEGORY_MOVEMENT":
        return f"Please explain the principal driver of the movement in {metrics.get('category')} and whether the closing level is expected to recur."
    if finding.finding_type == "TOTAL_CHANGE":
        return "Please explain the principal operational or accounting drivers of the overall OCL movement."
    if finding.finding_type == "DEBT_LIKE":
        return "Please describe the underlying obligations and expected settlement dates for the items identified as debt-like in the FDD review."
    if finding.finding_type == "ONE_OFF":
        return "Please explain the specific events giving rise to the items identified as one-off / non-recurring."
    if finding.finding_type == "CONCENTRATION":
        return f"Please explain the principal components and settlement profile of {metrics.get('category')}."
    if finding.finding_type == "MONTHLY_VARIABILITY":
        return f"Please explain the primary operational driver of the monthly volatility in {metrics.get('category')}."
    return "Please explain the underlying driver and expected settlement profile of this item."


def _finish_sheet(sheet) -> None:
    sheet.sheet_view.showGridLines = False
    sheet.freeze_panes = "A2"
    if sheet.max_row:
        for cell in sheet[1]:
            cell.font = Font(bold=True)
    for column in range(1, sheet.max_column + 1):
        width = min(65, max(12, max(len(str(sheet.cell(row, column).value or "")) for row in range(1, min(sheet.max_row, 150) + 1)) + 2))
        sheet.column_dimensions[get_column_letter(column)].width = width
