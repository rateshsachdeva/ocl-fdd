# OCL FDD

Dynamic, auditable financial due-diligence workflow for Other Current Liabilities.

## Normal use

Put raw client Excel files in:

```text
references/source/
```

Then run the root workflow:

```bash
python run_all.py
```

The architecture is:

```text
raw client Excel
        ↓
fdd-data-preparation
  Python structural profiling
        ↓
  AI dataset understanding + processing plan
        ↓
  deterministic Python execution
  + completeness + lineage
        ↓
work/data_prep/output/latest/
  standardized long/flat CSV(s)
  + metadata + manifest + lineage
        ↓
OCL agent
  AI semantic/OCL judgment where needed
  + deterministic controls/rendering
        ↓
output/OCL_Databook.xlsx
        ↓
analysis + management questions
        ↓
secondary output/OCL_Report.pptx
```

The OCL agent does **not** parse the original client workbook layout. Different client layouts are normalized upstream by `fdd-data-preparation`; OCL begins from the published standardized database.

## AI and Python boundary

This workflow uses AI for contextual understanding. It is model-provider-neutral: the active coding/agent host can be Codex, Claude Code, Copilot or another capable host.

Python owns source profiling, source hashes, validation, deterministic transformations, completeness, lineage, financial calculations, controls and rendering. The AI host owns contextual dataset understanding, the source-bound processing plan, and OCL semantic/judgment review. No external LLM API is embedded in the deterministic Python core.

When run from a plain terminal, `run_all.py` may pause at an `AI_HOST` checkpoint and print the handoff file and required artifacts. When a capable AI coding host is running the skill, it should complete that reasoning checkpoint and rerun the same root command automatically.

## Design principles

- Raw client workbooks remain read-only and should not be committed to Git.
- No fixed Excel structural template drives the final databook.
- No legacy OCL category universe is imposed.
- `Source_Record_ID` lineage is preserved into the standardized database and OCL model.
- No silent drops: relevant source material must be included or explicitly excluded.
- Applicable reconciliations are hard gates; no balancing plugs.
- Human-reviewed OCL decisions remain authoritative.
- Keep the runtime light: standard-library CSV/JSON plus `openpyxl` and `python-pptx`; no pandas and no embedded model API.

An already published data-preparation package can still be supplied directly:

```bash
python run_all.py --data-prep-output <path-to-output/latest>
```

See `SKILL.md` and `_how_it_works.md` for the detailed operating contract.
