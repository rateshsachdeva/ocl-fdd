# Embedded fdd-data-preparation

This is the upstream data-preparation layer used by the OCL skill. Its job is to convert heterogeneous raw Excel sources into reliable standardized long/flat dataset(s) for downstream FDD analysis.

```text
raw Excel
   ↓
Deterministic Python profile + staging
   ↓
Load reusable source-understanding knowledge
   ↓
AI host dataset understanding
   ↓
AI host Dataset Map + Processing Plan
   ↓
Deterministic Python validation + execution
   ↓
Completeness + lineage
   ↓
Publish standardized package
   ↓
Preserve updated reusable knowledge
```

The AI host may be Codex, Claude Code, GitHub Copilot or another capable coding/agent host. The Python runtime itself does not call a model API.

## Reusable learning lifecycle

The embedded runtime has three reusable knowledge assets:

- `field_knowledge.csv`
- `structure_knowledge.csv`
- `corrections.csv`

The extracted runtime may update these assets as the data-preparation workflow completes. The repository bootstrap preserves the current knowledge snapshot at:

```text
work/data_prep/knowledge/
```

On a later run, that persistent snapshot is copied back into the embedded runtime before source understanding/planning. This means learning survives across different source packages on the same workspace instead of being lost when the extracted runtime is recreated.

Reusable knowledge is evidence for understanding a new source; it must not be treated as a rigid rule that overrides the current dataset. Current source evidence, validation and completeness controls remain authoritative.

This learning store is intentionally separate from OCL judgment configuration. It should describe reusable source/field/structure understanding, not engagement-specific scope, category, working-capital, debt-like or normality conclusions.

`work/` is gitignored, so locally accumulated learning does not automatically travel to another machine or another clone. Any future cross-user sharing should use a deliberate sanitized/curated knowledge-pack process rather than committing client-specific working state.

## Boundary

`fdd-data-preparation` owns raw-source structure, source hashes, logical-dataset understanding, deterministic reshaping, completeness and lineage.

It does **not** decide OCL scope, OCL category/hierarchy, WC/debt-like treatment, normality, findings or management questions. Those belong downstream to `ocl_agent` after standardized data has been published.

The normal user does not run this folder separately. Use the repository-root:

```bash
python run_all.py
```

`fdd-data-preparation/run_databook.py` exists only for direct upstream testing/debugging and routes through the same full runtime.
