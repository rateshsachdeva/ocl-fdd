# Handoff to a New User

This repository is designed to run on another computer without carrying the original developer's `work/`, `output/` or client source folders.

## What the recipient needs

- Python 3.11 is recommended.
- Install dependencies with `pip install -r requirements.txt`.
- Copy the engagement's raw client files into `references/source/` separately. Client files are intentionally excluded from Git.
- Do not modify the raw source workbooks.

## GitHub Copilot Enterprise: two supported ways to run

### A. VS Code / GitHub Copilot coding agent

This is the simplest route when the recipient has GitHub Copilot Enterprise in VS Code.

Open the repository in VS Code and tell the coding agent:

> Run the OCL FDD skill end to end. Follow AGENTS.md. Continue through all AI_HOST checkpoints until READY, FAILED, or a genuine HUMAN review is required.

The repository instructions tell an interactive coding agent to use:

```bash
python run_all.py --ai-host external
```

The agent should complete the bounded AI reasoning artifacts itself and rerun Python between checkpoints.

### B. Plain terminal / PowerShell

Run:

```bash
python run_all.py
```

This route automatically uses GitHub Copilot CLI for AI reasoning checkpoints. Copilot Enterprise access by itself does **not** guarantee the CLI route is available: the recipient's organization/enterprise must allow Copilot CLI, the CLI must be installed, and the user must be authenticated.

Typical one-time checks are:

```bash
copilot --version
copilot login --web-flow
```

If enterprise policy blocks the CLI, use the VS Code coding-agent route above instead.

## Expected workflow

```text
raw client files
  -> Python discovery/profile/evidence
  -> AI: UNDERSTAND_AND_PLAN
  -> Python standardized data + lineage
  -> OCL reviewed judgments + controls
  -> Python databook + analytical evidence
  -> AI: WRITE_FDD_PARTNER_ANALYSIS
  -> Python final Excel/PPT + QA + versioning
```

Normal contextual AI usage is therefore two reasoning stages. Python owns financial amounts, calculations, controls, reconciliations and rendering.

## A HUMAN checkpoint is not a failure

On a new engagement, unseen source labels may require review of:

- OCL / trade payable / financing / outside-scope disposition;
- category and hierarchy;
- working-capital / debt-like / neither treatment;
- normal / one-off treatment.

If the workflow stops at `HUMAN / REVIEW_OCL_JUDGMENTS`, review the generated review workbook/context, record the decisions in the package runtime config as instructed, and rerun. The skill intentionally does not let AI mark unsupported accounting/FDD judgments as reviewed simply to reach an output.

## Evidence-aware additional analysis

The completed workbook contains `Analysis Coverage`, which tells the recipient what the supplied data supports.

The skill can perform, when evidence permits:

- annual/category movement and concentration;
- monthly volatility and seasonality;
- year-end build / unwind versus recent run-rate;
- 12-month balance persistence / recurrence proxy;
- 12-month average/median normalization reference (reference only, not an automatic adjustment);
- stale-balance proxy from monthly history;
- new-balance and cliff-to-zero diagnostics;
- debt-like, management-vs-FDD debt-like gap and one-off analysis from reviewed judgments;
- utilisation/release and explicit reversal analysis when validated movement data is supplied;
- OCL-to-expense ratios only when an explicitly identified expense/P&L context dataset is supplied;
- revenue/payroll context ratios when those supporting datasets are supplied.

The skill must **not** pretend to have tested matters for which the necessary evidence is missing. In particular, true accrual adequacy, missing-accrual completeness, double counting and true obligation aging require richer supporting evidence such as subsequent payments, invoice/vendor detail, contracts, payroll/bonus schedules or other obligation-level support. When that evidence is absent, `Analysis Coverage` marks the analysis as unsupported/partial rather than manufacturing a conclusion.

## Final output

A completed run publishes matching versioned deliverables, for example:

```text
output/OCL_Databook_v1.xlsx
output/OCL_Report_v1.pptx
```

Later completed runs create `v2`, `v3`, etc. Existing versioned outputs are not overwritten.

Before relying on a deliverable, confirm the terminal/agent reports `READY` and final QA `PASS`.
