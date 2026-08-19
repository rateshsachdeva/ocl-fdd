# How This OCL Skill Works

## Core architecture

```text
RAW CLIENT DATA
      ↓
fdd-data-preparation
      ↓
APPROVED STANDARDIZED DATA + METADATA + LINEAGE
      ↓
Part 1 — OCL Databook
  scope → mapping/hierarchy → WC/debt/normalization judgment
      ↓
SHARED RECONCILED OCL DATA MODEL
      ↓
  ├─ Part 1 dynamic workbook rendering
  ├─ Part 2 analysis/findings
  ├─ Part 3 management Q&A
  └─ Part 4 PowerPoint report
```

## Non-negotiable design rules

1. Source numbers are never invented.
2. Client source data and provenance are preserved.
3. Nothing is silently dropped; unmapped and excluded records stay visible.
4. Human-reviewed configuration owns financial meaning.
5. Reconciliation is a hard control.
6. Optional inputs degrade gracefully.
7. Deterministic Python calculates, reconciles and renders.
8. AI can interpret and draft but does not become the financial calculation engine.
9. No `Template.xlsx` or fixed workbook controls the databook structure.
10. Actual data + analytical judgment determine sheets, periods, categories, hierarchy and supported analyses.
11. The styling guide controls appearance only.
12. Parts 1-4 must consume the same reconciled OCL model.

## Dynamic workbook rule

```text
DATA + REVIEWED ANALYTICAL JUDGMENT
        ↓
DYNAMIC WORKBOOK BLUEPRINT
        ↓
DETERMINISTIC PYTHON RENDERING
        ↓
OCL WORKBOOK STYLING GUIDE
```

Mandatory control/review concepts such as Checks, Mapping, UNMAPPED and
SCOPE_EXCLUDED remain visible even though analytical sheet structure is dynamic.
A control may be `NOT_APPLICABLE` when its prerequisite data does not exist; the
skill must not invent an analysis merely to satisfy a fixed layout.
