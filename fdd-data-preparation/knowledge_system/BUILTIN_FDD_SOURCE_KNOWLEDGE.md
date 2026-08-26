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

---

# 1. Common difficult workbook structures

Expect financial source packs to contain one or more of the following without treating any one pattern as mandatory:

- title/preamble rows above the real header;
- merged cells, spacer rows and presentation-only sections;
- hidden rows or columns;
- formulas, subtotals and hierarchy rows mixed with detail;
- Actual / Budget / Variance blocks;
- annual TBs split across sheets such as FY23 / FY24 / FY25;
- monthly files split by month, year, legal entity or business unit;
- equivalent datasets with different worksheet names across files;
- one sheet containing multiple independent logical datasets;
- multiple header rows or repeated headers inside long reports;
- wide monthly layouts that need unpivoting;
- long transaction layouts that should remain long;
- amounts expressed in units, thousands or millions;
- debit/credit conventions that differ between datasets;
- dates represented as Excel dates, text month labels, fiscal-period codes or year-end labels;
- hierarchy expressed through indentation, subtotal formulas, blank parent cells or repeated labels.

Do not infer a dataset solely from filename or worksheet name. Use structure, headings, samples, cardinality, formulas, neighbouring fields and workbook context together.

# 2. Ambiguous field-name patterns

The following headings are deliberately ambiguous and must be interpreted contextually:

- `Cat`, `Category`, `Map1`, `Mapping`, `Classification`;
- `Description`, `Desc`, `Name`, `Text`;
- `Code`, `Account`, `GL`, `Ledger`, `Item`;
- `Amount`, `Balance`, `Value`, `Actual`;
- `Period`, `Month`, `FY`, `Date`.

For example, `Description` may mean account description, vendor, invoice narrative, project, provision description, customer, employee category or something else. `Cat`/`Map1` may be an account taxonomy in one dataset and a reporting mapping in another.

Interpret fields using:

- sample values;
- neighbouring columns;
- workbook/sheet context;
- primitive datatype and cardinality;
- hierarchy/indentation evidence;
- formatting/formula clues;
- relationship to other sheets/files;
- reusable prior knowledge as supporting evidence only.

# 3. Likely dataset roles in an OCL / accrued-liabilities engagement

The AI host should actively look for and preserve these logical roles when evidenced:

## Core balance datasets

- annual trial balance / balance-sheet detail;
- monthly trial balance or monthly OCL balances;
- detailed accrued-liability schedule;
- category / account mapping tables.

## Movement and settlement evidence

- opening / additions / utilisation / releases / closing roll-forward;
- reversals or true-up schedules;
- subsequent-payment / post-close settlement data;
- AP/open-item data;
- invoice or vendor detail linked to accrued obligations.

## Employee-related evidence

- payroll schedules;
- bonus accrual schedules;
- holiday-pay / leave accrual schedules;
- employee-liability detail.

## Operating/P&L context

- monthly P&L or expense data;
- revenue context;
- project/job cost or project profitability data;
- service-line or business-unit P&L;
- expense-category mapping.

## Contract/obligation evidence

- contracts;
- purchase commitments;
- project obligations;
- capex commitments;
- management explanation / call-note datasets when available.

Do not discard these datasets merely because they are not the primary annual OCL balance. Their presence determines which downstream analyses are supported.

# 4. Common OCL scope patterns

Potentially in-scope operating accrued liabilities can include, depending on source evidence:

- payroll / wages / social costs;
- bonus / commission;
- holiday pay / leave;
- agency / temporary staff;
- professional fees;
- utilities;
- rent/property-related accruals;
- freight/logistics;
- marketing;
- project/service-delivery costs;
- subcontractor costs;
- capex creditors where transaction treatment must be assessed separately;
- other incurred-but-unpaid operating obligations.

Nearby balances frequently require exclusion or separate treatment rather than automatic OCL inclusion:

- trade creditors / normal AP;
- VAT / sales tax;
- corporation/income tax;
- financing interest;
- lease liabilities;
- borrowings;
- deferred revenue / contract liabilities;
- customer credits;
- provisions that are economically distinct from routine accruals;
- financing/debt-like balances.

Use economic substance and available evidence, not keyword-only inclusion/exclusion.

# 5. Benchmark-derived structural lessons: healthcare-style management packs

A difficult management-report pack may contain:

- four or more separate workbooks with independently structured datasets;
- management-report presentation rather than clean database exports;
- multiple blocks, merged cells, blank rows and hidden detail;
- Actual/Budget/Variance structures;
- two independent logical datasets on one `Liability Detail`-type sheet;
- ambiguous `Cat`, `Map1` and `Description` semantics;
- incomplete mappings and hierarchy/subtotal rows.

Typical analytical patterns worth preserving evidence for include:

