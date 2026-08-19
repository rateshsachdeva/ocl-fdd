# OCL Financial Due Diligence Skill

## Objective

Build a traceable, dynamically structured Other Current Liabilities financial-due-diligence databook from raw client source files, then produce evidence-based analysis, management questions and a secondary PowerPoint report from one shared reconciled OCL model.

Normal use remains simple:

```text
put raw files in references/source/
        ↓
run the root workflow
        ↓
output/OCL_Databook.xlsx
```

`run_all.py` is the public launcher.

## Architecture

```text
references/source/
        ↓
FULL fdd-data-preparation
  deterministic profile/staging
        ↓
  AI dataset understanding + processing plan
        ↓
  deterministic execution + completeness + lineage
        ↓
work/data_prep/output/latest/
  standardized long/flat database(s)
        ↓
OCL semantic understanding + reviewed OCL judgments
        ↓
hard OCL controls
        ↓
Part 1 — dynamic formula-driven databook
        ↓
Part 2 — deterministic evidence analysis
        ↓
Part 3 — evidence-driven management questions
        ↓
final workbook styling + deterministic QA
        ↓
output/OCL_Databook.xlsx
        ↓
Part 4 — secondary OCL_Report.pptx
```

Keep the implementation light: standard-library CSV/JSON, `openpyxl`, `python-pptx`, bounded inspection and streaming where useful. Do not add pandas, a second raw-workbook parser or an embedded model-provider API without a demonstrated need.

## AI and Python responsibility split

The workflow is AI-powered but model-provider-neutral.

**Python owns:** source discovery, SHA-256 binding, structural profiling, deterministic staging, artifact validation, deterministic reshaping, completeness, lineage, financial calculations, controls and rendering.

**The active AI host owns:** contextual dataset understanding, the source-bound processing plan, OCL semantic interpretation, proposed scope/mapping/WC-debt/normality judgments and optional prose refinement.

**Human-reviewed decisions own final FDD meaning.** Do not silently replace an existing reviewed decision.

A plain terminal run may pause at an `AI_HOST` checkpoint. A capable coding/agent host should read the handoff artifact, perform the required reasoning, write the requested artifact(s), and rerun the same root workflow without requiring the user to manage the internal stages.

## Data-preparation boundary

`fdd-data-preparation/` is the only layer that understands raw Excel structure.

It must:

- treat raw workbooks as read-only;
- bind the workflow to source SHA-256 hashes;
- structurally profile files/sheets/regions before interpretation;
- let AI identify logical datasets, grain and field meaning from current evidence;
- let AI author a deterministic processing plan;
- let Python validate and execute that exact plan;
- preserve blank versus zero and source grain unless explicitly changed by an approved plan;
- prove source-file, source-region, source-row, output-record and lineage completeness;
- publish standardized CSV(s), `execution_manifest.json`, `databook_metadata.json`, `lineage.csv` and `field_lineage.csv`.

The output filename and physical client layout are not the OCL contract. OCL consumes the published standardized package and its metadata/lineage.

Do not add another OCL-specific raw Excel parser or growing header-alias dictionary.

## OCL semantic boundary

Once a standardized package exists, Part 1 determines how the available datasets support OCL analysis.

Dataset usages remain:

- `OCL_RECORDS`
- `MONTHLY_RECORDS`
- `MOVEMENT_RECORDS`
- `TB_CONTROL`
- `REVENUE_CONTEXT`
- `PAYROLL_CONTEXT`
- `IGNORE`

The AI host confirms package-specific field roles and alignments from current standardized evidence. Python validates the resulting `semantic_handoff.json` before using it.

Required roles for OCL/monthly records are `source_record_id`, `period`, `amount`, `source_label`. Optional roles include `source_code`, `entity`, `currency`. Movement records additionally require `movement_type` and exact source-specific movement rules. TB/control filters and monthly/movement period alignments must be explicit; never fuzzy-guess them.

## Non-negotiable databook rules

### Source fidelity

- Never invent financial amounts, balancing figures or plugs.
- Preserve `Source_Record_ID` and available upstream lineage.
- Foundation amounts link by Excel formula to protected standardized `SRC_*` source-copy tabs.
- Invalid, unknown, unmapped and excluded records remain visible; no silent drop.
- `references/source/` remains ignored by Git.

