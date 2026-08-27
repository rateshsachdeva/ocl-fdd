"""One final workbook presentation pass after all analysis is populated."""
from __future__ import annotations

import json
from pathlib import Path

from openpyxl import load_workbook

from ocl_agent.databook_display import apply_display_preferences_to_workbook
from ocl_agent.workbook_style import style_workbook


def apply_final_workbook_presentation(path: Path, semantic_handoff_path: Path | None = None) -> Path:
    path = Path(path)
    handoff = None
    if semantic_handoff_path and Path(semantic_handoff_path).is_file():
        payload = json.loads(Path(semantic_handoff_path).read_text(encoding="utf-8"))
        handoff = payload if isinstance(payload, dict) else None
    workbook = load_workbook(path)
    style_workbook(workbook)
    apply_display_preferences_to_workbook(workbook, handoff)
    workbook.save(path)
    return path
