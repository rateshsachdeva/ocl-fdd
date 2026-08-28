# Built-in FDD Source-Understanding Knowledge

Purpose: give the AI host strong starting hypotheses for difficult financial-due-diligence source packs so it does not rediscover common structures from scratch on every engagement.

This is **reference knowledge, not golden truth**. Current source evidence, deterministic profiling, reconciliation and completeness controls always override this file. Never force a prior pattern onto a new source just because it resembles a benchmark.

## Fast-start rule

When this file is referenced during `UNDERSTAND_AND_PLAN`:

1. Read the deterministic profile, prepared samples and this knowledge file first.
2. Match the current source against known structural and accounting patterns below.
3. Reuse a known interpretation only when the current evidence supports it.
4. Do not browse raw workbooks broadly just to rediscover patterns already evidenced by the profile/samples.
5. Request targeted inspection only for a specific unresolved ambiguity that could materially change the Dataset Map or Processing Plan.
6. Preserve all potentially useful supporting datasets even when they are not the primary OCL listing.
7. Never use benchmark-specific expected outcomes, amounts or labels as conclusions for the current engagement.

## Common difficult workbook structures

Expect source packs to contain combinations of title/preamble rows above the real header, merged cells, spacer rows, hidden rows/columns, formulas/subtotals, Actual/Budget/Variance blocks, FY-partitioned TB sheets, monthly files split by period/entity, equivalent datasets with different names, multiple independent datasets on one sheet, repeated headers, wide layouts that require unpivoting, long transaction layouts, mixed scale/units, varying debit/credit conventions and hierarchy expressed through indentation or subtotal formulas.

Do not infer a dataset solely from filename or worksheet name. Use structure, headings, samples, cardinality, formulas, neighbouring fields and workbook context together.

## Ambiguous field-name patterns

Treat headings such as `Cat`, `Category`, `Map1`, `Mapping`, `Classification`, `Description`, `Desc`, `Name`, `Text`, `Code`, `Account`, `GL`, `Ledger`, `Item`, `Amount`, `Balance`, `Value`, `Actual`, `Period`, `Month`, `FY` and `Date` as context-dependent.

For example, `Description` may mean account description, vendor, invoice narrative, project, provision description, customer or employee category. `Cat`/`Map1` may be an account taxonomy in one dataset and a reporting mapping in another.

Interpret fields using sample values, neighbouring columns, workbook/sheet context, datatype/cardinality, hierarchy/indentation evidence, formatting/formula clues, relationships to other sheets/files and reusable prior knowledge as supporting evidence only.

## Likely dataset roles in OCL / accrued-liabilities work

Actively look for and preserve these logical roles when evidenced:

- annual trial balance / balance-sheet detail;
- monthly trial balance or monthly OCL balances;
- detailed accrued-liability schedules;
- category/account mappings;
- opening/additions/utilisation/releases/closing roll-forwards;
- reversals/true-ups;
- subsequent-payment/post-close settlement data;
- AP/open items and invoice/vendor detail;
- payroll, bonus and holiday-pay schedules;
- monthly P&L/expense data;
- revenue context;
- project/job cost, profitability or status data;
- contracts, purchase commitments, project obligations and capex commitments;
- management explanation/call-note datasets when available.

Preserve useful join keys such as entity, GL/account, description, project/job ID, vendor/counterparty, employee/category, invoice/document/obligation ID, booking/accrual date, settlement/payment date, movement type, contract reference, expense category, currency and period.

Do not aggregate away a join key before determining whether it is required for adequacy, utilisation, completeness, duplicate or settlement testing.

## Common OCL scope patterns

Potential operating accrued liabilities can include payroll/wages/social costs, bonus/commission, holiday pay/leave, agency staff, professional fees, utilities, property/rent accruals, freight/logistics, marketing, project/service-delivery costs, subcontractor costs, capex creditors requiring separate transaction treatment and other incurred-but-unpaid operating obligations.

