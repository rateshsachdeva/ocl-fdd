# How This OCL Skill Works

## What you do

Put the raw Excel files in:

```text
references/source/
```

Run:

```bash
python run_all.py
```

## What the skill does

```text
RAW CLIENT EXCEL FILES
        ↓
embedded fdd-data-preparation
        ↓
standardized data + manifest + metadata + lineage
        ↓
OCL semantic roles
        ↓
OCL scope + dynamic category/hierarchy + WC/debt/normality
        ↓
reconciliation controls
        ↓
dynamic workbook blueprint
        ↓
formula-driven Excel databook
        ↓
analysis + management questions
        ↓
professional FDD workbook styling
        ↓
independent final QA
        ↓
output/OCL_Databook.xlsx
```

The secondary `output/OCL_Report.pptx` is generated from the same reconciled model.

## Why the split still matters

Even though the user now runs one repository and one command, the responsibilities remain separated internally:

- `fdd-data-preparation/` owns source discovery, deterministic reshaping, metadata and lineage.
- `ocl_agent` owns OCL-specific accounting/FDD meaning.
- deterministic Python owns calculations, controls, formula creation, rendering and final QA.
- human-maintained config overrides autonomous defaults.

This keeps the workflow simple to use without mixing source parsing and OCL judgment into one opaque script.

## Dynamic workbook rule

```text
SOURCE DATA + OCL JUDGMENT
        ↓
DYNAMIC WORKBOOK STRUCTURE
        ↓
DETERMINISTIC FORMULAS
        ↓
FDD PRESENTATION LAYER
```

There is no `Template.xlsx`, fixed period range or legacy category list.

## Controls

The skill never hides a mismatch with a balancing plug. Applicable controls must pass. Unsupported controls are explicitly `NOT_APPLICABLE`. Populated source sheets that cannot be classified safely remain visible in data-preparation metadata.

## Efficiency rule

The runtime stays deliberately light: standard-library CSV/JSON plus `openpyxl` and `python-pptx`; no pandas and no external LLM API in the deterministic financial core.
