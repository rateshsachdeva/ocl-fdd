For normal interactive repository work, use `AGENTS.md` as the canonical operating instructions.

If the prompt explicitly says you are the `AI_HOST` completing exactly one workflow checkpoint, stay narrowly scoped to that checkpoint: read the coordination payload's referenced instruction/handoff/evidence and any evidence paths explicitly named by those files, write only the required artifacts, and exit. Do not browse the repository broadly, edit code, run the workflow, or execute Python/shell commands from inside that child checkpoint.

When an interactive coding-agent session is itself running the skill, continue automatically through `AI_HOST` checkpoints as described in `AGENTS.md` until `READY`, `HUMAN`, or `FAILED`.

Never add raw-client Excel layout parsing to `ocl_agent`. Raw-source understanding belongs to the full embedded `fdd-data-preparation` workflow; OCL starts from its published standardized package.
