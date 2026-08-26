# OCL FDD Analysis Framework

## Purpose

This is the analytical decision framework for the OCL workstream. It tells the AI partner layer how to interpret Python-created evidence and, equally importantly, what not to conclude when evidence is missing.

The normal architecture remains:

```text
AI #1 understands source/supporting datasets and preserves the evidence
→ Python calculates all supportable OCL analyses
→ AI #2 interprets the combined evidence as an FDD partner
→ Human review owns actual FDD classifications / adjustments where judgment is required
```

Do not add another routine AI stage for analysis.

## FDD lenses

Every supported analysis should ultimately be considered through one or more of these transaction lenses:

1. **Normalized working capital** — is the closing balance representative of the recurring operating run-rate, or is there seasonality, unusual phasing, accumulation or release activity that could distort a peg?
2. **Net debt / equity value** — does the reviewed classification or settlement profile indicate a liability that may sit outside ordinary working capital?
3. **Quality of earnings** — do releases, reversals, one-off balances or unusual accrual mechanics indicate a potential P&L normalization matter?
4. **Completeness / adequacy / validity** — does the evidence suggest balances may be stale, unsupported, duplicated, under-accrued or missing? Only make these conclusions when the required supporting evidence exists.
5. **Settlement and cash conversion** — how quickly are liabilities utilized/paid/released and does the closing balance reflect normal settlement behavior?

## Evidence hierarchy

Use the strongest evidence actually available. Do not substitute a weaker proxy for a stronger test.

### Level A — Core balance history

Can support:

- annual total/category movement;
- category concentration and mix shift;
- monthly volatility;
- seasonality / year-end representativeness;
- year-end build or unwind versus recent run-rate;
- persistence / intermittent balance patterns;
- persistent accumulation diagnostics;
- 12-month average / median normalization references;
- new balances, cliffs to nil and unchanged-balance stale proxies.

Cannot by itself prove:

- true accrual aging;
- adequacy;
- completeness of unrecorded liabilities;
- double counting;
- settlement timing;
- over/under accrual.

### Level B — Explicit movement / roll-forward data

Adds support for:

- additions versus releases/utilisation;
- utilisation rate;
- explicit reversal activity;
- roll-forward mechanics;
- repeated releases or build-up that may be relevant to QoE / NWC;
- settlement-pattern questions where movement definitions genuinely represent settlement.

Do not infer a payment or reversal from a balance decline unless source movement roles explicitly support it.

### Level C — Explicit P&L / expense context

Adds support for:

- accrual-to-expense ratios;
- trend in accrual coverage relative to the linked expense base;
- potential under/over-accrual indicators when the expense relationship is explicitly established.

A generic total-P&L denominator is not a substitute for a specifically linked expense base.

### Level D — Detailed accrual / obligation / settlement evidence

May support, where exact fields/relationships are available:

- true aging / vintage analysis;
- subsequent settlement testing;
- adequacy indicators versus known obligation or settlement amount;
- candidate duplicate accruals using exact identifiers/keys;
- candidate missing accruals from source-backed unmatched obligations/subsequent payments;
- payroll/bonus or contract-specific adequacy/completeness testing.

If exact evidence/keys are not present, mark the analysis unsupported rather than using fuzzy AI matching to create a financial conclusion.

## How to combine indicators

AI #2 should reason across multiple Python analyses rather than treating each table independently. Examples:

- **Year-end spike + high volatility + closing above 12M average** → closing balance may not represent normalized NWC; establish the operational driver and whether the pattern recurs.
- **Year-end build + persistent accumulation + low utilisation** → could indicate delayed settlement or build-up; do not call it over-accrued without stronger evidence.
- **Material build + explicit post-period reversal/release** → may warrant QoE / NWC attention; establish whether the release reflects settlement, estimate true-up or reversal.
- **Persistent balance + unchanged-balance stale proxy** → validity should be challenged; do not call it aged without actual dates.
- **Large concentration + debt-like classification** → heightened net-debt/equity-value sensitivity and need for settlement evidence.
- **One-off classification + material release/reversal** → consider both QoE and normalized NWC implications.
- **Mix shift toward categories with different settlement behavior** → closing total alone may hide a change in working-capital quality.

These are interpretation patterns, not automatic conclusions.

## Analysis status rules

- `SUPPORTED` — the required evidence exists and Python performed the stated test.
- `PARTIAL` — only a proxy/limited test is available; AI must preserve that limitation.
- `REFERENCE_ONLY` — useful benchmark/run-rate information, but not an FDD adjustment by itself.
- `UNSUPPORTED` — required evidence is absent; do not imply the test was performed or that no issue exists.

## Management-question rule

Only ask a question when the answer could change an FDD conclusion, transaction treatment, or confidence in the balance.

Good questions establish facts such as:

- operational driver;
- calculation basis;
- recurrence;
- settlement timing;
- whether a release was settlement versus reversal;
- whether an obligation remains valid;
- why year-end differs from the normal run-rate;
- what exact obligation supports a material closing balance.

Do not ask management to decide the FDD treatment for us.
