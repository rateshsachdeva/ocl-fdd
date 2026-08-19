# OCL FDD

Dynamic, auditable financial due-diligence workflow for Other Current Liabilities (OCL).

This repository intentionally does **not** use a fixed Excel template as the structural basis of the databook. Workbook structure is derived from standardized source data, reviewed OCL judgments, available periods, actual hierarchy, and analyses supported by the engagement data.

Core principles:

- source numbers are never invented;
- source lineage is preserved;
- nothing is silently dropped;
- human-reviewed configuration overrides AI suggestions;
- reconciliation is a hard control;
- deterministic Python performs calculations and workbook rendering;
- Part 1 Databook, Part 2 Analysis, Part 3 Q&A, and Part 4 Report share one reconciled data model;
- `python run_all.py` remains the main entry point.

The detailed architecture is implemented on a feature branch before being merged to `main`.
