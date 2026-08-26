For normal interactive repository work, use `AGENTS.md` as the canonical operating instructions.

If the prompt explicitly says you are the `AI_HOST` completing exactly one workflow checkpoint, stay narrowly scoped to that checkpoint: read the coordination payload's referenced instruction/handoff/evidence and any evidence paths explicitly named by those files, write only the required artifacts, and exit. Do not browse the repository broadly, edit code, run the workflow, or execute Python/shell commands from inside that child checkpoint.

For `UNDERSTAND_AND_PLAN`, if coordination contains `reusable_knowledge_context`, read that compact context **first**, then the current deterministic profile/samples/handoff. Use matched knowledge to recognize already-evidenced source patterns quickly and spend reasoning effort only on material unresolved ambiguity. Current source evidence always wins. Do not use historical synthetic `Expected_Results`, golden-truth, generation-validation or training-prompt files as production evidence or an answer key. Do not inspect every month/file independently when deterministic evidence establishes a common structure.

When an interactive coding-agent session is itself running the skill, start/resume with `python run_all.py --ai-host external` and continue automatically through every coordination checkpoint where `next_actor=AI_HOST` and `must_continue=true`, as described in `AGENTS.md`, until `READY`, `HUMAN`, or `FAILED`.

For one-source learning, use `python run_all.py --learn-source <file> --ai-host external` and thereafter rerun the exact `resume_command` printed in coordination until the learning source completes. One-source learning is data-preparation/knowledge-only; the final combined engagement must still use normal `python run_all.py --ai-host external` with all relevant sources present.

Never add raw-client Excel layout parsing to `ocl_agent`. Raw-source understanding belongs to the full embedded `fdd-data-preparation` workflow; OCL starts from its published standardized package.
