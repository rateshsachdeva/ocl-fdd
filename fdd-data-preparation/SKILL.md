# Embedded FDD Data Preparation

## Purpose

Prepare raw Excel sources from the parent repository's `references/source/` folder into a standardized, lineage-preserving publication for the downstream OCL skill.

## Contract

- Read source workbooks only; never modify them.
- Capture and re-check SHA-256 around processing.
- Detect structured annual, monthly, movement, TB/control, revenue and payroll schedules from workbook/sheet evidence rather than fixed filenames.
- Preserve source workbook, worksheet, row and amount-cell lineage in `Source_Record_ID`.
- Publish standardized CSVs plus `execution_manifest.json`, `databook_metadata.json`, `lineage.csv` and `field_lineage.csv`.
- Report populated sheets that cannot be classified safely in metadata; do not silently drop them.
- Do not decide OCL category, WC/debt-like treatment, normality or deal treatment here. Those belong to the OCL layer.

The normal user does not run this folder separately. The parent `python run_all.py` orchestrates it automatically.