### OCL judgment

Scope is decided before category treatment. Explicit scope outcomes include:

- `IN_SCOPE`
- `TRADE_PAYABLE`
- `FINANCING`
- `OUT_OF_SCOPE`
- `REVIEW_REQUIRED`

Only categories/hierarchy genuinely present in the current source are created. No legacy OCL category universe is imposed.

Canonical management/FDD views are `working_capital`, `debt_like`, `neither`; normality values are `normal`, `one_off`.

AI proposals must remain reviewable. Human-reviewed decisions override proposals. Trade payables, financing and other excluded items remain visible for reconciliation rather than being dropped.

### Dynamic workbook

Do not use `Template.xlsx` or another fixed Excel workbook as the structural basis. Actual standardized data, available periods, reviewed hierarchy and supported analyses determine workbook structure.

Relevant sheets may include:

- `Flat File`
- `Balance by Category`
- `Monthly Flat`
- `Monthly Balance`
- `Roll-forward`
- `Checks`
- `Mapping`
- `UNMAPPED`
- `SCOPE_EXCLUDED`
- protected `SRC_*` tabs
- `Analysis Summary`
- `Key Findings`
- `Management Questions`

Children appear before parent subtotals. Parent subtotals and Total OCL are formula-driven. Unsupported analyses do not create empty sheets.

### Reconciliation is a hard gate

Applicable controls must pass within tolerance before final publication. Missing prerequisites are `NOT_APPLICABLE`; genuine unresolved evidence is `REVIEW_REQUIRED`; actual breaks are `FAIL`.

Controls include, where applicable:

- mapped categories to in-scope OCL;
- record coverage / no silent loss;
- listing to explicitly bound TB/control;
- scope reconciliation;
- WC/debt-like completeness;
- roll-forward and closing-to-listing reconciliation;
- explicit period continuity;
- monthly closing to annual closing;
- semantic-build and judgment-completion checks.

Never solve a failed control with a plug or by widening tolerance.

## Part 2 — Analysis

Part 2 calculates only from the reconciled Part 1 model. Use only analyses genuinely supported by the data, such as annual/category movements, concentration, monthly variability, new/cliff/stale balances, reviewed debt-like/one-off treatments and optional revenue/payroll context.

Do not fabricate a business explanation. Numeric evidence comes from the reconciled model; prose may be refined without changing that evidence.

## Part 3 — Management questions

Questions arise only from actual findings. Ask one focused operational/evidential point per question. Do not ask questions merely to fill a sheet, and do not ask management to decide the FDD deal treatment.

Questions remain embedded in `OCL_Databook.xlsx`.

## Workbook presentation

Presentation is controlled separately from financial structure. Apply the project styling guide without creating unsupported content:

- dark blue headers with white text;
- professional Arial-style body formatting;
- accounting number formats, negatives in parentheses, zeros as dashes;
- blue source/hardcoded inputs, green inter-sheet links, black calculations;
- clear parent subtotal and Total OCL treatment;
- unambiguous green/red/amber/grey control statuses;
- hidden gridlines, freeze panes, sensible widths and print setup;
- protected source-copy tabs;
- visible `UNMAPPED` and `SCOPE_EXCLUDED` sections;
- readable findings and management questions.

## Part 4 — Report

`output/OCL_Report.pptx` is secondary and is built from the same reconciled model. Unsupported analyses do not create empty slides. The Excel databook is the principal product.

## Final QA

After analysis/questions and styling, reopen the workbook and independently check mandatory control/lineage sheets, source-copy protection, required record fields, blocking controls, broken `#REF!` formulas and successful reopen. QA remains an internal artifact under `work/`.

## Completion rule

The workflow is complete only when:

1. raw sources remain unchanged;
2. full data preparation publishes standardized data with metadata/manifest/lineage and completeness passed;
3. OCL semantics and required judgments are resolved from the standardized package;
4. every relevant OCL record has explicit disposition;
5. applicable hard controls pass and unsupported controls are explicitly `NOT_APPLICABLE`;
6. the databook reopens cleanly and passes final QA;
7. analysis and questions use the same reconciled model; and
8. `output/OCL_Databook.xlsx` is produced in the required FDD-style format and quality.
