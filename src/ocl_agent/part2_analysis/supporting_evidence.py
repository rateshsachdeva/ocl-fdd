"""Bounded deterministic handoff of standardized supporting evidence to AI #2.

Supporting datasets are never converted into ``OCLRecord`` objects and therefore
cannot change foundation totals or controls. They are exposed as clearly
labelled analysis tables with deterministic, disclosed row selection.
"""
from __future__ import annotations

import csv
import heapq
from collections import deque
from decimal import Decimal, InvalidOperation

from ocl_agent.part1_databook.input_contract import StandardizedPackage
from ocl_agent.part1_databook.semantic_handoff import DatasetUsage, SemanticHandoff
from ocl_agent.schemas import AnalysisTable

MAX_EVIDENCE_ROWS = 200
EDGE_ROWS = 25
TOP_AMOUNT_ROWS = 150


def load_supporting_evidence_tables(
    package: StandardizedPackage,
    handoff: SemanticHandoff,
) -> tuple[AnalysisTable, ...]:
    """Load only explicitly bound standardized supporting datasets."""
    summary_rows: list[tuple[object, ...]] = []
    tables: list[AnalysisTable] = []
    for binding in handoff.datasets:
        if DatasetUsage.SUPPORTING_EVIDENCE not in binding.usages:
            continue
        path = package.root / binding.file
        columns = _bound_columns(binding)
        row_count, selected, selection = _select_rows(path, columns, binding.fields.amount)
        summary_rows.append((binding.file, row_count, len(selected), selection, binding.notes))
        tables.append(
            AnalysisTable(
                f"supporting_evidence_{_slug(binding.file)}",
                f"Standardized supporting evidence: {binding.file}",
                ("Standardized_CSV_Row", *columns),
                tuple(selected),
            )
        )
    if not tables:
        return ()
    summary = AnalysisTable(
        "supporting_evidence_summary",
        "Supporting evidence supplied outside OCL foundation totals",
        ("Dataset", "Source Rows", "Evidence Rows", "Selection", "Semantic Notes"),
        tuple(summary_rows),
    )
    return (summary, *tables)


def _bound_columns(binding) -> tuple[str, ...]:
    fields = binding.fields
    ordered = (
        fields.source_record_id,
        fields.period,
        fields.amount,
        fields.source_label,
        fields.source_code,
        fields.entity,
        fields.currency,
        *binding.dimensions,
    )
    seen: set[str] = set()
    return tuple(value for value in ordered if value and not (value in seen or seen.add(value)))


def _select_rows(path, columns: tuple[str, ...], amount_field: str | None):
    all_rows: list[tuple[object, ...]] = []
    first_rows: list[tuple[object, ...]] = []
    tail_rows: deque[tuple[object, ...]] = deque(maxlen=100)
    top_amounts: list[tuple[Decimal, int, tuple[object, ...]]] = []
    row_count = 0
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for csv_row, row in enumerate(reader, start=2):
            row_count += 1
            values = (csv_row, *(row.get(column) for column in columns))
            if row_count <= MAX_EVIDENCE_ROWS:
                all_rows.append(values)
            if row_count <= 100:
                first_rows.append(values)
            tail_rows.append(values)
            amount = _decimal(row.get(amount_field)) if amount_field else None
            if amount is not None:
                candidate = (abs(amount), csv_row, values)
                if len(top_amounts) < TOP_AMOUNT_ROWS:
                    heapq.heappush(top_amounts, candidate)
                elif candidate[:2] > top_amounts[0][:2]:
                    heapq.heapreplace(top_amounts, candidate)
    if row_count <= MAX_EVIDENCE_ROWS:
        return row_count, all_rows, "FULL"
    if top_amounts:
        selected = _unique_by_row(
            [*first_rows[:EDGE_ROWS], *(item[2] for item in top_amounts), *list(tail_rows)[-EDGE_ROWS:]]
        )
        return row_count, selected, "BOUNDED: first/last 25 plus largest absolute amounts (max 200)"
    selected = _unique_by_row([*first_rows, *tail_rows])
    return row_count, selected, "BOUNDED: first/last 100 rows (max 200)"


def _unique_by_row(rows: list[tuple[object, ...]]) -> list[tuple[object, ...]]:
    by_row = {int(row[0]): row for row in rows}
    return [by_row[index] for index in sorted(by_row)][:MAX_EVIDENCE_ROWS]


def _decimal(value) -> Decimal | None:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _slug(value: str) -> str:
    text = "".join(character if character.isalnum() else "_" for character in value.casefold())
    return "_".join(part for part in text.split("_") if part)[:60] or "dataset"