- seasonal holiday-pay / leave accruals;
- volatile agency-staff accruals;
- relatively stable utility accruals;
- stale professional-fee balances;
- liabilities retained for closed locations/sites;
- new service-line or business-unit accruals appearing in a later year;
- location-specific accrual build-ups;
- property accrual seasonality;
- category mix shifts despite stable total OCL;
- nearby out-of-scope VAT, tax, lease, deferred-revenue, customer-credit, financing-interest and trade-creditor balances.

These are hypotheses to test, not conclusions to assume.

# 6. Benchmark-derived structural lessons: engineering/project-style packs

A harder engineering/project source pack may combine:

- heterogeneous annual TBs;
- monthly balances supplied in different formats by period/entity;
- large project accrual schedules;
- corporate accrual schedules;
- employee accrual schedules;
- AP/open items;
- post-close settlement or subsequent-payment data;
- contracts/commitments;
- monthly P&L;
- project/job-level financial data;
- project status / closed-project indicators;
- explicit movement/reversal information.

Preserve keys that could connect these datasets, such as:

- entity;
- GL/account code;
- account description;
- project/job ID;
- vendor/counterparty;
- employee/category;
- invoice/document/obligation ID;
- booking/accrual date;
- settlement/payment date;
- movement type;
- contract reference;
- expense category;
- currency;
- period.

Do not aggregate away a join key before determining whether it is required for adequacy, utilisation, completeness, duplicate or settlement testing.

# 7. Evidence requirements for downstream analyses

The Dataset Map / Processing Plan should preserve enough evidence to allow downstream Python to label each analysis `SUPPORTED`, `PARTIAL`, `REFERENCE_ONLY` or `UNSUPPORTED`.

## Usually supported from monthly OCL balances

- monthly volatility;
- seasonality when sufficient history exists;
- year-end build/unwind;
- recurring/intermittent balance patterns;
- persistent accumulation/release;
- normalization references versus average/median;
- concentration;
- category mix shift;
- stale-balance proxy (not true aging).

## Requires explicit movement evidence

- utilisation/burn-down;
- additions versus releases;
- reversal patterns;
- opening-to-closing roll-forward.

## Requires linked P&L / expense context

- accrual-to-expense ratios;
- expense-run-rate comparison;
- certain adequacy indicators.

## Requires detailed obligation / settlement evidence

- true aging;
- adequacy against underlying obligation;
- missing-accrual completeness;
- duplicate/double-counting tests;
- subsequent settlement validation;
- invoice/vendor/contract-level completeness.

Never manufacture an unsupported conclusion from aggregate balance data.

# 8. FDD mechanics to preserve in the data model

Where evidence exists, retain data needed to test:

- annual and monthly OCL balances;
- movement/addition/utilisation/release roll-forwards;
- subsequent settlement;
- aging;
- adequacy;
- completeness / missing accruals;
- duplicates / double counting;
- one-off / normality indicators;
- working-capital versus debt-like treatment;
- QoE releases or historical over/under-accrual indicators;
- closed-site / closed-project liabilities;
- project mobilisation/build patterns;
- category/location/project mix shifts;
- capex-creditor treatment;
- FX or currency effects where relevant.

# 9. Negative-test discipline

Some source packs deliberately contain nearby balances or patterns that look suspicious but are valid. The AI host must preserve evidence for negative tests and avoid converting every anomaly into an issue.

Examples of negative-test logic:

- a seasonal balance may be appropriate for the reporting date;
- a bonus accrual may be normal when supported by payroll/bonus evidence;
- a recurring project accrual may be valid if utilisation/settlement supports it;
- similar amounts are not duplicates without matching obligation evidence;
- a stale-looking aggregate balance is not true aging without dates;
- a large release is not automatically an EBITDA adjustment;
- a capex creditor may require debt-like treatment but should not be assumed without transaction classification evidence.

# 10. Performance guidance for difficult packs

To keep the understanding stage efficient:

- start from deterministic regions/profile/samples, not broad workbook reading;
- recognize known layout patterns quickly;
- group equivalent sheets/files into logical datasets when evidence supports it;
- infer likely field roles from samples/cardinality/context before requesting inspection;
- inspect only unresolved fields/regions that could materially change processing;
- do not inspect every month/file independently when deterministic profiles show they share a schema;
- do not ask the AI host to calculate/reconcile amounts that Python will calculate later;
- preserve supporting datasets and join keys in the processing plan rather than deeply analysing them during planning;
- state uncertainty explicitly and move on when it does not block deterministic processing.

# 11. Priority of evidence

Use this precedence:

1. current source contents and deterministic profile;
2. current prepared samples / structural evidence;
3. validated relationships/reconciliations in the current package;
4. reviewed user corrections for the current package;
5. reusable learned knowledge;
6. this built-in reference knowledge.

Built-in knowledge is the lowest-priority evidence layer. Its purpose is speed and recognition, never assumption.
