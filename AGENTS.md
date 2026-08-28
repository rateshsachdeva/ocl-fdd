# OCL FDD Agent Instructions

Read and follow `SKILL.md`. `SKILL.md` is authoritative.

When the user says "run the skill", "run OCL", "build the databook", "process the source files" or equivalent:

1. Act as the external AI host for this repository.
2. Run `python run_all.py --ai-host external`.
3. Follow the workflow's returned coordination instructions and referenced artifacts.
4. Continue automatically through checkpoints where `next_actor=AI_HOST` and `must_continue=true`.
5. Stop only at `READY`, `FAILED` or a genuine `HUMAN` judgment checkpoint.
6. Do not modify production code merely to complete an engagement.

Do not repeat the detailed methodology from `SKILL.md`.
