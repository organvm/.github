# Trusted completion assessor

Owner: shared workflow PR 26; Limen intake PR 2651.

Implement a read-only CLI for an exact completion run/attempt/head. Resolve one PR through authenticated API reads, bind repository ID 1154799938, verify all bounded commits are signed Dependabot commits, and parse each signed metadata block without aliases or duplicate keys. Require Actions patch/minor metadata throughout; major, missing and malformed metadata remain HOLD. Existing exact-generation CI and protection checks remain mandatory. Output REVIEW_READY is never automatic acceptance or merge authority.

Metadata verification was independently inspected against dependabot/fetch-metadata commit 25dd0e34f4fe68f24cc83900b1fe3fe149efef98, src/dependabot/verified_commits.ts and update_metadata.ts. The assessor strengthens first-commit-only validation by verifying every bounded commit and update type. No PR-event context is fabricated. PyYAML is required for this completion command; its absence produces HOLD and does not alter the existing standard-library admission path.

Next integration: deploy the reviewed source/digest in the isolated assessor, generate source-bound broker packets, and connect the existing disabled intake consumer. No completion workflow trigger, credential installation, protection mutation or merge is performed here. These source tests do not discharge the live integration findings.
