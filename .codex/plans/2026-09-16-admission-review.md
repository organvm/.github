# Admission review dispositions

Owner: Codex; shared policy PR #26.

Review 4022311973 is valid: GitHub documents workflow-run paths with an optional @ref suffix. Match the exact CI filename with an optional nonempty, whitespace-free suffix; retain independent event, repository identity, head/base and executed-step checks. Reject other filenames, prefixed paths, empty suffixes and non-string values. Source: https://docs.github.com/en/rest/actions/workflow-runs?apiVersion=2026-03-10

Reviews 4022306622 and 4022306625 are valid unresolved integration obligations: branch-protection inspection requires Administration read, while the ordinary workflow token cannot supply it; CI completion also does not re-trigger this one-shot PR event. The existing diagnostic guard therefore cannot establish operational automatic delivery by itself. Do not claim these findings fixed by the path correction or by tests. Source: https://docs.github.com/en/rest/branches/branch-protection#get-branch-protection

Remaining owner is governed integration under Limen L-DEPENDABOT-DELIVERY-ARM. The selected relay governor contract (Limen docs/architecture/personal-relay-merge.md; relay issue #3) isolates privileged credentials from candidate workflows and currently applies to the relay repository. Extending that contract to shared-policy consumers requires a reviewed scope/credential deployment and completion-event route, with exact-head protected canaries; it is not already supplied by this shared PR. No workflow_run privileged trigger, credential grant, protection weakening or polling loop is introduced here. The shared PR remains partial until that execution path exists.

Verification: 21 tests passed with python3 -m unittest discover -s tests -p 'test_*.py' -v, including both accepted path forms and rejected malformed/spoofed paths. Diff hygiene passed. No remote workflow execution or dependency merge is claimed.
