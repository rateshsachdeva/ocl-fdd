# OCL Financial Due Diligence Skill

## Objective

Build a traceable, dynamically structured Other Current Liabilities financial due-diligence databook and, in later parts, analysis, management questions and a report from one shared reconciled OCL data model.

## Operating model

`run_all.py` is the public launcher. The normal upstream input is an approved `fdd-data-preparation` publication.

```text
fdd-data-preparation
        ↓
standardized CSVs + metadata + lineage
        ↓
Part 1: semantic handoff → reviewed OCL judgments → controls → dynamic databook
        ↓
shared reconciled OCL data model
        ↓
Part 2 analysis → Part 3 Q&A → Part 4 report
```

The implementation stays deliberately light: standard-library CSV/JSON processing plus `openpyxl`; bounded sampling for interpretation; streaming row construction; no pandas dependency; no duplicate raw-workbook parser; no embedded LLM API.

## Non-negotiable databook rules

### Source fidelity

- Never invent financial amounts, balancing figures or plug numbers.
- Do not alter raw client source workbooks.
- Preserve `Source_Record_ID` and available upstream lineage.
- In the generated databook, model amounts link by Excel formula to protected standardized source-copy tabs.
- Invalid, unknown, unmapped and excluded records must remain visible; no silent drop is permitted.

### Human judgment owns meaning

- Reviewed human decisions override AI suggestions.
- Scope, mapping/hierarchy, WC/debt-like treatment and normal/one-off treatment must be reviewable outside hidden code.
- AI-host suggestions must be marked `PROPOSED` until reviewed.
- Existing reviewed config must not be overwritten just because a new run occurs.
- Judgment keys may use source label + source code + entity where needed; generic label-only decisions remain supported.

### Dynamic workbook

Do not use `Template.xlsx` or another fixed Excel workbook as the structural basis. Do not hard-code legacy OCL categories, fixed periods, or empty analytical sections.

Workbook content is derived from actual standardized data, reviewed OCL judgments, actual available periods, actual category/hierarchy and analyses genuinely supported by the engagement data.

A separate OCL styling guide governs presentation only. It may not create financial content that the data does not support.

### Reconciliation is a hard control

Applicable controls must pass within the defined tolerance before Part 1 publishes the final databook. Missing prerequisites are reported as `NOT_APPLICABLE`; available-but-unresolved prerequisites are `REVIEW_REQUIRED`.

The framework includes, where applicable:

- mapped categories to total in-scope OCL;
- record coverage / no silent loss;
- OCL listing to an explicitly bound TB control;
- scope reconciliation to an explicitly bound control where available;
- WC/debt-like completeness;
- roll-forward closing to listing closing;
- period continuity;
- monthly closing to annual closing;
- semantic-build and judgment-completion checks.

Never identify a TB control row or period alignment from a loose keyword guess. Bind it explicitly from current source evidence.

## Part 1 state machine

### 1. `AWAITING_SEMANTIC_HANDOFF`

Python validates/profiles the upstream package and writes `output/OCL_Input_Review.xlsx` and `output/semantic_handoff_draft.json`.

The AI host inspects current upstream metadata/source evidence, assigns dataset usages and field roles, and creates `config/semantic_handoff.json` with status `CONFIRMED`. Do not infer a field role from a heading alone.

### 2. `AWAITING_JUDGMENT_REVIEW`

Python writes `output/OCL_Stage2_Review.xlsx` and `output/OCL_Review_Context.json`.

The AI host may propose missing scope/mapping/WC-debt/normality judgments, but must preserve existing reviewed decisions. New proposals remain `PROPOSED` until reviewed. The final databook is blocked while required judgments remain incomplete or unreviewed.

### 3. `AWAITING_CONTROL_ALIGNMENT`

All row-level judgments are complete, but one or more hard controls need explicit source-backed binding/alignment or contain a genuine break. Do not create balancing adjustments. Resolve the evidence or leave the break visible.

### 4. `DATABOOK_READY`

Part 1 creates `output/OCL_Databook.xlsx` dynamically. Relevant sheets may include `Flat File`, `Balance by Category`, monthly sheets only when monthly data exists, `Checks`, `Mapping`, `UNMAPPED`, `SCOPE_EXCLUDED`, protected `SRC_*` standardized source-copy tabs, and later analysis sheets only when supported.

No fixed sheet list is imposed beyond mandatory control/review concepts.

## Semantic handoff contract

`config/semantic_handoff.json` is package-specific and intentionally not committed. Dataset usages are `OCL_RECORDS`, `MONTHLY_RECORDS`, `MOVEMENT_RECORDS`, `TB_CONTROL`, `REVENUE_CONTEXT`, `PAYROLL_CONTEXT`, and `IGNORE`.

For OCL/monthly records, required roles are `source_record_id`, `period`, `amount`, and `source_label`. Optional roles include `source_code`, `entity`, `currency`, and `movement_type`.

Monthly-to-annual period relationships must be explicit. Source-backed TB checks use exact dataset/period/amount fields and exact filter values; they are not keyword-discovered by Python.

## Config ownership

`config/` is the human-owned meaning layer: `mapping.csv`, `judgment_scope.csv`, `judgment_wc_debt.csv`, `line_item_notes.csv`, `column_memory.json`, and optional revenue/payroll inputs. Config defaults may be created only when missing. User-reviewed edits are never regenerated away.

## Four-part repository workflow

- `src/ocl_agent/part1_databook/`: shared OCL model, judgments, controls, dynamic workbook.
- `src/ocl_agent/part2_analysis/`: analytical findings only.
- `src/ocl_agent/part3_qanda/`: management questions only.
- `src/ocl_agent/part4_report/`: PowerPoint reporting only.

Parts 2-4 must consume the same reconciled OCL model produced by Part 1; they must not rebuild independent financial data cuts.
