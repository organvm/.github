# Shared Actions dependency delivery: integration contract

Owner: Codex; organvm/.github PR #26; Limen L-DEPENDABOT-DELIVERY-ARM.

## Current evidence

Limen scripts/_dependency_upkeep.py routes only its declared pilot repositories. institutio/github/dependency-trust.json has installed=false and repositories={}. It supplies review routing, not merge authority. The dedicated relay transaction in docs/architecture/personal-relay-merge.md is restricted to organvm-ci-relay and cannot be assumed to protect this repository. No available credential or deployment was widened.

The shared candidate is therefore preparation, not operational auto-merge. Keep reviews 4022306622 and 4022306625 unresolved until the following path executes successfully.

## Required implementation

1. Extend the existing governor owner with an explicit repository-ID-scoped Actions policy. Register organvm/.github ID 1154799938, its exact default branch, reviewed admission code digest and required validator identity. Do not infer policy from candidate-controlled labels, workflow names or repository strings. Repository additions remain explicit; this does not add a relay target.
2. Route completed CI events to that governor through its authenticated intake. Treat event content only as a hint: independently GET the run and associated PR, enforce current repository ID/default, Dependabot identity, exact head/base and latest run attempt, and apply finite existing broker capacity/lease controls. A completion event starts a new bounded assessment; no session waits or polling loop.
3. Preserve metadata verification. fetch-metadata v3 has no PR-number input and expects PR event context; do not simply move it into workflow_run and assume equivalent verification. Reuse its verified output only through an authenticated source-bound receipt, or implement and independently verify the equivalent commit/actor/metadata checks in the trusted consumer. No event-file fabrication is an acceptance receipt.
4. Keep candidate execution isolated from authority. The trusted governor reads protection with its approved Administration-read capability. Candidate CI never receives that credential. Retain strict server-side policy and exact-head merge fencing; the shared gate's final GET alone does not fence base movement. A relay-only policy or broad ordinary token is not a substitute.
5. Persist the event/run/attempt/head/base tuple and terminal outcome in the existing governor receipt store. Duplicate events observe the existing disposition; ambiguous writes require readback and remain unmeasured without positive landing proof. Successful unrelated child receipts remain reusable.
6. Only after protected canaries succeed, replace the current ineffective direct workflow merge step with the approved route and restore PR readiness. Do not mark the two findings addressed from a design or fixture alone.

## Acceptance batch

- CI completes after its PR event: exactly one bounded assessment is delivered without waiting.
- Duplicate/reordered events, changed run attempt, older successful run, changed head/base, fork identity and spoofed metadata cannot authorize a merge.
- Candidate code cannot read the governor credential; denied protection reads remain HOLD.
- Missing policy, uninstalled trust registry, stale evidence and unknown required checks stay visible.
- Normal GitHub Actions/direct-user writes are rejected under the chosen server policy; one legitimate governor-controlled Actions patch merge has an exact landing receipt.
- Major dependency updates still require repository-specific review and validation.

External gate: approved isolated credential/deployment and repository protection. Engineering owner remains this PR and the dependency-delivery lever; do not treat account activation as the whole missing implementation. Next engineering action: implement the authenticated completion intake and its bounded replay/readback tests in the existing governor, with the repository scope declared for review. No workflow trigger or account state changed in this planning increment.
