from pathlib import Path
import json

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

    monthly = wb.create_sheet("Monthly OCL")
    months = [f"2025-{month:02d}" for month in range(1, 13)]
    monthly.append(["GL Account", "Account description", *months])
    monthly.append(["2100", "Bonus accrual", *[300 + month for month in range(12)]])
    monthly.append(["2110", "Holiday pay accrual", *[200 + month for month in range(12)]])
    monthly.append(["2120", "VAT payable", *[100 + month for month in range(12)]])
    monthly.append(["2130", "Professional fee accrual", *[130 + month for month in range(12)]])
    wb.save(path)


def test_raw_source_profiles_then_hands_off_to_ai_understanding(tmp_path: Path):
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

    # A plain Python process deliberately stops here. A coding/agent AI host
    # reads the handoff, creates Dataset Map + Processing Plan artifacts and
    # reruns the same root workflow. No client-format parser is expected here.
    assert result.state == "DATA_PREP_AWAITING_AI_PLANNING"
    assert result.data_prep_state == "AWAITING_AI_PLANNING"
    assert result.next_actor == "AI_HOST"
    assert result.next_action == "UNDERSTAND_AND_PLAN"
    assert result.handoff_path and result.handoff_path.exists()
    assert len(result.required_artifacts) == 3
    assert raw.read_bytes() == source_bytes
    assert not (output / "OCL_Databook.xlsx").exists()

    handoff = json.loads(result.handoff_path.read_text(encoding="utf-8"))
    assert handoff["task"] == "FAST_PATH_DATASET_UNDERSTANDING_AND_PROCESSING_PLAN"
    assert handoff["evidence_package"]["sources"]
    assert Path(handoff["targets"]["dataset_map"]) == result.required_artifacts[0]
    assert Path(handoff["targets"]["processing_plan"]) == result.required_artifacts[1]
    assert Path(handoff["targets"]["approval_questions"]) == result.required_artifacts[2]

    run_dir = result.handoff_path.parents[1]
    assert (run_dir / "workflow_state.json").exists()
    profile_paths = list(run_dir.glob("PROFILE_*/profile.json"))
    assert len(profile_paths) == 1
    profile = json.loads(profile_paths[0].read_text(encoding="utf-8"))
    assert profile["source_files"][0]["filename"] == raw.name
    assert any(
        region.get("candidate_confidence") == "TABULAR_CANDIDATE"
        for workbook in profile["workbook_profiles"]
        for worksheet in workbook["worksheet_profiles"]
        for region in worksheet["data_regions"]
    )
