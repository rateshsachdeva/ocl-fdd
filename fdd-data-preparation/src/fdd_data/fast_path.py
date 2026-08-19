"""Structural fast-path routing and compact one-cycle AI evidence."""

from __future__ import annotations

from typing import Any


def assess_profile_complexity(profile: dict[str, Any]) -> dict[str, Any]:
    """Route only structurally ambiguous packages to the deeper workflow."""
    reasons: list[str] = []
    for workbook in profile.get("workbook_profiles", []):
        if workbook.get("profiling_status") != "PROFILED":
            reasons.append(f"Source {workbook.get('source_id')} was not fully profiled.")
        for worksheet in workbook.get("worksheet_profiles", []):
            tabular = [
                item for item in worksheet.get("data_regions", [])
                if item.get("candidate_confidence") == "TABULAR_CANDIDATE"
            ]
            if len(tabular) > 1:
                reasons.append(f"Worksheet {worksheet.get('worksheet_name')} contains multiple physical tables.")
            for region in tabular:
                primary = [
                    item for item in region.get("header_candidates", [])
                    if item.get("confidence") == "PRIMARY"
                ]
                if len(primary) != 1:
                    reasons.append(f"Region {region.get('region_id')} has an ambiguous header row.")
                if len(region.get("header_candidates", [])) > 1:
                    reasons.append(f"Region {region.get('region_id')} has a multi-row header candidate.")
    return {
        "workflow_mode": "COMPLEX_PATH" if reasons else "FAST_PATH",
        "requires_targeted_inspection": bool(reasons),
        "reasons": sorted(set(reasons)),
    }


def compact_evidence_package(profile: dict[str, Any]) -> dict[str, Any]:
    """Return bounded structural evidence for one understanding/planning cycle."""
    sources = []
    for workbook in profile.get("workbook_profiles", []):
        worksheets = []
        for worksheet in workbook.get("worksheet_profiles", []):
            regions = []
            for region in worksheet.get("data_regions", []):
                regions.append({
                    "region_id": region.get("region_id"),
                    "cell_range": region.get("cell_range"),
                    "candidate_confidence": region.get("candidate_confidence"),
                    "likely_data_row_ranges": region.get("likely_data_row_ranges", []),
                    "fields": [{
                        "field_id": field.get("field_id"),
                        "physical_column": field.get("physical_column"),
                        "exact_original_header": field.get("exact_original_header"),
                        "normalized_display_header": field.get("normalized_display_header"),
                        "primitive_characteristic": field.get("primitive_characteristic"),
                        "populated_count": field.get("populated_count"),
                        "blank_count": field.get("blank_count"),
                        "formula_presence": field.get("formula_presence"),
                        "representative_values": field.get("representative_values", [])[:3],
                    } for field in region.get("column_profiles", [])],
                    "samples": region.get("samples", [])[:5],
                })
            worksheets.append({
                "worksheet_name": worksheet.get("worksheet_name"),
                "visibility": worksheet.get("visibility"),
                "meaningful_bounds": worksheet.get("meaningful_bounds"),
                "formula_cell_count": worksheet.get("formula_cell_count"),
                "merged_ranges": worksheet.get("merged_ranges", []),
                "hidden_rows": worksheet.get("hidden_rows", []),
                "hidden_columns": worksheet.get("hidden_columns", []),
                "regions": regions,
            })
        sources.append({
            "source_id": workbook.get("source_id"),
            "profiling_status": workbook.get("profiling_status"),
            "worksheets": worksheets,
        })
    return {"profile_run_id": profile.get("run_id"), "sources": sources}


__all__ = ["assess_profile_complexity", "compact_evidence_package"]
