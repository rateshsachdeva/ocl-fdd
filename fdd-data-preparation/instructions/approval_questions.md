# Approval Questions

Create `approval_questions.json` after the Dataset Map and Processing Plan exist. Ask only `BLOCKING_USER_DECISION` questions whose answers materially change output grain, financial interpretation, sign convention, inclusion/exclusion, period handling, join behavior or another material processing outcome.

Unknown metadata alone is not a reason to ask. Put non-blocking assumptions and information items in their own arrays. For each blocking question provide stable ID, concise question/reason/why-it-matters, interaction type, meaningful options where applicable, optional evidence-backed recommendation, decision effect, affected plan elements, status `OPEN`, and a null user answer. Never silently rewrite the plan from a user answer.
