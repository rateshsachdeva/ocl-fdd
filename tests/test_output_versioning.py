from pathlib import Path

from ocl_agent.output_versioning import next_output_version, publish_versioned_databook


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_first_completed_run_publishes_databook_only(tmp_path: Path):
    output = tmp_path / "output"
    working = _write(tmp_path / "work" / "OCL_Databook_working.xlsx", "book-one")

    published = publish_versioned_databook(working, output)

    assert published.version == 1
    assert published.databook == output / "OCL_Databook_v1.xlsx"
    assert published.databook.read_text(encoding="utf-8") == "book-one"
    assert not list(output.glob("*.pptx"))
    assert not (output / "OCL_Databook.xlsx").exists()


def test_next_publication_preserves_historical_databook(tmp_path: Path):
    output = tmp_path / "output"
    _write(output / "OCL_Databook_v1.xlsx", "old-book")
    working = _write(tmp_path / "work" / "OCL_Databook_working.xlsx", "new-book")

    published = publish_versioned_databook(working, output)

    assert published.version == 2
    assert published.databook.name == "OCL_Databook_v2.xlsx"
    assert (output / "OCL_Databook_v1.xlsx").read_text(encoding="utf-8") == "old-book"
    assert published.databook.read_text(encoding="utf-8") == "new-book"


def test_version_scan_uses_only_versioned_databooks(tmp_path: Path):
    output = tmp_path / "output"
    _write(output / "OCL_Databook_v2.xlsx", "x")
    _write(output / "OCL_Report_v9.pptx", "legacy")
    _write(output / "other.xlsx", "z")

    assert next_output_version(output) == 3
