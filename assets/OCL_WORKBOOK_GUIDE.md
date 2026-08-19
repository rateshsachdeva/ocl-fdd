# OCL Workbook Styling and Presentation Guide

This guide controls **presentation only**. It must never create a category, period, analysis, amount or conclusion that the current data does not support.

## Overall principles

- Professional financial-due-diligence workbook, not a decorative dashboard.
- Clear hierarchy: source/flat-file foundation -> analytical schedules -> checks -> findings/questions.
- Hidden gridlines on all final sheets.
- Freeze panes at the first logical data row.
- Sensible column widths; no clipped key labels and no extreme autofit widths.
- Arial 10pt body as the default workbook font.
- Dark navy headers (`#17365D`) with white bold text.
- Use light blue only for subtotal/section emphasis; avoid excessive fills.
- Source-copy tabs remain protected.

## Financial-model font conventions

- **Blue**: source/hardcoded input values.
- **Green**: inter-sheet links to source/foundation schedules.
- **Black**: formulas and model calculations.

The convention is a visual aid only; it does not change calculation ownership.

## Number formats

Default financial amount format:

```text
#,##0;[Red](#,##0);-
```

- negatives in parentheses;
- zeros displayed as a dash;
- no unnecessary decimal places for full-currency schedules;
- percentages use a consistent 0.0% or 0.0x presentation only where actually required.

## Dynamic balance schedules

- Children appear before the parent subtotal.
- Parent subtotals are formula-driven and visually distinct with a light-blue band / top border.
- `Total OCL` is formula-driven and receives strong navy total treatment.
- Do not create empty categories or rows just because they existed in an old template.
- If residual source amounts genuinely sit within a mapped parent but cannot be assigned to a child, use an explicit `Unallocated within category` concept; never use a plug.
- Group/hide child detail only where it materially improves readability; do not group a trivial number of rows.

## Checks

- `PASS`: green fill / dark-green text.
- `FAIL`: red fill / dark-red text.
- `REVIEW_REQUIRED`: amber.
- `NOT_APPLICABLE`: grey.
- Control rows must make actual, expected and difference visible where available.
- A failed control is never hidden or formatted to look acceptable.

## Mapping / scope transparency

- Mapping decisions remain visible.
- `UNMAPPED` is visibly flagged and easy to locate.
- `SCOPE_EXCLUDED` retains trade payable / financing / out-of-scope rows and lineage.
- Review status and reason remain visible.

## Source tabs

- `SRC_*` tabs are standardized source copies, not client originals.
- Header: grey with white text.
- Values: blue font.
- Sheet protection enabled.
- Source_Record_ID / source file / sheet / cell lineage remains available in the Flat File.

## Findings

- Findings are concise FDD observations supported by numbers.
- High priority receives stronger visual emphasis than medium/low.
- Evidence text must remain readable and wrapped.
- Do not write speculative explanations as facts.

## Management questions

- Questions arise from actual evidence/findings.
- One focused question per row.
- Include a concise rationale / evidence link.
- Use sufficient row height and text wrapping for review.
- Do not ask management to make FDD deal-treatment conclusions.

## Printing / review usability

- Fit key analytical schedules to one page wide where practical.
- Use landscape orientation for wide monthly schedules.
- Keep titles/headers visible and widths stable.
- Workbook must reopen cleanly after final save.

## Quality gate

Presentation is complete only when:

- no formula/lineage/control logic has been changed by styling;
- financial cells use consistent number formats;
- source tabs are protected;
- checks are visually unambiguous;
- key schedules are readable at normal zoom;
- final QA reopens the workbook and confirms no broken `#REF!` formulas.
