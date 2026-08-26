# Dataset-understanding fast start

For `UNDERSTAND_AND_PLAN`, the OCL bridge references `BUILTIN_FDD_SOURCE_KNOWLEDGE.md` and sets `fast_start_mode=true` in coordination.

The AI host should therefore:

1. read deterministic profile/samples;
2. read reusable promoted knowledge;
3. read the built-in FDD pattern library;
4. complete the Dataset Map + Processing Plan from that evidence wherever possible;
5. use targeted inspection only for a material unresolved ambiguity.

The built-in library accelerates recognition. It never supplies benchmark answers or overrides current-source evidence.
