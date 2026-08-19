# OCL FDD

Dynamic, auditable financial due-diligence workflow for Other Current Liabilities (OCL).

## Design

The repository does **not** use a fixed Excel workbook as the structural basis of the databook.  The structure is derived from approved standardized data, reviewed OCL judgments, available periods, actual hierarchy and analyses supported by the engagement.

```text
fdd-data-preparation
        ↓
approved standardized data + metadata + lineage
        ↓
Part 1 — OCL scope / mapping / hierarchy / judgment / controls
        ↓
shared reconciled OCL data model
        ↓
├─ dynamic OCL_Databook.xlsx
├─ Part 2 findings
├─ Part 3 management Q&A
└─ Part 4 OCL_Report.pptx
```

## Core rules

- source numbers are never invented;
- source lineage is preserved;
- nothing is silently dropped;
- human-reviewed configuration overrides AI suggestions;
- reconciliation is a hard control;
- deterministic Python performs calculations, controls and workbook rendering;
- Parts 1-4 share one reconciled data model;
- `python run_all.py` remains the public entry point;
- no `Template.xlsx`, legacy fixed line-item list, fixed period range or empty analysis section is allowed to drive the databook.

## Current milestone

The first foundation milestone provides the repository structure, shared contracts, upstream publication validation, human-owned judgment loading, dynamic workbook blueprint generation, deterministic rendering primitives, reconciliation primitives, tests and CI.

It deliberately stops before inventing a universal adapter from arbitrary standardized columns to OCL fields.  That semantic handoff will be implemented from actual `fdd-data-preparation` metadata and reviewed evidence in the next stage.

See [`SKILL.md`](SKILL.md) and [`_how_it_works.md`](_how_it_works.md).
