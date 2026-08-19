"""Lightweight deterministic PowerPoint renderer.

The report contains only analyses supported by the current OCL data model.  A
future presentation style guide may change appearance without changing the
financial content or forcing fixed slides.
"""
from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt

from ocl_agent.schemas import AnalysisResult, ManagementQuestion


def render_report(analysis: AnalysisResult, questions: tuple[ManagementQuestion, ...], output_path: Path) -> Path:
    prs = Presentation()
    _title_slide(prs)
    _findings_slide(prs, analysis)
    for table in analysis.tables:
        if table.key == "annual_balance":
            _table_slide(prs, table.title, table.headers, table.rows)
        elif table.key == "monthly_statistics":
            _table_slide(prs, table.title, table.headers, table.rows)
    if questions:
        _questions_slide(prs, questions)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(output_path)
    return output_path


def _title_slide(prs: Presentation) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "Other Current Liabilities"
    slide.placeholders[1].text = "Financial due diligence | Dynamic analysis from the reconciled OCL databook"


def _findings_slide(prs: Presentation, analysis: AnalysisResult) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Key findings"
    frame = slide.placeholders[1].text_frame
    frame.clear()
    findings = analysis.findings[:7]
    if not findings:
        paragraph = frame.paragraphs[0]
        paragraph.text = "No material deterministic findings were triggered by the available data."
        return
    for index, finding in enumerate(findings):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = finding.text
        paragraph.level = 0
        paragraph.font.size = Pt(16)


def _table_slide(prs: Presentation, title: str, headers, rows) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = title
    max_rows = min(len(rows), 12)
    max_cols = min(len(headers), 7)
    table_shape = slide.shapes.add_table(max_rows + 1, max_cols, Inches(0.6), Inches(1.5), Inches(12.1), Inches(5.5))
    table = table_shape.table
    for column in range(max_cols):
        table.cell(0, column).text = str(headers[column])
    for row_index, row in enumerate(rows[:max_rows], start=1):
        for column in range(max_cols):
            value = row[column] if column < len(row) else ""
            table.cell(row_index, column).text = _format_value(value)
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.text_frame.paragraphs:
                paragraph.font.size = Pt(10)


def _questions_slide(prs: Presentation, questions: tuple[ManagementQuestion, ...]) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Management questions"
    frame = slide.placeholders[1].text_frame
    frame.clear()
    for index, item in enumerate(questions[:6]):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = item.question
        paragraph.level = 0
        paragraph.font.size = Pt(15)


def _format_value(value) -> str:
    if isinstance(value, float):
        return f"{value:,.1f}"
    try:
        from decimal import Decimal
        if isinstance(value, Decimal):
            return f"{value:,.0f}"
    except ImportError:
        pass
    return str(value)
