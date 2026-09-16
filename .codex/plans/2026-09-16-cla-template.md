# CLA template event boundary

Owner: Codex; requested estate workflow repair.

Restrict the CLA job to pull_request_target or comments attached to pull requests.
Pin the existing v2.6.1 action to its verified commit. Keep the signature document,
allowlist, permissions, event subscriptions and signing phrases unchanged.

Validation: YAML parsed successfully and comparison against the original proves
only the job condition and action reference changed. The v2.6.1 tag currently
resolves to ca4a40a7d1004f18d9960b404b97e5f30a505a08 in the upstream repository.
No action version upgrade or CLA policy change is included. This fixes the shared
template; propagation to consumers and runner admission remain separate work.
