# Embedded fdd-data-preparation runtime

This folder is the integrated upstream data-preparation layer used by the OCL skill.

The user-facing workflow is intentionally simple:

```text
references/source/  ->  fdd-data-preparation  ->  work/data_prep/latest/  ->  OCL workflow
```

The integrated runtime follows the same core boundaries as the standalone `fdd-data-preparation` design supplied for this project:

- source workbooks are read-only;
- source SHA-256 hashes are recorded;
- workbook/sheet structure is inspected before extraction;
- source rows/cells receive persistent `Source_Record_ID` lineage;
- standardized CSVs, metadata, manifest and lineage are published together;
- ambiguous or unclassified material is surfaced in metadata rather than silently dropped;
- OCL-specific scope, taxonomy and FDD judgments remain downstream in `ocl_agent`.

For the one-repository product experience, this embedded runtime includes a deterministic OCL-oriented fast path for common annual, monthly, movement, TB/control and optional context schedules. It does not modify the raw files and does not hard-code a client category universe.

Run the complete skill from the repository root with:

```bash
python run_all.py
```

The raw client files belong only in `references/source/`. Intermediate data-preparation publications are generated under `work/data_prep/` and the principal deliverable is `output/OCL_Databook.xlsx`.
