"""Render validated AI-host narrative into Deal Issues and Key Findings.

All financial figures remain linked to deterministic workbook schedules.  The AI
host supplies only interpretation and wording.
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Font

from ocl_agent.part2_analysis.run import PROJECT_LABEL, _analysis_sheet, _finding_formula, _finish_sheet
from ocl_agent.schemas import AnalysisResult


def apply_partner_interpretation(path: Path, result: AnalysisResult, interpretation: dict) -> Path:
    path = Path(path)
    workbook = load_workbook(path)
    for name in ("Deal Issues", "Key Findings"):
        if name in workbook.sheetnames:
            del workbook[name]

    finding_by_id = {item.finding_id: item for item in result.findings}
    _write_deal_issues(workbook, finding_by_id, interpretation)
    _write_key_findings(workbook, finding_by_id, interpretation)
    _finish_sheet(workbook["Deal Issues"])
    _finish_sheet(workbook["Key Findings"])
    workbook.save(path)
    return path


def _write_deal_issues(workbook, finding_by_id: dict, interpretation: dict) -> None:
    sheet = workbook.create_sheet("Deal Issues")
    sheet["A1"] = PROJECT_LABEL
    sheet["A2"] = "Key deal issues — FDD partner interpretation"
    issues = interpretation.get("deal_issues") or []
    if not issues:
        sheet["A4"] = "No material deal issue identified from the available evidence"
        sheet["A4"].font = Font(bold=True)
        sheet.merge_cells("A5:D5")
        sheet["A5"] = str(interpretation.get("overall_assessment") or "")
        return

    row = 4
    for issue in issues:
        linked = finding_by_id.get(str(issue.get("linked_finding_id") or ""))
        priority = str(issue.get("priority") or "MEDIUM").upper()
        sheet.cell(row, 1, f"{priority} | {issue['title']}")
        sheet.cell(row, 1).font = Font(bold=True)
        sheet.merge_cells(start_row=row + 1, start_column=1, end_row=row + 1, end_column=4)
        sheet.cell(row + 1, 1, issue["so_what"])
        sheet.cell(row + 2, 1, "Figure")
        sheet.cell(row + 2, 2, _finding_formula(workbook, linked) if linked else "")
        sheet.cell(row + 3, 1, f"Evidence: {issue['evidence']}")
        sheet.merge_cells(start_row=row + 3, start_column=1, end_row=row + 3, end_column=4)
        sheet.cell(row + 4, 1, f"Management focus: {issue['management_focus']}")
        sheet.merge_cells(start_row=row + 4, start_column=1, end_row=row + 4, end_column=4)
        row += 6


def _write_key_findings(workbook, finding_by_id: dict, interpretation: dict) -> None:
    sheet = _analysis_sheet(workbook, "Key Findings", "FDD partner interpretation of validated OCL evidence")
    headers = ["ID", "Area", "Metric", "FY periods / Item", "Movement", "Magnitude", "So what", "Evidence", "Materiality", "Ask management"]
    for col, value in enumerate(headers, start=2):
        sheet.cell(7, col, value)

    for row, item in enumerate(interpretation.get("key_findings") or [], start=8):
        linked = finding_by_id.get(str(item.get("linked_finding_id") or ""))
        magnitude = ""
        if linked is not None:
            magnitude = (
                linked.metrics.get("change_pct")
                or linked.metrics.get("share_pct")
                or linked.metrics.get("coefficient_of_variation")
                or ""
            )
        values = [
            item["id"],
            item["area"],
            item["metric"],
            item["period_item"],
            _finding_formula(workbook, linked) if linked else "",
            magnitude,
            item["so_what"],
            item["evidence"],
            item["materiality"],
            item["ask_management"],
        ]
        for col, value in enumerate(values, start=2):
            sheet.cell(row, col, value)
