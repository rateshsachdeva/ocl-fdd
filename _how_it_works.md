# How This OCL Skill Works

```text
RAW CLIENT DATA
      ↓
fdd-data-preparation
      ↓
APPROVED STANDARDIZED DATA + METADATA + LINEAGE
      ↓
semantic handoff (AI host interprets; Python validates)
      ↓
reviewed scope + mapping/hierarchy + WC/debt + normality
      ↓
shared reconciled OCL data model
      ↓
controls
      ↓
dynamic workbook blueprint
      ↓
deterministic Excel rendering
      ↓
OCL_Databook.xlsx
```

## Why the split matters

- `fdd-data-preparation` owns generic raw-source discovery, understanding and reshaping.
- OCL owns OCL-specific financial meaning and review.
- Python owns calculations, traceability, controls and workbook writing.
- The AI host owns contextual interpretation and drafting, not financial arithmetic.
- Human-reviewed config is the highest authority.

## Part 1 states

```text
run_all.py
   │
   ├─ no confirmed semantic handoff → AWAITING_SEMANTIC_HANDOFF
   ├─ incomplete/unreviewed OCL judgments → AWAITING_JUDGMENT_REVIEW
   ├─ hard control needs alignment / has break → AWAITING_CONTROL_ALIGNMENT
   └─ applicable controls pass → DATABOOK_READY
```

The skill never solves a failed control with a plug. A missing prerequisite is `NOT_APPLICABLE`; an available but unresolved prerequisite is `REVIEW_REQUIRED`.

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

No `Template.xlsx`, fixed period range, legacy category list or empty analysis section drives the workbook. `Checks`, mapping transparency, unmapped visibility and scope-exclusion visibility remain mandatory control concepts.

## Efficiency rule

Keep the deterministic core small: stream standardized CSV rows, keep only bounded samples for interpretation, use standard-library CSV/JSON plus `openpyxl`, and reuse the one OCL record model everywhere. Do not add pandas, an LLM API, or a second raw-source parser unless a demonstrated requirement justifies it.
