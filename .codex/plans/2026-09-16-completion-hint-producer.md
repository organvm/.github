# Completion hint producer and staged deployment template

Owner: Codex; organvm/.github PR #26; L-DEPENDABOT-DELIVERY-ARM.

Limen PR #2651 merged as 3c1313aab9e03706d776bf8cbcc390883acddc68 with the
repository-ID-scoped hint intake and source-bound assessment handoff. This
increment supplies the shared-workflow producer for that interface.

`scripts/dependency-completion-hint.py` reads a bounded workflow_run event and
copies only repository_id, run_id, run_attempt and head_sha. It filters the
registered repository/default, internal head repository, successful completed PR
run and CI Minimal workflow path. Those filters are routing; the trusted assessor
still independently verifies current GitHub state, signed metadata and policy.
Neither the event nor a recorded hint authorizes execution or merge.

The default invocation emits a hint. Explicit `--publish` performs one authenticated
POST in an isolated child with a 20-second wall limit, 15-second socket timeout,
no redirect/proxy inheritance and bounded readback. Only the dedicated
LIMEN_DEPENDENCY_COMPLETION_OBSERVER_TOKEN reference is accepted; ordinary GitHub
or conductor tokens are not fallback credentials. Ambiguous delivery remains HOLD
without retry. A recorded response must match the exact four-field identity and
retain automatic_acceptance=false.

`docs/deployment/dependency-completion.yml` is a reviewable template outside the
active workflow directory. It has contents-read permission, a pinned checkout,
explicit enablement, a trusted default-branch checkout and the dedicated observer
credential reference. It executes no candidate checkout or artifact. The source
basis is GitHub's [workflow_run event contract](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run),
which binds GITHUB_SHA to the default branch, and Octokit's
[workflow-run schema](https://github.com/octokit/webhooks/blob/main/payload-schemas/api.github.com/common/workflow-run.schema.json),
which declares the path and run_attempt fields. The template is not installed.

Credential ownership remains the Limen credential wall (#320), unprovisioned for
this producer. Existing #269/#1995 admission, isolated deployment grants, trusted
assessor-source approval, native wake integration and protected governor canaries
remain required. No credential, repository variable, webhook, active workflow,
service registration or live hint was created. Reviews 4022306622 and 4022306625
remain unresolved until the operational acceptance path succeeds.
