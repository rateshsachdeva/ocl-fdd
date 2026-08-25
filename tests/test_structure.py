from pathlib import Path


def test_no_fixed_excel_template_in_repository():
    root = Path(__file__).resolve().parents[1]
    names = {path.name.casefold() for path in root.rglob("*.xlsx")}
    assert "template.xlsx" not in names


def test_four_part_structure_exists():
    root = Path(__file__).resolve().parents[1] / "src" / "ocl_agent"
    for part in ("part1_databook", "part2_analysis", "part3_qanda", "part4_report"):
        assert (root / part).is_dir()
