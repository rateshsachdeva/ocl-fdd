For normal interactive repository work, use `AGENTS.md` as the canonical operating instructions.

If the prompt explicitly says you are the `AI_HOST` completing exactly one workflow checkpoint, stay narrowly scoped to that checkpoint: read the coordination payload's referenced instruction/handoff/evidence and any evidence paths explicitly named by those files, write only the required artifacts, and exit. Do not browse the repository broadly, edit code, run the workflow, or execute Python/shell commands from inside that child checkpoint.

For `UNDERSTAND_AND_PLAN`, if coordination contains `builtin_knowledge`, read that file together with the deterministic profile/samples and reusable knowledge evidence. When `fast_start_mode=true`, treat the knowledge as low-priority hypotheses and use it to recognize already-evidenced source patterns quickly. Prefer completing the Dataset Map + Processing Plan from prepared evidence; use targeted inspection only for a material unresolved ambiguity. Current source evidence always wins, and benchmark golden answers or prior-client conclusions must never be assumed.

When an interactive coding-agent session is itself running the skill, start/resume with `python run_all.py --ai-host external` and continue automatically through every coordination checkpoint where `next_actor=AI_HOST` and `must_continue=true`, as described in `AGENTS.md`, until `READY`, `HUMAN`, or `FAILED`.

Never add raw-client Excel layout parsing to `ocl_agent`. Raw-source understanding belongs to the full embedded `fdd-data-preparation` workflow; OCL starts from its published standardized package.
