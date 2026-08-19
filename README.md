# OCL FDD

Dynamic, auditable financial due-diligence workflow for Other Current Liabilities.

```text
fdd-data-preparation
        ↓
approved standardized data + metadata + lineage
        ↓
OCL semantic handoff + reviewed judgments + hard controls
        ↓
dynamic OCL_Databook.xlsx
        ↓
analysis → management Q&A → OCL_Report.pptx
```

The Excel databook has **no fixed structural template**. Actual data, reviewed OCL judgment, available periods, real hierarchy and supported analyses determine what exists. Deterministic Python calculates/reconciles/renders; the AI host interprets and drafts; human-reviewed config remains authoritative.

The core intentionally stays light: standard-library CSV/JSON plus `openpyxl`, streaming row processing, bounded review samples, no pandas, no embedded LLM API and no second raw-source parser.

Run with:

```bash
python run_all.py --data-prep-output <path-to-fdd-data-preparation/output/latest>
```

If the two repos are side-by-side and the upstream `output/latest` exists, `python run_all.py` can discover it automatically.

See `SKILL.md` for the operating contract and `_how_it_works.md` for the workflow.
