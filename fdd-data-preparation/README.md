# Embedded fdd-data-preparation

This is the upstream data-preparation layer used by the OCL skill. Its job is to convert heterogeneous raw Excel sources into reliable standardized long/flat dataset(s) for downstream FDD analysis.

```text
raw Excel
   ↓
Deterministic Python profile + staging
   ↓
AI host dataset understanding
   ↓
AI host Dataset Map + Processing Plan
   ↓
Deterministic Python validation + execution
   ↓
Completeness + lineage
   ↓
work/data_prep/output/latest/
```

The AI host may be Codex, Claude Code, GitHub Copilot or another capable coding/agent host. The Python runtime itself does not call a model API.

## Boundary

`fdd-data-preparation` owns raw-source structure, source hashes, logical-dataset understanding, deterministic reshaping, completeness and lineage.

It does **not** decide OCL scope, OCL category/hierarchy, WC/debt-like treatment, normality, findings or management questions. Those belong downstream to `ocl_agent` after standardized data has been published.

The normal user does not run this folder separately. Use the repository-root:

```bash
python run_all.py
```

`fdd-data-preparation/run_databook.py` exists only for direct upstream testing/debugging and routes through the same full runtime.