Nearby balances frequently require exclusion or separate treatment: trade creditors/AP, VAT/sales tax, corporation/income tax, financing interest, lease liabilities, borrowings, deferred revenue/contract liabilities, customer credits and economically distinct provisions.

Use economic substance and evidence rather than keyword-only rules.

## Healthcare-style difficult management packs

A difficult management-report pack may contain multiple workbooks, management-report presentation rather than clean exports, merged/hidden/presentation rows, Actual/Budget/Variance structures, multiple logical datasets on one `Liability Detail`-type sheet, ambiguous `Cat`, `Map1` and `Description` semantics, incomplete mappings and hierarchy/subtotal rows.

Useful hypotheses to test include seasonal holiday-pay/leave accruals, volatile agency-staff accruals, relatively stable utility accruals, stale professional-fee balances, liabilities for closed locations/sites, new service-line/business-unit accruals, location-specific build-ups, property accrual seasonality, category mix shifts and nearby out-of-scope VAT, tax, lease, deferred-revenue, customer-credit, financing-interest and trade-creditor balances.

These are hypotheses to test, not conclusions to assume.

## Engineering/project-style difficult packs

A harder project source pack may combine heterogeneous annual TBs, monthly balances in different formats, project/corporate/employee accrual schedules, AP/open items, post-close settlement/subsequent-payment data, contracts/commitments, monthly P&L, project/job data, project-status/closed-project indicators and explicit movement/reversal information.

Preserve evidence needed for movement, utilisation, releases, settlement, aging, adequacy, completeness, duplicates, debt-like classification, QoE releases and reconciliation when those datasets exist.

## Evidence requirements for downstream analysis

From monthly OCL balances, downstream Python can usually support monthly volatility, seasonality with sufficient history, year-end build/unwind, recurring/intermittent patterns, persistent accumulation/release, normalization references, concentration, category mix shift and stale-balance proxies.

Explicit movement evidence is needed for utilisation/burn-down, additions/releases, reversal patterns and opening-to-closing roll-forwards.

Linked P&L/expense context is needed for accrual-to-expense and expense-run-rate comparisons.

Detailed obligation/settlement evidence is needed for true aging, adequacy against obligation, missing-accrual completeness, duplicate/double-counting testing and subsequent-settlement validation.

Downstream analysis must label evidence availability `SUPPORTED`, `PARTIAL`, `REFERENCE_ONLY` or `UNSUPPORTED`; never manufacture an unsupported conclusion from aggregate balances.

## Negative-test discipline

Some source packs deliberately contain suspicious-looking but valid patterns. Preserve evidence for negative tests and avoid turning every anomaly into an issue.

Examples: a seasonal balance may be appropriate; a normal bonus accrual may be supported by payroll evidence; a recurring project accrual may be valid if utilisation/settlement supports it; similar amounts are not duplicates without obligation evidence; a stale-looking aggregate balance is not true aging without dates; a large release is not automatically an EBITDA adjustment; a capex creditor may require debt-like treatment but should not be assumed without transaction evidence.

## Performance guidance

- Start from deterministic regions/profile/samples, not broad workbook reading.
- Recognize known layout patterns quickly.
- Group equivalent sheets/files when the profile supports a common schema.
- Infer likely field roles from samples/cardinality/context before requesting inspection.
- Inspect only unresolved fields/regions that could materially change processing.
- Do not inspect every month/file independently when deterministic profiles show the same schema.
- Do not ask AI to calculate/reconcile amounts that Python owns.
- Preserve supporting datasets and join keys in the plan instead of deeply analysing them during planning.
- State uncertainty explicitly when it does not block deterministic processing.

## Priority of evidence

Use this precedence:

1. current source contents and deterministic profile;
2. current prepared samples / structural evidence;
3. validated current-package relationships/reconciliations;
4. reviewed current-package user corrections;
5. reusable learned knowledge;
6. this built-in reference knowledge.

Built-in knowledge is the lowest-priority layer. Its purpose is speed and recognition, never assumption.
