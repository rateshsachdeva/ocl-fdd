# OCL Financial Due Diligence Skill

## Objective

Build a traceable, dynamically structured Other Current Liabilities financial-due-diligence databook from raw client source files, then produce evidence-based analysis, management questions and a secondary PowerPoint report from one shared reconciled OCL model.

The target user experience is:

```text
put files in references/source/
        ↓
python run_all.py
        ↓
output/OCL_Databook.xlsx
```

No separate manual execution of another repository should be required.

## End-to-end operating model

`run_all.py` is the only public launcher.

```text
references/source/
        ↓
embedded fdd-data-preparation
        ↓
work/data_prep/latest/
  standardized CSVs + metadata + manifest + lineage
        ↓
canonical OCL semantic handoff
        ↓
reviewable scope + dynamic mapping/hierarchy + WC/debt/normality
        ↓
hard controls
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

Keep the implementation light: standard-library CSV/JSON, `openpyxl`, `python-pptx`, streaming/bounded source processing, no pandas, no duplicate hidden data model, no embedded external LLM API.

## Source and data-preparation boundary

The repository contains `fdd-data-preparation/` as the internal upstream preparation layer.

It owns:

- read-only source discovery;
- source SHA-256 capture and immutability checks;
- workbook/sheet structural inspection;
- deterministic reshape of supported annual, monthly, movement, TB/control and optional context schedules;
- standardized CSV publication;
- `Source_Record_ID` lineage;
- execution manifest and dataset metadata;
- visible reporting of populated sheets that could not be classified safely.

OCL owns the downstream FDD meaning: scope, categories, hierarchy, WC/debt-like treatment, normality, analyses, management questions and final presentation.

Do not modify raw client workbooks. Do not silently drop populated source material.

## Non-negotiable databook rules

### Source fidelity

- Never invent financial amounts, balancing figures or plugs.
- Preserve `Source_Record_ID` and source file/sheet/cell lineage.
- Databook amounts link by Excel formula to protected standardized `SRC_*` source-copy tabs.
- Invalid, unknown, unmapped and excluded records remain visible.
- `references/source/` remains ignored by Git so client data is not committed accidentally.

### Judgment ownership

- Existing human-maintained config rows always override autonomous defaults.
- Scope, mapping/hierarchy, WC/debt-like treatment and normal/one-off treatment remain visible and reviewable.
- Autonomous first-pass rows are allowed so a normal structured source package can complete without forcing the user to populate config first.
- Autonomous rows are package-bound and must be discarded/rebuilt when the source package changes; they must not silently leak between engagements.
- Autonomous defaults are conservative: do not invent a debt-like or one-off treatment without direct evidence.
- Judgment keys may use source label + source code + entity where needed.

Canonical values:

- management/FDD view: `working_capital`, `debt_like`, `neither`;
- normality: `normal`, `one_off`.

### Dynamic workbook

Do not use `Template.xlsx` or another fixed Excel workbook as the structural basis. Do not hard-code a legacy OCL category universe, fixed periods or empty analytical sections.

Actual source-present records and available periods determine categories, hierarchy, sheets and analyses. A presentation layer may style those structures but may not create financial content that the data does not support.

### Reconciliation is a hard gate

Applicable controls must pass within the defined tolerance before final publication. Missing prerequisites are `NOT_APPLICABLE`; actual breaks are `FAIL`; available-but-unresolved evidence is `REVIEW_REQUIRED`.

Controls include, where applicable:

- mapped categories to total in-scope OCL;
- record coverage / no silent loss;
- listing to source-backed TB/control;
- scope reconciliation including explicit trade-payable/financing outcomes;
- WC/debt-like completeness;
- roll-forward and closing-to-listing reconciliation;
- explicit period continuity where an expected sequence is available;
- monthly closing to annual closing;
- semantic-build and judgment-completion checks.

Never fix a failed control with a plug.

## Embedded semantic handoff

The integrated data-preparation fast path emits canonical dataset names and fields. When those canonical outputs are present, `auto_semantics.py` creates the package-specific `config/semantic_handoff.json` deterministically.

Dataset usages remain:

- `OCL_RECORDS`
- `MONTHLY_RECORDS`
- `MOVEMENT_RECORDS`
- `TB_CONTROL`
- `REVENUE_CONTEXT`
- `PAYROLL_CONTEXT`
- `IGNORE`

For OCL/monthly records the required roles are `source_record_id`, `period`, `amount`, `source_label`; optional roles include `source_code`, `entity`, `currency`.

Movement records also require `movement_type`. Exact source movement values are mapped to `OPENING`, `FLOW` or `CLOSING` roles with explicit multipliers. Monthly-to-annual and movement-to-annual alignments are package-specific.

If an external standardized publication is supplied with `--data-prep-output`, the existing semantic-handoff validation contract remains available.

## Part 1 — Databook

Part 1 creates `output/OCL_Databook.xlsx` only after the applicable controls permit publication.

Relevant sheets are data-driven and may include:

- `Flat File`
- `Balance by Category`
- `Monthly Flat`
- `Monthly Balance`
- `Roll-forward`
- `Checks`
- `Mapping`
- `UNMAPPED`
- `SCOPE_EXCLUDED`
- protected `SRC_*` source-copy tabs

Children appear before parent subtotals. Parent rows and total OCL are formula-driven. No nonexistent category or period is created just because it appeared in another engagement.

## Part 2 — Analysis

Part 2 calculates only from the reconciled Part 1 model. Supported evidence may include:

- annual OCL movements;
- category movements;
- concentration;
- monthly variability;
- new balances;
- balances falling to nil;
- stale balances;
- reviewed debt-like/one-off classifications;
- optional OCL-to-revenue or payroll context ratios.

Do not fabricate explanations. Numeric evidence comes from deterministic calculations and workbook formulas.

## Part 3 — Management questions

Questions arise only from actual findings.

- Ask one focused operational/evidential point per question.
- New item: ask what event or calculation gave rise to it.
- Cliff to nil: ask how it was settled/released.
- Stale balance: ask whether the obligation remains valid and outstanding.
- Movement/spike: ask for the primary driver.
- Concentration: ask for composition and settlement timing.
- Do not ask management to decide whether something is debt-like, one-off or a purchase-price adjustment.
- Do not ask questions merely to fill a sheet.

Questions are embedded in the same `OCL_Databook.xlsx`.

## Workbook presentation contract

The final workbook styling layer follows the methodology supplied for this project:

- dark blue headers with white text;
- Arial-style professional body formatting;
- accounting number formats, negative values in parentheses and zeros as dashes;
- blue font for source/hardcoded inputs;
- green font for inter-sheet source links;
- black font for model calculations;
- clear parent subtotal and total OCL treatments;
- green/red/amber/grey control-status presentation;
- hidden gridlines, freeze panes, sensible widths and print setup;
- source-copy tabs protected;
- `UNMAPPED` visibly flagged;
- excluded scope retained visibly;
- findings and management questions formatted for review rather than as raw data dumps.

Presentation never changes the financial logic.

## Part 4 — Report

`output/OCL_Report.pptx` is a secondary deliverable built from the same analysis model. Unsupported analyses do not create empty slides. The Excel databook remains the principal product.

## Final QA

After analysis/questions and styling, the workbook is reopened and independently checked for:

- mandatory control/lineage sheets;
- source-copy protection;
- missing `Source_Record_ID`/amount/scope/review fields;
- blocking Python controls;
- broken `#REF!` formulas;
- successful workbook reopen.

QA is written under `work/final_qa.json`, not as another principal deliverable.

## Completion rule

The workflow is complete only when:

1. raw sources remain unchanged;
2. the standardized publication exists with metadata/manifest/lineage;
3. every relevant OCL record has explicit disposition;
4. applicable hard controls pass and unsupported controls are explicit `NOT_APPLICABLE`;
5. the databook reopens cleanly and passes final QA;
6. analysis and management questions use the same reconciled model;
7. `output/OCL_Databook.xlsx` is produced in the required FDD-style format and quality;
8. the secondary report is produced unless explicitly skipped.
