# OCL PowerPoint Creation Guide

This guide controls the `OCL_Report.pptx` presentation layer. It must not change the financial analysis, materiality conclusions, OCL scope, mapping, controls or source data.

## Generation architecture

```text
AnalysisResult + ManagementQuestion objects
        ↓
PPT renderer
        ↓
OCL_Report.pptx
```

The PPT is generated from the same reconciled model used by the Excel databook. It does not recalculate balances or create unsupported findings.

## Visual style

- Widescreen 16:9, 13.333 x 7.5 inches.
- Arial throughout.
- Title: 18pt, bold, dark navy `#002060`.
- Thin top bar in KPMG blue `#00338D`.
- Body text generally 7–14pt depending on purpose.
- Table headers: KPMG blue with white bold text.
- Alternating table rows: white / light blue.
- Small footer source line on every slide.
- Use grey panels for commentary / key message areas.

## Slide set

The report should stay concise and evidence-led. Supported slides are:

1. Cover / purpose.
2. Key deal issues.
3. Annual snapshot.
4. Roll-forward / movement review, only when supported.
5. Seasonality, only when supported by sufficient monthly data.
6. Top item monthly summary, only when monthly data exists.
7. Questions for management, only when questions exist.
8. Data sources and quality checks.

Unsupported slides are omitted rather than left blank.

## Content rules

- Key deal issues should lead with commercial relevance, not a raw data dump.
- Annual snapshot should combine a table with short key messages.
- Roll-forward should only appear where movement roles are explicit.
- Seasonality should explain year-end representativeness.
- Monthly summary should show only a small number of most relevant items.
- Questions should be evidence-led and have space for management response.
- Footer/source wording should make clear that the report is generated from the reconciled OCL databook.

## Quality rules

- No overlap between tables, charts and commentary.
- No very small unreadable table fonts.
- Amounts use thousands separators and no unnecessary decimals.
- Percentages show one decimal place.
- The PPT must open successfully with `python-pptx` after generation.
- Never create a slide merely to preserve a fixed layout.
