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

Normal terminal use delegates the two contextual AI reasoning stages to an installed/authenticated GitHub Copilot CLI. If Codex or Claude Code is already running the repository interactively, use `python run_all.py --ai-host external` so that active agent completes the AI checkpoints itself.

The normal successful workflow is intentionally simple:

```text
RAW CLIENT EXCEL
references/source/
        ↓
Python discovery + structural profiling + knowledge evidence
        ↓
AI #1: understand datasets + create Dataset Map / Processing Plan
        ↓
Python validation + deterministic reshape + completeness + lineage
        ↓
canonical standardized datasets
        ↓
Python OCL scope/model/controls/databook + analytical tables
        ↓
AI #2: FDD-partner Deal Issues + Key Findings + Q&A
        ↓
Python workbook/PPT rendering + independent final QA
        ↓
output/OCL_Databook_vN.xlsx
output/OCL_Report_vN.pptx
```

The raw source workbooks are read-only and are not committed to Git. The Excel databook is the principal deliverable.

## The important architectural boundary

`fdd-data-preparation` is responsible for understanding **whatever source layout the client supplied** and producing reliable standardized datasets. `ocl_agent` does **not** parse messy raw Excel and does not contain client-specific header/sheet heuristics.

This means a new source format should normally change the AI-generated Dataset Map / Processing Plan, not OCL production code.

## How AI is used

Python itself does not call an LLM API and AI does not calculate financial amounts.

For a normal canonical run there are two reasoning passes:

1. **UNDERSTAND_AND_PLAN** — AI reads deterministic profile/knowledge evidence and writes the Dataset Map / Processing Plan.
2. **WRITE_FDD_PARTNER_ANALYSIS** — after Python has calculated and reconciled the analytical tables, AI writes evidence-backed Deal Issues, Key Findings and Management Q&A.

Intermediate semantic confirmation is deterministic when the standardized publication follows the canonical contract. Control investigation or semantic review remains an exception path only when evidence genuinely requires it.

The automatic GitHub Copilot child checkpoint is deliberately narrow: it may read referenced evidence and write required workflow artifacts, but it does not execute Python/shell commands, modify code, or browse the repository broadly. Python remains the parent workflow executor.

## Design principles

- **Full generic upstream preparation.** Raw Excel structure is handled by profiler → AI understanding/planning → deterministic executor.
- **No second raw-source parser in OCL.** OCL starts from the published standardized package.
- **No fixed Excel structural template.** Actual data, periods, categories, hierarchy and supported analyses determine workbook structure.
- **No legacy category universe.** Source-present line items drive the dynamic mapping layer.
- **No silent drops.** In-scope unmapped items, trade payables, financing and other exclusions remain visible.
- **Source traceability.** `Source_Record_ID` and upstream lineage are retained through the OCL model.
- **Reconciliation is a hard gate.** Applicable controls must pass; missing evidence is not solved with plugs.
- **Human judgment remains authoritative.** Scope, mapping/hierarchy, WC/debt-like and normal/one-off decisions remain reviewable; existing reviewed config wins.
- **Lightweight downstream runtime.** OCL uses standard-library CSV/JSON plus `openpyxl` and `python-pptx`; no pandas and no embedded external LLM API.

## Existing standardized package

For compatibility/testing, an already published upstream package can still be supplied explicitly:

```bash
python run_all.py --data-prep-output <path-to-output/latest>
```

See `SKILL.md`, `AGENTS.md` and `_how_it_works.md` for the detailed operating contract.
