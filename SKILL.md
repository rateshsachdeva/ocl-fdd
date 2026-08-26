# OCL Financial Due Diligence Skill

## Objective

Build a traceable, dynamically structured Other Current Liabilities financial-due-diligence databook from raw client source files, then produce evidence-based analysis, management questions and a secondary PowerPoint report from one shared reconciled OCL model.

The user-facing workflow is:

```text
put raw files in references/source/
        ↓
python run_all.py
        ↓
output/OCL_Databook_vN.xlsx
output/OCL_Report_vN.pptx
```

## Architecture

```text
RAW CLIENT EXCEL
        ↓
FULL fdd-data-preparation
        ├─ deterministic discovery + structural profiling
        ├─ AI-host Dataset Understanding + Processing Plan
        ├─ deterministic validation + execution
        └─ completeness + metadata + row/field lineage
        ↓
PUBLISHED STANDARDIZED LONG / FLAT DATA
        ↓
OCL canonical semantic carry-forward / exception semantic review
        ↓
reviewable scope + mapping/hierarchy + WC/debt + normality
        ↓
hard controls
        ↓
Part 1 — dynamic formula-driven databook
        ↓
Part 2 — deterministic evidence-aware analysis
        ↓
AI-host FDD-partner interpretation
        ↓
Deal Issues + Key Findings + Management Q&A
        ↓
final workbook styling + deterministic QA
        ↓
versioned OCL_Databook_vN.xlsx + OCL_Report_vN.pptx
```

`run_all.py` is the public launcher.

## Full fdd-data-preparation boundary

Raw client workbook structure belongs entirely to the embedded full `fdd-data-preparation` workflow.

It owns:

- read-only source discovery and SHA-256 binding;
- workbook / worksheet / region / field profiling;
- bounded samples and targeted inspection evidence;
- AI-host logical-dataset understanding;
- AI-host Dataset Map and Processing Plan creation;
- deterministic schema / source-reference validation;
- deterministic union, unpivot, reshape, select and other approved operations;
- completeness proof;
- row and field lineage;
- execution manifest and metadata publication.

The data-preparation AI layer is **provider-neutral, not absent**. Codex, Claude Code, GitHub Copilot or another capable coding agent may perform the contextual reasoning. Python itself does not call an external LLM API.

When the upstream Python state machine requires reasoning, it returns a coordination object identifying `next_actor`, `next_action`, `relevant_instruction`, `handoff_path` and required artifacts. A coding-agent host must follow `AGENTS.md`, create those artifacts and rerun until publication or a genuine human checkpoint.

During `UNDERSTAND_AND_PLAN`, source-present supporting FDD datasets must not be discarded merely because they are not the core annual OCL listing. Where evidence supports their role, preserve monthly P&L/expense, detailed accrual schedules, movement/reversal/settlement data, revenue/payroll context, account mapping and similar supporting datasets in the Dataset Map / Processing Plan.

**Do not add client-specific Excel heading aliases, worksheet-name parsers or raw-source interpretation to `ocl_agent`.** A changed client format should normally produce a different Dataset Map / Processing Plan, not new OCL parsing code.

`ocl_agent` starts only from a publishable standardized package.

## Non-negotiable databook rules

### Source fidelity and lineage

- Never invent financial amounts, balancing figures or plugs.
- Never alter raw client source workbooks.
- Preserve upstream `Source_Record_ID` and available lineage.
- Foundation amounts are source-derived; analytical schedules use deterministic Excel formulas/arithmetic over the foundation.
- Invalid, unknown, unmapped and excluded records remain visible; no silent drop is permitted.

### Judgment ownership

OCL owns accounting/FDD meaning after data preparation:

- scope: `IN_SCOPE`, `TRADE_PAYABLE`, `FINANCING`, `OUT_OF_SCOPE`, `REVIEW_REQUIRED`;
- source-present category and parent/child hierarchy;
- management/FDD view: `working_capital`, `debt_like`, `neither`;
- normality: `normal`, `one_off`;
- line-item notes and optional context.

Existing reviewed human config is authoritative. AI can interpret evidence and prepare proposals, but it must not silently overwrite reviewed decisions or mark an unsupported judgment reviewed merely to complete a run.

### Dynamic workbook

Do not use `Template.xlsx` or another fixed Excel workbook as the structural basis. Do not hard-code a legacy OCL category universe, fixed periods or empty analytical sections.

