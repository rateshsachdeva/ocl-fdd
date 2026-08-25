from pathlib import Path

from ocl_agent.output_versioning import next_output_version, publish_versioned_deliverables


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_first_completed_run_publishes_matching_v1_pair(tmp_path: Path):
    output = tmp_path / "output"
    databook = _write(output / "OCL_Databook.xlsx", "book-one")
    report = _write(output / "OCL_Report.pptx", "report-one")

    published = publish_versioned_deliverables(databook, report, output)

    assert published.version == 1
    assert published.databook == output / "OCL_Databook_v1.xlsx"
    assert published.report == output / "OCL_Report_v1.pptx"
    assert published.databook.read_text(encoding="utf-8") == "book-one"
    assert published.report.read_text(encoding="utf-8") == "report-one"


def test_next_completed_run_uses_next_global_version(tmp_path: Path):
    output = tmp_path / "output"
    _write(output / "OCL_Databook_v1.xlsx", "old-book")
    _write(output / "OCL_Report_v1.pptx", "old-report")
    databook = _write(output / "OCL_Databook.xlsx", "new-book")
    report = _write(output / "OCL_Report.pptx", "new-report")

    published = publish_versioned_deliverables(databook, report, output)

    assert published.version == 2
    assert published.databook.name == "OCL_Databook_v2.xlsx"
    assert published.report.name == "OCL_Report_v2.pptx"
    assert (output / "OCL_Databook_v1.xlsx").read_text(encoding="utf-8") == "old-book"
    assert (output / "OCL_Report_v1.pptx").read_text(encoding="utf-8") == "old-report"


def test_workbook_only_run_still_consumes_one_version(tmp_path: Path):
    output = tmp_path / "output"
    databook = _write(output / "OCL_Databook.xlsx", "book")

    first = publish_versioned_deliverables(databook, None, output)
    assert first.version == 1
    assert first.report is None

    report = _write(output / "OCL_Report.pptx", "report")
    second = publish_versioned_deliverables(databook, report, output)
    assert second.version == 2
    assert second.databook.name == "OCL_Databook_v2.xlsx"
    assert second.report.name == "OCL_Report_v2.pptx"


def test_version_scan_uses_highest_existing_databook_or_report(tmp_path: Path):
    output = tmp_path / "output"
    _write(output / "OCL_Databook_v2.xlsx", "x")
    _write(output / "OCL_Report_v5.pptx", "y")
    _write(output / "other.xlsx", "z")

    assert next_output_version(output) == 6
