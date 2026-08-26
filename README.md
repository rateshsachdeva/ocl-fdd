# OCL FDD

Dynamic, auditable financial due-diligence workflow for Other Current Liabilities.

## User experience

Put the raw client Excel files in:

```text
references/source/
```

Install the Python dependencies and run:

```bash
pip install -r requirements.txt
python run_all.py
```

Python 3.11 is recommended.

Normal terminal use delegates the two contextual AI reasoning stages to an installed/authenticated GitHub Copilot CLI. A recipient with GitHub Copilot Enterprise can alternatively open the repo in the VS Code Copilot coding agent and ask it to run the skill end to end; the repository instructions use `python run_all.py --ai-host external` for that interactive-agent route.

For the plain-terminal route, the recipient's organization/enterprise must allow Copilot CLI and the CLI must be installed/authenticated. A Copilot Enterprise seat by itself does not bypass an organization policy that disables the CLI. See `HANDOFF_TO_NEW_USER.md` for the recipient checklist.

The normal successful workflow is intentionally simple:

```text
RAW CLIENT EXCEL
references/source/
        ↓
Python discovery + structural profiling + matched reusable knowledge
        ↓
AI #1: understand datasets + create Dataset Map / Processing Plan
        ↓
Python validation + deterministic reshape + completeness + lineage
        ↓
canonical standardized datasets
        ↓
Python OCL scope/model/controls/databook + evidence-aware analytical tables
        ↓
AI #2: FDD-partner Deal Issues + Key Findings + Q&A
        ↓
Python workbook/PPT rendering + independent final QA
        ↓
output/OCL_Databook_vN.xlsx
output/OCL_Report_vN.pptx
```

The raw source workbooks are read-only and are not committed to Git. The Excel databook is the principal deliverable.

A first run on a new source may intentionally stop at `HUMAN / REVIEW_OCL_JUDGMENTS` for scope, category/hierarchy, WC/debt-like or normal/one-off review. That is a governance checkpoint, not a broken run. Reviewed human judgment remains authoritative.

## Fast reusable knowledge

The data-preparation layer now combines three things before AI #1 plans the source:

```text
source-controlled generic FDD/data patterns
        +
previously promoted safe local learning
        +
current deterministic source profile
        ↓
Python-matched compact knowledge context
        ↓
AI #1 UNDERSTAND_AND_PLAN
```

The built-in knowledge pack contains reusable lessons from difficult synthetic training designs — for example ambiguous headings, multiple datasets on one sheet, Actual/Budget/Variance layouts, hierarchy/subtotals, movement schedules, payroll/P&L/AP/contracts support and evidence requirements for advanced analyses. It deliberately does **not** contain synthetic answer labels, exact expected findings or client-specific mappings.

Current-source evidence always wins over reusable knowledge. Production AI checkpoints are instructed not to open historical synthetic golden-truth/test-answer files.

### Learn one source at a time

For a large or structurally difficult source pack, you can teach the data-understanding layer one workbook at a time before the final combined run:

```bash
python run_all.py --learn-source Finance_Pack.xlsx
python run_all.py --learn-source Balance_Sheet_Detail.xlsx
python run_all.py --learn-source Payroll_and_Accruals.xlsx
python run_all.py --learn-source Supporting_Schedules.xlsx
```

`--learn-source` copies only the selected file into a gitignored learning package, runs data preparation and AI #1 as required, safely promotes reusable learning, and stops **without** creating the final OCL Excel/PPT.

After the desired sources have been learned, keep all relevant client files in `references/source/` and run:

```bash
python run_all.py
```

The final databook still uses the combined source package so cross-file reconciliation, P&L linkage, subsequent settlements, completeness and other FDD analyses remain evidence-complete.

This mode is intended to reduce repeated AI rediscovery. It does not bypass deterministic parsing or genuine ambiguity, so actual runtime should be measured from the printed runtime summary rather than assumed.

## The important architectural boundary

`fdd-data-preparation` is responsible for understanding **whatever source layout the client supplied** and producing reliable standardized datasets. `ocl_agent` does **not** parse messy raw Excel and does not contain client-specific header/sheet heuristics.

This means a new source format should normally change the AI-generated Dataset Map / Processing Plan, not OCL production code.

## How AI is used

Python itself does not call an LLM API and AI does not calculate financial amounts.

For a normal canonical run there are two reasoning passes:

1. **UNDERSTAND_AND_PLAN** — AI reads deterministic profile plus compact matched reusable-knowledge evidence and writes the Dataset Map / Processing Plan, preserving source-present supporting FDD datasets when they are relevant.
2. **WRITE_FDD_PARTNER_ANALYSIS** — after Python has calculated and reconciled the analytical tables, AI writes evidence-backed Deal Issues, Key Findings and Management Q&A.

Intermediate semantic confirmation is deterministic when the standardized publication follows the canonical contract. Control investigation or semantic review remains an exception path only when evidence genuinely requires it.

The automatic GitHub Copilot child checkpoint is deliberately narrow: it may read referenced evidence and write required workflow artifacts, but it does not execute Python/shell commands, modify code, or browse the repository broadly. Python remains the parent workflow executor.

## Evidence-aware analysis

The databook includes an `Analysis Coverage` view so a reviewer can see what the supplied evidence genuinely supports.

Depending on the source package, Python can calculate:

- annual/category movements and concentration;
- monthly volatility and seasonality;
- year-end build/unwind versus the prior three-month run-rate;
- a 12-month balance-persistence / recurrence proxy;
- 12-month average/median normalization references (reference only, not an automatic adjustment);
- stale-balance, new-balance and cliff-to-zero diagnostics;
- debt-like, management-vs-FDD debt-like gap and one-off analysis from reviewed judgments;
- utilisation/release and explicit reversal analysis when validated movement data exists;
- OCL-to-expense ratios only when explicit expense/P&L context is bound;
- revenue/payroll context ratios when those datasets exist.

The workflow does **not** infer unsupported work. True adequacy testing, missing-accrual completeness, double counting and true obligation aging require richer supporting evidence such as subsequent payments, invoice/vendor detail, contracts, payroll/bonus schedules or other obligation-level support. When that evidence is absent, the coverage view marks the analysis unsupported/partial rather than manufacturing a conclusion.

## Design principles

- **Full generic upstream preparation.** Raw Excel structure is handled by profiler → matched knowledge → AI understanding/planning → deterministic executor.
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

See `SKILL.md`, `AGENTS.md`, `HANDOFF_TO_NEW_USER.md` and `_how_it_works.md` for the detailed operating contract.
