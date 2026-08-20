from pathlib import Path
import json


def test_no_fixed_excel_template_in_repository():
    root = Path(__file__).resolve().parents[1]
    names = {path.name.casefold() for path in root.rglob("*.xlsx")}
    assert "template.xlsx" not in names


def test_four_part_structure_exists():
    root = Path(__file__).resolve().parents[1] / "src" / "ocl_agent"
    for part in ("part1_databook", "part2_analysis", "part3_qanda", "part4_report"):
        assert (root / part).is_dir()


def test_codespaces_configuration_is_lightweight_and_complete():
    root = Path(__file__).resolve().parents[1]
    path = root / ".devcontainer" / "devcontainer.json"
    config = json.loads(path.read_text(encoding="utf-8"))

    assert "python:1-3.11" in config["image"]
    assert config["postCreateCommand"] == "python -m pip install -r requirements.txt"
    extensions = config["customizations"]["vscode"]["extensions"]
    assert "GitHub.copilot" in extensions
    assert "GitHub.copilot-chat" in extensions