Actual standardized data + reviewed OCL judgment determine periods, categories, hierarchy, sheets and supported analysis.

Core transparency concepts remain mandatory where relevant:

- `Checks`;
- `Mapping`;
- `UNMAPPED`;
- `SCOPE_EXCLUDED`;
- `Analysis Coverage` in a full Part 2 run;
- protected standardized `SRC_*` tabs / source evidence.

Children appear before parent subtotals. Parent rows and Total OCL are formula-driven. If a genuine residual exists within a category, it must remain explicit (for example `Unallocated within category`) rather than being hidden in a plug.

### Reconciliation is a hard gate

Applicable controls must pass within tolerance before Part 1 publishes the final databook. Missing prerequisites are `NOT_APPLICABLE`; available-but-unresolved prerequisites are `REVIEW_REQUIRED`; genuine mismatches are `FAIL`.

Controls include, where supported:

1. `chk_categories_sum`
2. `chk_listing_vs_tb`
3. `chk_rollforward`
4. `chk_wcdebt_exhaustive`
5. `chk_continuity`
6. `chk_scope_reconciles`
7. `chk_monthly_to_annual`
8. record-coverage / semantic-build / judgment-completion checks

Default monetary tolerance is `< 0.5` unless a documented source-scale rule requires otherwise.

Never solve a failed control with a balancing plug.

## Part 1 states

### Upstream data-preparation checkpoints

Before OCL starts, the full upstream workflow may return states such as:

- `AWAITING_DATASET_UNDERSTANDING`
- `AWAITING_AI_PLANNING`
- `AWAITING_PROCESSING_PLAN`
- `AWAITING_USER_DECISIONS`

AI-host checkpoints are internal continuation points. Genuine user-decision states are surfaced narrowly.

### `AWAITING_SEMANTIC_HANDOFF`

The standardized package exists, but OCL dataset usages / field roles are not yet confirmed. Python writes the review/draft artifacts. This is an exception path when canonical semantic carry-forward is not available. The AI host interprets only the published standardized package and writes package-specific `semantic_handoff.json`.

It must not go back to raw Excel and duplicate upstream source parsing.

### `AWAITING_JUDGMENT_REVIEW`

Scope, category/hierarchy, WC/debt-like or normality judgments require reviewed decisions. This is an intentional `HUMAN` checkpoint for new/unreviewed source labels. Review context remains visible and human-owned decisions win.

### `AWAITING_CONTROL_ALIGNMENT`

One or more hard controls require explicit source-backed alignment or contain a genuine break. Investigate the evidence; never plug the difference.

### `DATABOOK_READY`

Part 1 creates the working `output/OCL_Databook.xlsx` and downstream analysis/reporting use the same reconciled OCL model. A completed launcher run publishes versioned snapshots.

## Standardized-package semantic handoff

Dataset usages are:

- `OCL_RECORDS`
- `MONTHLY_RECORDS`
- `MOVEMENT_RECORDS`
- `TB_CONTROL`
- `REVENUE_CONTEXT`
- `PAYROLL_CONTEXT`
- `EXPENSE_CONTEXT`
- `IGNORE`

For OCL/monthly records, required roles are `source_record_id`, `period`, `amount`, `source_label`. Optional roles include `source_code`, `entity`, `currency` and available dimensions.

Movement records additionally require `movement_type`, with explicit source-value rules mapped to `OPENING`, `FLOW` or `CLOSING` and explicit multipliers. Period alignments are package-specific.

Context datasets require explicit `period` and `amount` roles. `EXPENSE_CONTEXT` is only for a genuinely relevant source-backed P&L/expense measure; do not substitute an unrelated denominator.

Do not infer field meaning from a heading alone; use the upstream Dataset Map, metadata, samples, lineage and contextual evidence.

## Part 2 — evidence-aware analysis

Part 2 calculates only from the reconciled Part 1 model and explicitly reports whether each analysis is supported by the evidence actually supplied.

### Balance-history analysis

Where monthly/annual balances support it, Python calculates:

- annual OCL and category movements;
- concentration;
- monthly variability / volatility;
- seasonality;
- year-end build / unwind versus the prior three-month run-rate;
- new balances and balances falling to nil;
- stale-balance proxy from unchanged monthly history;
- 12-month balance persistence / recurrence proxy;
- 12-month average and median normalization reference.

The recurrence output is a **balance-pattern proxy**, not proof of economic recurrence. The normalization output is a **reference**, not an automatic normalized-working-capital adjustment.

