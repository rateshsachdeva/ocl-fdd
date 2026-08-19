# OCL FDD

Dynamic, auditable financial due-diligence workflow for Other Current Liabilities.

## User experience

Put the raw client Excel files in:

```text
references/source/
```

Then run:

```bash
python run_all.py
```

The repository now owns the complete flow:

```text
references/source/
        ↓
embedded fdd-data-preparation
        ↓
work/data_prep/latest/
  standardized CSVs + metadata + manifest + lineage
        ↓
automatic canonical semantic handoff
        ↓
OCL scope + dynamic mapping/hierarchy + WC/debt/normality layer
        ↓
hard reconciliations
        ↓
dynamic formula-driven OCL_Databook.xlsx
        ↓
analysis + management questions
        ↓
PDF-aligned workbook styling + final deterministic QA
        ↓
output/OCL_Databook.xlsx
        ↓
secondary output/OCL_Report.pptx
```

The raw source workbooks are read-only and are not copied into Git. The principal deliverable is `output/OCL_Databook.xlsx`.

## Design principles

- **No fixed Excel structural template.** Actual data, periods, categories, hierarchy and supported analyses determine workbook structure.
- **No legacy category universe.** Source-present line items drive the dynamic mapping layer.
- **No silent drops.** In-scope unmapped items, trade payables, financing and other exclusions remain visible.
- **Source traceability.** `Source_Record_ID` lineage is preserved and workbook amounts link to protected standardized source-copy tabs.
- **Reconciliation is a hard gate.** Applicable controls must pass; missing evidence is not solved with plugs.
- **Human decisions remain authoritative.** Existing user-maintained config rows override autonomous first-pass defaults.
- **Package isolation.** Autonomous config rows are source-package-bound so they do not silently leak across engagements.
- **Lightweight runtime.** Standard-library CSV/JSON plus `openpyxl` and `python-pptx`; no pandas and no embedded external LLM API.

## Embedded data preparation

The repository contains `fdd-data-preparation/` as the internal upstream preparation layer. It performs a deterministic fast path for common structured annual, monthly, movement, TB/control and optional revenue/payroll schedules, while preserving source hashes and lineage. Populated sheets that cannot be classified safely are surfaced in `databook_metadata.json` rather than silently ignored.

An existing standardized publication can still be supplied explicitly for compatibility:

```bash
python run_all.py --data-prep-output <path>
```

See `SKILL.md` for the operating contract and `_how_it_works.md` for the workflow.
