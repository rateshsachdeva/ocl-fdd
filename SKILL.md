# OCL Financial Due Diligence Skill

## Objective

Build a traceable, dynamically structured Other Current Liabilities financial due-diligence databook, analysis, management questions and PowerPoint report from one shared reconciled OCL data model.

## Operating model

`run_all.py` is the public launcher. The normal upstream input is an approved `fdd-data-preparation` publication.

```text
fdd-data-preparation
        ↓
standardized CSVs + metadata + lineage
        ↓
Part 1 — semantic handoff → reviewed OCL judgments → controls → dynamic databook
        ↓
shared reconciled OCL data model
        ↓
Part 2 — deterministic evidence analysis
        ↓
Part 3 — evidence-driven management questions
        ↓
Part 4 — dynamic PowerPoint report
```

Keep the implementation light: standard-library CSV/JSON, `openpyxl`, `python-pptx`, bounded interpretation samples and streaming row construction. Do not add pandas, a second raw-workbook parser or an embedded LLM API without a demonstrated need.

## Non-negotiable databook rules

### Source fidelity

- Never invent financial amounts, balancing figures or plugs.
- Do not alter raw client source workbooks.
- Preserve `Source_Record_ID` and available upstream lineage.
- Databook amounts link by Excel formula to protected standardized `SRC_*` source-copy tabs.
- Invalid, unknown, unmapped and excluded records remain visible; no silent drop is permitted.

### Human judgment owns meaning

- Reviewed human decisions override AI suggestions.
- Scope, mapping/hierarchy, WC/debt-like treatment and normal/one-off treatment remain reviewable outside hidden code.
- AI-host suggestions are `PROPOSED` until reviewed.
- Existing reviewed config is never regenerated away.
- Judgment keys may use source label + source code + entity where necessary.

Canonical reviewed values:

- management/FDD view: `working_capital`, `debt_like`, `neither`;
- normality: `normal`, `one_off`.

### Dynamic workbook

Do not use `Template.xlsx` or another fixed Excel workbook as the structural basis. Do not hard-code legacy OCL categories, fixed periods or empty analytical sections.

Actual standardized data + reviewed judgment determine periods, categories, hierarchy, sheets and supported analysis. A separate OCL styling guide controls appearance only; it may not create financial content.

### Reconciliation is a hard control

Applicable controls must pass within tolerance before Part 1 publishes the final databook. Missing prerequisites are `NOT_APPLICABLE`; available-but-unresolved prerequisites are `REVIEW_REQUIRED`.

Controls include, where applicable:

- mapped categories to in-scope OCL;
- record coverage / no silent loss;
- listing to explicitly bound TB control;
- scope reconciliation to explicitly bound control;
- WC/debt-like completeness;
- explicit roll-forward and closing-to-listing reconciliation;
- explicit period continuity;
- monthly closing to annual closing;
- semantic-build and judgment-completion checks.

Never guess a TB control row, movement sign convention, period alignment or expected period sequence.

## Part 1 state machine

### `AWAITING_SEMANTIC_HANDOFF`

Python writes `output/OCL_Input_Review.xlsx` and `output/semantic_handoff_draft.json`. The AI host inspects current metadata/data evidence, assigns dataset usages and field roles, then writes package-specific `config/semantic_handoff.json` with `status: CONFIRMED`.

### `AWAITING_JUDGMENT_REVIEW`

Python writes `output/OCL_Stage2_Review.xlsx` and `output/OCL_Review_Context.json`. Missing OCL scope/mapping/WC-debt/normality judgments are reviewed without overwriting prior reviewed decisions.

### `AWAITING_CONTROL_ALIGNMENT`

One or more hard controls require explicit evidence/alignment or contain a genuine break. Never solve a break with a plug.

### `DATABOOK_READY`

Part 1 creates `output/OCL_Databook.xlsx`. Relevant sheets can include `Flat File`, `Balance by Category`, monthly sheets only when monthly data exists, `Roll-forward` only when explicitly supported, `Checks`, `Mapping`, `UNMAPPED`, `SCOPE_EXCLUDED`, and protected `SRC_*` tabs.

## Semantic handoff contract

Dataset usages are `OCL_RECORDS`, `MONTHLY_RECORDS`, `MOVEMENT_RECORDS`, `TB_CONTROL`, `REVENUE_CONTEXT`, `PAYROLL_CONTEXT`, and `IGNORE`.

For OCL/monthly records, required roles are `source_record_id`, `period`, `amount`, `source_label`. Optional roles include `source_code`, `entity`, `currency`.

For movement records, `movement_type` is also required. Movement interpretation must use exact reviewed `movement_rules`, for example:

```json
{
  "movement_rules": {
    "Opening": {"role": "OPENING", "multiplier": 1},
    "Additions": {"role": "FLOW", "multiplier": 1},
    "Utilisation": {"role": "FLOW", "multiplier": -1},
    "Closing": {"role": "CLOSING", "multiplier": 1}
  }
}
```

Use top-level `movement_to_annual` to align movement closing periods to annual/listing periods. Use `monthly_to_annual` for monthly year-end alignments. `expected_annual_periods` and `expected_monthly_periods` may be supplied for deterministic continuity checks.

Source-backed TB/scope checks use exact dataset, period/amount fields and exact filters. They are never keyword-discovered.

Revenue/payroll context is optional. It is used only when the semantic handoff explicitly binds its period and amount fields; absence never blocks the workflow.

## Part 2 — analysis

Part 2 calculates only from the reconciled Part 1 model. Supported evidence includes, when data supports it:

- annual OCL movements;
- category movements;
- concentration;
- monthly variability;
- new balances;
- balances falling to nil;
- stale monthly balances;
- reviewed debt-like and one-off classifications;
- OCL-to-revenue/payroll context ratios when optional context exists.

Do not fabricate a business explanation. Deterministic code establishes the numeric observation; an AI host may improve language without changing the evidence.

## Part 3 — management questions

Questions must arise from an actual finding. Do not ask questions for the sake of asking them.

- Request one focused operational explanation/evidence item per question.
- New item: ask what event/calculation gave rise to it.
- Cliff to nil: ask how it was settled or released.
- Stale balance: ask whether it remains a valid outstanding obligation.
- Movement/spike: ask for the primary underlying driver.
- Concentration: request a breakdown of underlying obligations including settlement timing.
- Do not ask management to decide whether an item is debt-like, one-off, a purchase-price adjustment or other deal treatment.
- Do not routinely demand roll-forwards or invoices unless the evidence specifically requires them.

## Part 4 — report

Part 4 produces `output/OCL_Report.pptx` from the same analysis model. It creates only supported slides/tables; unsupported analyses do not create empty slides. The future report styling guide may change presentation without changing financial content.

## Config ownership

`config/` is the human-owned meaning layer: `mapping.csv`, `judgment_scope.csv`, `judgment_wc_debt.csv`, `line_item_notes.csv`, `column_memory.json`, optional revenue/payroll inputs and package-specific `semantic_handoff.json` (not committed).

## Completion rule

The workflow is complete only when:

1. source/lineage coverage is preserved;
2. required judgments are reviewed;
3. all applicable hard controls pass;
4. unsupported controls are explicitly `NOT_APPLICABLE` rather than fabricated;
5. the databook reopens cleanly;
6. Parts 2–4 consume the same reconciled Part 1 model;
7. `OCL_Databook.xlsx` and `OCL_Report.pptx` are produced without forcing unsupported content.