### Movement analysis

Only when validated explicit movement records exist, Python may calculate:

- additions / releases;
- utilisation/release ratios;
- explicit reversal patterns;
- movement-linked roll-forward observations.

Do not infer utilisation or reversals from balance changes when explicit movement evidence is absent.

### Context ratios

Only when explicit context datasets are semantically bound, Python may calculate:

- OCL / revenue;
- OCL / payroll;
- OCL / expense.

An accrual-to-expense ratio is therefore supported only when a relevant expense/P&L denominator is explicitly present and bound. Do not create a proxy denominator from unrelated data.

### Reviewed-judgment analysis

Python also analyses reviewed:

- debt-like treatment;
- management-versus-FDD debt-like gaps;
- normal / one-off classification.

### Analysis Coverage — hard evidence boundary

The full databook includes `Analysis Coverage` with statuses such as `SUPPORTED`, `PARTIAL`, `REFERENCE_ONLY` and `UNSUPPORTED`.

The skill must never pretend an analysis is supported because the output would otherwise look incomplete.

In particular:

- unchanged monthly history may support a stale-balance proxy, but not true obligation aging;
- adequacy requires obligation/expense/settlement evidence beyond aggregate balance history;
- missing-accrual completeness requires completeness evidence such as subsequent payments, contracts, vendor/payroll or P&L support;
- double counting requires sufficiently detailed obligation/vendor/payroll/invoice-level evidence.

Until those richer evidence contracts are explicitly implemented and supplied, adequacy, missing-accrual and double-counting analysis must remain `UNSUPPORTED`, not inferred.

Deterministic code establishes numeric observations. AI interprets the validated evidence without changing calculations or elevating unsupported coverage into a conclusion.

## FDD-partner analysis and management questions

After Python creates the analytical evidence pack, the AI host writes Deal Issues, Key Findings and Management Q&A from that evidence only.

Questions arise only from actual evidence/findings. Do not ask questions for the sake of filling a sheet.

- Ask one focused operational/evidential point per question.
- New item: ask what event or calculation gave rise to it.
- Cliff to nil: ask how it was settled/released.
- Stale-balance proxy: ask whether the obligation remains valid and outstanding, while acknowledging the evidence limitation.
- Movement/spike: ask for the primary underlying driver.
- Concentration: request composition and settlement timing where useful.
- Do not ask management to decide whether something is debt-like, one-off or a purchase-price adjustment.
- Do not routinely demand invoices or roll-forwards unless the evidence requires them.
- Never claim an `UNSUPPORTED` analysis was performed.

Questions are embedded in the databook and use the same hash-bound Python evidence package as Deal Issues / Key Findings.

## Workbook presentation contract

Presentation follows `assets/OCL_WORKBOOK_GUIDE.md` and may not change financial logic.

Key conventions include:

- dark navy headers with white text;
- Arial-style professional body formatting;
- accounting number formats, negatives in parentheses and zeros as dashes;
- blue source/hardcoded values, green inter-sheet links and black calculations;
- visible parent subtotals and Total OCL;
- green/red/amber/grey control-status formatting;
- hidden gridlines, freeze panes, sensible widths and print setup;
- protected standardized source-copy tabs;
- visible `UNMAPPED` and scope-excluded material;
- readable findings and management questions.

## Final QA

After analysis/questions and styling, the workbook is reopened and independently checked for:

- mandatory control / lineage concepts;
- source-copy protection;
- required `Source_Record_ID`, amount, scope and review fields;
- blocking Python controls;
- broken `#REF!` formulas;
- substantive narrative sections in a full analysis run;
- successful reopen.

## Completion rule

The workflow is complete only when:

1. raw sources remain unchanged;
2. the full data-preparation workflow publishes standardized data + metadata + lineage;
3. OCL consumes that publication rather than reparsing raw Excel;
4. every relevant OCL record has explicit disposition;
5. required judgments are reviewed;
6. applicable hard controls pass and unsupported controls are explicit `NOT_APPLICABLE`;
7. the databook reopens cleanly and passes final QA;
8. analysis coverage accurately reflects the supplied evidence;
9. Deal Issues, Key Findings and management questions use the same reconciled evidence pack;
10. matching versioned Excel and PowerPoint outputs are produced unless the report is explicitly skipped.

For transfer to another user, see `HANDOFF_TO_NEW_USER.md`.
