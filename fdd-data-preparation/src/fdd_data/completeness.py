"""Deterministic source, output, and lineage completeness controls."""

from __future__ import annotations

from typing import Any, Iterable

from .lineage import SourceRowIdentity


def evaluate_completeness(
    *,
    discovered_source_ids: Iterable[str],
    discovered_region_ids: Iterable[str],
    included_source_ids: Iterable[str],
    included_region_ids: Iterable[str],
    excluded_source_ids: Iterable[str],
    excluded_region_ids: Iterable[str],
    relevant_source_rows: Iterable[SourceRowIdentity],
    retained_source_rows: Iterable[SourceRowIdentity],
    excluded_source_rows: Iterable[SourceRowIdentity],
    expected_output_records: int,
    actual_output_records: int,
    output_records_with_valid_lineage: int,
    retained_rows_with_output_lineage: Iterable[SourceRowIdentity],
) -> dict[str, Any]:
    """Return the publication-gate completeness result without business inference."""
    discovered_sources = set(discovered_source_ids)
    discovered_regions = set(discovered_region_ids)
    included_sources = set(included_source_ids)
    included_regions = set(included_region_ids)
    excluded_sources = set(excluded_source_ids)
    excluded_regions = set(excluded_region_ids)
    relevant_rows = set(relevant_source_rows)
    retained_rows = set(retained_source_rows)
    excluded_rows = set(excluded_source_rows)
    lineage_rows = set(retained_rows_with_output_lineage)

    unexplained_sources = discovered_sources - included_sources - excluded_sources
    unexplained_regions = discovered_regions - included_regions - excluded_regions
    unexplained_rows = relevant_rows - retained_rows - excluded_rows
    overlapping_rows = retained_rows & excluded_rows
    rows_missing_lineage = retained_rows - lineage_rows

    source_files_pass = not unexplained_sources
    source_regions_pass = not unexplained_regions
    source_rows_pass = not unexplained_rows and not overlapping_rows and retained_rows | excluded_rows == relevant_rows
    output_pass = expected_output_records == actual_output_records
    lineage_pass = output_records_with_valid_lineage == actual_output_records and not rows_missing_lineage
    passed = all((source_files_pass, source_regions_pass, source_rows_pass, output_pass, lineage_pass))
    return {
        "source_files": {
            "discovered": len(discovered_sources), "included": len(included_sources),
            "explicitly_excluded": len(excluded_sources), "unexplained": len(unexplained_sources),
            "status": "PASS" if source_files_pass else "FAIL",
        },
        "source_regions": {
            "discovered": len(discovered_regions), "included": len(included_regions),
            "explicitly_excluded": len(excluded_regions), "unexplained": len(unexplained_regions),
            "status": "PASS" if source_regions_pass else "FAIL",
        },
        "source_rows": {
            "relevant": len(relevant_rows), "retained": len(retained_rows),
            "explicitly_excluded": len(excluded_rows), "unexplained": len(unexplained_rows),
            "overlap": len(overlapping_rows), "status": "PASS" if source_rows_pass else "FAIL",
        },
        "output_records": {
            "expected": expected_output_records, "actual": actual_output_records,
            "status": "PASS" if output_pass else "FAIL",
        },
        "lineage": {
            "output_records_with_valid_lineage": output_records_with_valid_lineage,
            "actual_output_records": actual_output_records,
            "retained_source_rows_without_output_lineage": len(rows_missing_lineage),
            "status": "PASS" if lineage_pass else "FAIL",
        },
        "unexplained_source_ids": sorted(unexplained_sources),
        "unexplained_region_ids": sorted(unexplained_regions),
        "overall_status": "PASS" if passed else "FAIL",
    }


def completeness_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    labels = {
        "source_files": "SOURCE_FILE_COMPLETENESS",
        "source_regions": "SOURCE_REGION_COMPLETENESS",
        "source_rows": "SOURCE_ROW_COMPLETENESS",
        "output_records": "OUTPUT_RECORD_COMPLETENESS",
        "lineage": "LINEAGE_COMPLETENESS",
    }
    checks = []
    for key, check in labels.items():
        details = summary[key]
        checks.append({"check": check, "status": details["status"], "message": f"{check}: {details['status']}.", **details})
    checks.append({
        "check": "OVERALL_COMPLETENESS",
        "status": summary["overall_status"],
        "message": f"Overall data completeness: {summary['overall_status']}.",
    })
    return checks


__all__ = ["completeness_checks", "evaluate_completeness"]
