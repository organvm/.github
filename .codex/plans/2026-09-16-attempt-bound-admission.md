# Bind dependency admission to one CI attempt

Read jobs through the exact run-attempt endpoint, reject unknown attempts, and read back the run after jobs. Changed attempts or source/completion bindings remain HOLD. Preserve the nine-read, 90-second budget and include the attempt in eligible observations.

GitHub contract: https://docs.github.com/en/rest/actions/workflow-jobs#list-jobs-for-a-workflow-run-attempt

This is read-only admission evidence. It does not implement the trusted completion intake, supply isolated protection authority, or fence a subsequent merge transaction. The existing completion-governor contract and open review findings retain those requirements.
