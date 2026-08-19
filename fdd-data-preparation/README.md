# Embedded fdd-data-preparation

This is the upstream data-preparation layer used by the OCL skill. Its job is to convert heterogeneous raw Excel sources into a reliable long/flat publication for downstream FDD analysis.

```text
raw Excel
   ↓
Python profile + staging
   ↓
AI dataset understanding
   ↓
AI processing plan
   ↓
Python validation + deterministic execution
   ↓
Python completeness + lineage
   ↓
output/latest standardized database(s)
```

The AI host can be Codex, Claude Code, Copilot or another capable agent. The Python runtime itself does not call a model API.

## Responsibilities

Python owns read-only discovery, SHA-256 source binding, structural profiling, targeted inspection, plan validation, deterministic reshaping, reconciliation, completeness, lineage and publication.

The AI host owns contextual interpretation of the current source evidence: what logical datasets exist, their grain/field meaning, how source partitions relate, and the deterministic processing plan needed to produce the standardized database.

This layer does **not** decide OCL scope, OCL categories, WC/debt-like treatment, normality or deal treatment. Those remain downstream in `ocl_agent`.

The normal user does not run this folder separately. The root `python run_all.py` orchestrates the workflow and passes the published `work/data_prep/output/latest/` package to OCL.
