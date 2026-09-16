# Exact-head Actions dependency admission

Owner: Codex; extends shared policy PR #26 under the full gap-filling plan.

The prior workflow enabled auto-merge solely from patch/minor metadata. The
new gate requires a verified Dependabot Actions update, workflow-only modified
paths, current same-repository default-branch PR identity, and strict server-side
required CI bound to the observed GitHub Actions App identity. It reads the latest
CI Minimal run, its exact head/base pair and its completed validation step, then
re-reads the PR before eligibility. Pending, failed, denied, malformed, partial,
stale, spoofed and zero-step evidence produces a visible HOLD. No waiting loop.

The guard makes at most eight GET requests in 90 seconds, with 15-second request
limits and 2 MB response limits. The workflow has a three-minute bound, checks
out only the base SHA with persisted credentials disabled, and retains upstream
Dependabot commit verification. Auto-merge still uses an exact-head match and no
administrative override. Major updates remain separate, requiring repository-
specific validation; Actions patch/minor updates share their own group.

Upstream references were resolved without upgrades: fetch-metadata v3 is
25dd0e34f4fe68f24cc83900b1fe3fe149efef98; checkout v7 is
3d3c42e5aac5ba805825da76410c181273ba90b1. Source:
https://github.com/dependabot/fetch-metadata/blob/main/README.md

## Boundaries and continuation

No account grant, branch protection, workflow dispatch or remote dependency merge
was performed. This remains a one-shot pull-request-event guard. A pending CI
result is not re-polled or automatically re-armed here; the governed integration
owner must handle later accepted evidence. Dependabot's pull-request token may
remain read-only, and absent classic strict protection or unavailable read
capability holds. The selected independently protected governor is the owner of
privileged execution; this repair does not replace that outstanding obligation.
Ruleset-only protection is currently unmeasured by this gate, never assumed safe.

Runner admission remains distinct from executed code. Shared-template consumer
propagation follows central acceptance in bounded PRs; no external repository was
automatically synchronized. Keep the original CLA signature and legal policy.

Verification: run `python3 -m unittest discover -s tests -p 'test_*.py' -v`, parse
all changed YAML, and check diff hygiene. The suite covers preserved profile
refresh behavior plus positive executed-CI eligibility and adversarial holds.

Observed local validation: all 19 tests passed; all three changed YAML files parsed; git diff --check passed. These receipts establish local code validation only.
