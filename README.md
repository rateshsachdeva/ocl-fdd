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

The repository owns the complete workflow:

```text
RAW CLIENT EXCEL
references/source/
        ↓
full fdd-data-preparation
        ├─ Python discovery + structural profiling
        ├─ AI-host dataset understanding
        ├─ AI-host Dataset Map + Processing Plan
        ├─ Python plan validation + deterministic execution
        └─ Python completeness + lineage + publication
        ↓
work/data_prep/output/latest/
standardized long/flat datasets + metadata + lineage
        ↓
OCL semantic handoff
        ↓
OCL scope + dynamic mapping/hierarchy + WC/debt/normality
        ↓
hard reconciliations
        ↓
dynamic formula-driven OCL_Databook.xlsx
        ↓
analysis + management questions
        ↓
workbook styling + final deterministic QA
        ↓
output/OCL_Databook.xlsx
        ↓
secondary output/OCL_Report.pptx
```

The raw source workbooks are read-only and are not committed to Git. The principal deliverable is `output/OCL_Databook.xlsx`.

## The important architectural boundary

`fdd-data-preparation` is responsible for understanding **whatever source layout the client supplied** and producing reliable standardized datasets. `ocl_agent` does **not** parse messy raw Excel and does not contain client-specific header/sheet heuristics.

This means a new source format should normally change the AI-generated Dataset Map / Processing Plan, not OCL production code.

## How AI is used

The data-preparation workflow is AI-powered but model-provider-neutral. The contextual reasoning may be performed by Codex, Claude Code, GitHub Copilot or another capable coding agent.

Python itself does not call an LLM API. Instead the full upstream state machine returns explicit `AI_HOST` checkpoints with the relevant instruction/evidence and required artifacts. A coding-agent host follows those instructions, writes the Dataset Map / Processing Plan (or other requested reasoning artifact), reruns Python, and continues until publication or a genuine human checkpoint.

If `python run_all.py` is launched from a plain terminal with no coding agent driving it, the command may therefore stop at a clearly identified AI-host checkpoint. That is expected and safer than guessing the source layout.

`AGENTS.md` and `.github/copilot-instructions.md` tell coding agents to continue these internal AI-host checkpoints automatically.

## Design principles

- **Full generic upstream preparation.** Raw Excel structure is handled by the full profiler → AI understanding → Processing Plan → deterministic executor workflow.
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
