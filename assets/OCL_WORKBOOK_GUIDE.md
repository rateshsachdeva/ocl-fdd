# OCL Workbook Formatting Guide

This guide controls **workbook layout and presentation only**. It must never create categories, periods, amounts, analyses, classifications or conclusions that the reconciled data does not support.

## Core workbook rules

- The workbook is generated in code with `openpyxl`; there is no external workbook template.
- Remove the default workbook sheet.
- Build foundation tabs before analysis tabs so formulas reference stable ranges.
- Hide gridlines on all sheets, including Excel View gridlines and printed gridlines.
- Force full recalculation on open.
- Save the principal Excel output as `OCL_Databook.xlsx`.
- Financial totals must be formulas, not typed results.
- Source values are copied into protected `SRC_*` tabs and the model links back to those copies.
- Every source-backed amount must retain an audit trail to source tab / source cell through the Flat File lineage fields.

## Tab order

Front review tabs, when present:

1. `Deal Issues`
2. `Key Findings`
3. `Q&A`
4. `Checks`
5. `Balance by Category`
6. `Monthly Balance`
7. `Roll-forward`
8. `Seasonality`
9. `Item Monthly Charts`
10. `Analysis Summary`

Then foundation and support tabs:

- `Flat File`
- `Movements` when present
- `TB` when present
- `Monthly Flat`
- `Mapping`
- `UNMAPPED`
- `SCOPE_EXCLUDED`
- `SRC_*` source-copy tabs

## Global style

- Font family: Arial.
- Body font size: 8.
- Header font size: 8.
- Main title font size: 14.
- Title text colour: dark navy `#002060`.
- Main table / section fill: KPMG-style blue `#00338D` with white text.
- Column-heading strip fill: light grey `#E1E4E2`.
- Grand-total fill: light grey `#E5E5E5`.
- Flag / review fill: amber `#FFF2CC`.
- Check pass fill: green `#C6EFCE`.
- Check fail fill: red `#FFC7CE`.

Font meaning:

- Black = all displayed financial/model numbers, linked formulas, normal model formulas and standard text.
- Blue = hardcoded/source-style value on protected source/support tabs where source-input convention is useful.
- Green is not used for displayed financial numbers merely because a formula links to another worksheet.
- Grey italic/note text = notes, helper text, source references and hidden check explanations.
- Bold = headings, subtotals, totals, opening balances and key calculated figures.

## Number formats

- Financial amounts: whole currency, negatives in red parentheses, zeros as dashes.
- Percentages: one decimal place where used.
- Multiples: `0.0x`.
- Source values, model amounts, checks, balances, bridge values and finding figures use the financial amount format unless their meaning is percentage/multiple.
- Visible annual and monthly period headings use Excel date format `mmmyy` (for example `Dec24`) whenever the exact/source-backed period-end date can be determined.
- Do not invent an annual period-end date merely to force a date display. If an exact date cannot be determined from the standardized period or confirmed annual-to-monthly alignment, retain the source period label.

## Standard analysis-sheet layout

For analytical review tabs:

- `A1`: `TargetCo - Other Current Liabilities`.
- `A2`: sheet title.
- Column A width: 5 as left margin.
- Main tables start in column B.
- Section/table heading row: typically row 6.
- Column heading row: typically row 7.
- First data row: typically row 8.
- Row 6 uses blue fill / white text.
- Row 7 uses the column-heading style with bottom border.
- Default data row height is compact; wrapped narrative rows expand only as needed.
- Numeric columns align right.
- Use explicit sensible widths rather than uncontrolled auto-fit.

## Foundation tabs

### Flat File / Monthly Flat

- Row 1: title.
- Row 2: headers.
- Data starts row 3.
- Freeze at `A3`.
- Amounts are formula links back to source-copy tabs where source-cell linkage is available.
- Source-linked amount formulas use black font and the financial number format in the finished databook.

### Source tabs

- `SRC_*` tabs are protected source copies.
- Source values are not cleaned or reshaped for presentation.
- Grey tab colour.
- Numeric values use the financial amount format.

## Balance by Category

- Use standard analysis layout.
- Category labels in column B.
- Period columns follow dynamically from available data; do not force fixed FY labels.
- Where exact/source-backed period ends are known, annual and monthly period headings display as `mmmyy` (for example `Dec24`).
- Child/category rows are indented.
- Parent/family subtotal rows are visible, bold and followed by their child/detail rows.
- Sort top-level economic groups from highest to lowest using the latest displayed period. Preserve the source-driven order of children within each group.
- Keep every detail row physically present. Use Excel row outlines, with child rows grouped beneath the parent and collapsed/hidden by default so users can expand them with the outline controls.
- `Total OCL` remains the final visible total row and is bold with light-grey `#E5E5E5` fill and strong borders.
- `UNMAPPED` remains separately visible; never hide it inside mapped subtotals.
- Numeric columns align right and display in black font.

## Roll-forward

