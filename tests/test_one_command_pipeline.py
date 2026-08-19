from pathlib import Path

from openpyxl import Workbook

from ocl_agent.config import RepoPaths
from ocl_agent.end_to_end import run_end_to_end


def _build_raw_source(path: Path) -> None:
    wb = Workbook()
    annual = wb.active
    annual.title = "Annual OCL"
    annual.append(["GL Account", "Account description", "FY24", "FY25"])
    annual.append(["2100", "Bonus accrual", 300, 450])
    annual.append(["2110", "Holiday pay accrual", 200, 250])
    annual.append(["2120", "VAT payable", 100, 150])
    annual.append(["2130", "Professional fee accrual", 130, 120])
    annual.append(["2000", "Trade payables", 400, 500])
    annual.append(["2200", "Current bank loan", 500, 400])

    monthly = wb.create_sheet("Monthly OCL")
    months = [f"2025-{month:02d}" for month in range(1, 13)]
    monthly.append(["GL Account", "Account description", *months])
    monthly.append(["2100", "Bonus accrual", 300, 250, 275, 330, 290, 310, 360, 340, 375, 390, 410, 450])
    monthly.append(["2110", "Holiday pay accrual", 200, 180, 190, 205, 210, 220, 215, 225, 235, 240, 245, 250])
    monthly.append(["2120", "VAT payable", 100, 90, 105, 95, 110, 125, 120, 130, 140, 135, 145, 150])
    monthly.append(["2130", "Professional fee accrual", 130, 115, 120, 125, 110, 105, 100, 115, 125, 130, 118, 120])
    wb.save(path)


def test_raw_source_reaches_ai_understanding_checkpoint_without_source_change(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    references = tmp_path / "references"
    source = references / "source"
    other = references / "other"
    config = tmp_path / "config"
    output = tmp_path / "output"
    for folder in (source, other, config, output):
        folder.mkdir(parents=True, exist_ok=True)

    raw = source / "Synthetic_Client_OCL_Source.xlsx"
    _build_raw_source(raw)
    source_bytes = raw.read_bytes()

    paths = RepoPaths(repo_root, repo_root / "assets", config, output, references, source, other)
    result = run_end_to_end(paths)

    # A plain Python process must stop at the real AI reasoning boundary. A
    # coding/agent host reads the handoff, writes the requested Dataset Map /
    # Processing Plan artifacts and resumes this same root workflow.
    assert result.state in {"AWAITING_AI_PLANNING", "AWAITING_DATASET_UNDERSTANDING"}
    assert result.coordination.get("next_actor") == "AI_HOST"
    assert result.coordination.get("next_action") in {"UNDERSTAND_AND_PLAN", "DATASET_UNDERSTANDING"}
    handoff_path = Path(result.coordination["handoff_path"])
    assert handoff_path.exists()
    assert result.coordination.get("must_continue") is True
    assert result.coordination.get("resume_command") == "python run_all.py"
    assert raw.read_bytes() == source_bytes
    assert not (output / "OCL_Databook.xlsx").exists()
