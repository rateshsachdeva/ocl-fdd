# OCL FDD — Agent Operating Instructions

## Product goal

The user experience is one repository and one launcher:

```text
references/source/
  -> python run_all.py
  -> output/OCL_Databook_vN.xlsx + output/OCL_Report_vN.pptx
```

Raw Excel interpretation belongs to the full `fdd-data-preparation` workflow. `ocl_agent` starts only from its published standardized package. Never add client-specific raw-Excel parsing to `ocl_agent`.

## Normal end-to-end architecture

Keep the normal workflow simple:

```text
raw client files
    -> deterministic Python discovery/profile + reusable knowledge
    -> AI_HOST UNDERSTAND_AND_PLAN
    -> deterministic Python validation/reshape/lineage/publication
    -> deterministic OCL scope/mapping/controls/databook/analysis tables
    -> AI_HOST WRITE_FDD_PARTNER_ANALYSIS
    -> deterministic Excel/PPT rendering + final QA + versioned publication
```

For the canonical integrated standardized publication, Python carries the already-established dataset/field semantics into OCL deterministically. Do not ask AI to reinterpret the same standardized package a second time.

Therefore a normal successful new-source run should require only two substantive AI reasoning passes:

1. **UNDERSTAND_AND_PLAN** — understand the profiled source evidence and create the source-bound Dataset Map / Processing Plan.
2. **WRITE_FDD_PARTNER_ANALYSIS** — read Python-created analysis evidence and write Deal Issues, Key Findings and Management Q&A.

Additional AI or human checkpoints are exception paths only when genuine ambiguity, missing canonical semantics, judgment review, or a control break requires them.

## AI host continuation

### Normal PowerShell / terminal use

Run:

```text
python run_all.py
```

The root Python process delegates explicit `AI_HOST` checkpoints to the installed/authenticated GitHub Copilot CLI and then resumes deterministic processing. Python owns routine processing, calculations, reconciliations, controls and rendering.

If Copilot CLI is unavailable, unauthenticated, or fails to create the exact required artifact, stop safely. Never invent or bypass the missing artifact.

### Already-open Codex / Claude Code session

Run:

```text
python run_all.py --ai-host external
```

When the workflow returns:

```json
{"next_actor": "AI_HOST", "must_continue": true}
```

the current agent must:

1. read `relevant_instruction` and `handoff_path` plus referenced evidence;
2. create/update exactly the required artifact(s);
3. never invent source values or replace deterministic Python calculations with AI arithmetic;
4. rerun `python run_all.py --ai-host external`;
5. continue until `READY`, `FAILED`, or a genuine `HUMAN` checkpoint.

When the user says **“run the skill”** in Codex or Claude Code, run it end to end in external mode rather than stopping at internal AI checkpoints.

## Exception checkpoints

These are not part of the intended normal two-AI path:

- `CONFIRM_OCL_SEMANTIC_HANDOFF` — fallback only for a non-canonical standardized package where semantics cannot be carried forward safely.
- `INVESTIGATE_OCL_CONTROL_ALIGNMENT` — only when a real control needs source-backed investigation; never solve with a plug.
- `HUMAN` judgment review — only for unresolved scope, mapping/hierarchy, WC/debt-like, normality or other genuinely human-owned decisions.

Existing reviewed human config always wins.

## FDD-partner analysis boundary

Python calculates the numbers once from the reconciled OCL model and produces the evidence package. AI interprets that evidence qualitatively.

```text
formula-linked foundation
    -> Python metrics / materiality / reconciliations
    -> AI_HOST FDD-partner interpretation
    -> Deal Issues + Key Findings + Q&A
    -> deterministic workbook/PPT rendering
```

For `WRITE_FDD_PARTNER_ANALYSIS`, follow `src/ocl_agent/llm/FDD_PARTNER_ANALYSIS.md`.

AI must not recalculate, override or invent an amount, percentage, classification or materiality result. Think as an experienced FDD partner: focus on deal implications, normalized working capital, net debt/equity value, QoE, representativeness of closing balances, validity/completeness, settlement/release risk and the specific facts still needed from management. Avoid robotic variance commentary and filler questions.

Materiality remains deterministic:

- Databook review: absolute movement >= 100,000 **OR** percentage movement >= 10%.
- Headline trigger: absolute movement >= 100,000 **AND** percentage movement >= 30%.

Management questions must ask for factual evidence or operational explanations. Do not ask management to decide whether an item is debt-like, working capital, one-off or a purchase-price adjustment.

## Source and financial safety

- Raw source files are immutable.
- Source-package fingerprinting binds each run to the exact current files.
- No balancing plugs or invented amounts.
- Every relevant input record has visible disposition and lineage.
- Python owns deterministic reshaping, calculations and controls.
- Applicable hard controls must pass before final publication.
- Unsupported controls are explicit `NOT_APPLICABLE`; unresolved evidence is not silently guessed.
- Canonical semantics may be carried forward deterministically only from the standardized publication; arbitrary raw headings must never be reinterpreted by OCL Python.
- The final Excel databook is the principal deliverable; the PowerPoint is secondary and uses the same reconciled evidence.