- Use standard analysis layout.
- Build only for movement data that actually exists.
- Render one separate table for each dynamic reviewed in-scope category, with actual movement periods across columns in `mmmyy` format.
- Each table contains exactly `Opening`, `Net movement`, `Closing` and `Calculated closing` analytical rows.
- Visible values are formulas linked to the deterministic `Movements` support schedule. The first opening links to source opening; each later opening references the prior displayed closing; calculated closing equals opening plus net movement.
- The deterministic control remains independent of this display schedule; never solve a break with a plug.

## Checks

- Row 1 states that all check values should be zero.
- Row 2 explains the colour convention.
- Header row is row 4.
- PASS is green; FAIL is red; REVIEW_REQUIRED is amber; NOT_APPLICABLE is grey.
- Applicable difference threshold is absolute difference below `0.5`.
- Required hard controls remain the authoritative control set.

## Seasonality

- Use monthly data only when enough history exists.
- Standard analysis layout.
- Compare year-end with trailing 12-month average.
- `YE vs Avg` is year-end / average less 1.
- Peak month is based on the maximum monthly balance.
- The analytical columns after the monthly values are `12M Average`, `Year End`, `YE vs Avg`, `Peak Month` and `Flag`; `YE vs Avg` uses percentage format.
- Preserve the Balance by Category hierarchy and collapsed detail outline, including identical `Total OCL` presentation.
- Flag `YEAR-END SPIKE` above +15% and `YEAR-END DIP` below -15%; otherwise blank.
- Nonblank flags receive amber review formatting.

## Item Monthly Charts

- Use standard analysis layout.
- Include monthly amount grid and LTM 12-month average grid.
- LTM averages appear only once a full 12-month window exists; earlier months remain blank.
- One chart per category.
- Bars: KPMG blue `#00338D`.
- LTM line: amber `#FFC000`.
- Show a visible bottom legend with series names `Monthly balance` and `LTM 12M average`.
- Set bar gap width to `40%`.
- Hide y-axis, remove major gridlines and display blanks as gaps.
- Charts sit below the data grids.

## Deal Issues

- Blue tab.
- All visible narrative is in column A; do not merge cells or display a separate figure row.
- Column A is width 90 and wrapped. Each issue is a vertical title, implication, evidence, evidence limitation and fact-to-establish block, followed by a blank row.
- Deterministic figures and evidence references remain in the analysis artifacts even though the separate workbook figure line is omitted.

## Key Findings

- Standard analysis layout.
- Visible columns are ID, FDD Lens, Area, Metric, FY periods / Item, FDD implication / So what, Evidence, Evidence limitation, Fact to establish and Materiality.
- The four narrative columns use width 50, wrap and top alignment. Generic width logic must not overwrite these widths.
- Findings remain evidence-led; no speculative explanation may be presented as fact.

## Q&A

- Standard analysis layout.
- The Question, Why it matters and Evidence trigger columns use width 50, wrap and top alignment; Management Response remains blank and available for user input.
- Questions are sequentially numbered.
- Theme, question, evidence and response columns wrap.
- Management response is blank for user input.
- Questions must arise from material evidence/findings, not filler.

## Analysis Summary

- Display formula-linked monthly OCL statistics only; do not render the annual balance recap or year-end build/reference table on this sheet.
- Use up to the latest three supported fiscal/calendar years. Prefer confirmed `monthly_to_annual` year ends where available and do not create placeholder years.
- Under each year repeat `Average`, `Minimum`, `Maximum` and `Latest`; all four are formulas linked to Monthly Balance and use financial number formats.
- Preserve hierarchy, subtotals, collapsed detail and the Total OCL treatment. `Std Dev` is not displayed.

## Internal analysis evidence

- Analysis coverage and extended analyses remain in `analysis_evidence.json` for validation and AI interpretation.
- Do not render client-facing `Analysis Coverage` or `Additional Analysis` worksheets; delete legacy copies during rerendering.

## Mapping / exception tabs

### Mapping

- Row 1 explains original-label to category/scope mapping.
- Header row 2; data row 3; freeze `A3`.
- Blank category displays as `UNMAPPED`.
- Non-reviewed rows receive amber emphasis.

### UNMAPPED

- Row 1 explains that unmapped rows remain visible and are excluded from mapped-category subtotals.
- Row 2 contains explanatory note.
- Header row 3; data starts row 4; freeze `A4`.
- Rows use amber emphasis.

### SCOPE_EXCLUDED

- Row 1 explains that excluded rows are retained but excluded from OCL.
- Header row 2; data starts row 3; freeze `A3`.
- Scope and lineage remain visible.

## Structural controls

- Financial analysis must reconcile through the Checks tab.
- Do not edit source data in the workbook.
- Do not silently drop rows.
- Unmapped and out-of-scope records remain visible.
- Mapping, scope, WC/debt and normal/one-off judgments come from reviewed configuration / explicit fallback rules.
- Major analytical totals must trace back through formulas to foundation/source schedules.
- Any new tab must either use the standard analysis layout or clearly follow a consistent foundation/support layout.
