# README Standards

Organization-wide adoption policy for README and reader-mode documentation
across all ORGANVM repositories.

## Scope

This file defines fleet adoption requirements for:

- README structure and depth by tier
- applying reader-mode repository classes and required audience routes;
- requiring the canonical project-record and evidence contracts;
- Organ-specific required sections
- Minimum quality rubric used for audits
- Minimum community-health and root-hygiene requirements tied to README quality

Derived from the system corpus standards:

- `organvm-corpvs-testamentvm/docs/standards/10-repository-standards.md`
- `organvm-corpvs-testamentvm/docs/planning/01-readme-audit-framework.md`
- `organvm-corpvs-testamentvm/docs/planning/03-per-organ-readme-templates.md`

## Universal README Model

Every README should follow progressive disclosure. The reader should receive
orientation before being asked to interpret mechanism or proof:

1. **Recognition:** what this is, in ordinary language
2. **Relevance:** problem, user, present state, and one concrete example
3. **Route:** audience-specific inspection paths appropriate to the repository
4. **Mechanism:** architecture, method, operation, or formal construction
5. **Evidence:** status, authorship, tests, provenance, and limitations
6. **Depth:** the canonical long-form intellectual and technical treatment

The README remains the hub and principal exhibition. It does not need to contain
every edition in one linear sequence.

## Reader-mode contract

One factual project may have several audience-specific editions. They may change
order, terminology, examples, assumed knowledge, and evidence emphasis. They may
not change project status, authorship, capabilities, limitations, deployment,
adoption, outcomes, or evidence state.

Definitions do not originate here. The canonical editorial specification and
templates live in
[`organvm/editorial-standards`](https://github.com/organvm/editorial-standards).
Machine-readable project and evidence contracts live in
[`organvm-iv-taxis/schema-definitions`](https://github.com/organvm-iv-taxis/schema-definitions):

- [reader-mode standard](https://github.com/organvm/editorial-standards/blob/main/docs/reader-mode-documentation.md)
- [project-record schema](https://github.com/organvm-iv-taxis/schema-definitions/blob/main/schemas/project-record-v1.schema.json)
- [assertion-evidence schema](https://github.com/organvm-iv-taxis/schema-definitions/blob/main/schemas/assertion-evidence.v1.schema.json)
- [README v2 template](https://github.com/organvm/editorial-standards/blob/main/templates/repository-readme-v2.md)
- [audit rubric](https://github.com/organvm/editorial-standards/blob/main/schemas/reader-mode-rubric.yaml)

### Repository classes

Documentation class describes repository function, not quality or prestige.
Promotion tier and documentation class are separate fields.

| Class | Repository function | Contract |
|---|---|---|
| A | Flagship system spanning several audiences | README v2, five audience editions, evidence record, project record |
| B | Major project with two or three material audiences | README v2, 2–3 audience editions, evidence record, project record |
| C | Supporting component, library, schema, or infrastructure | Technical route, interfaces/status/evidence, project record |
| D | Deployment artifact, player, mirror, or delivery shell | Minimal use/deployment README, project record, and canonical-project redirect |
| E | Research, theory, scholarship, or artistic corpus | Humanities/scholarly route, mechanism, sources/provenance, project record |
| F | Archive, superseded surface, contribution record, or reference | Project record, immutable status, provenance, successor/redirect when one exists; no SEO expansion |

Do not inflate deployments and mirrors into independent projects. Do not require
commercial framing from art/theory repos or multi-audience bloat from supporting
components.

### Class A/B first screen

Before the inherited long-form README, establish:

1. title and one ordinary-language sentence;
2. verified artifact, demo, documentation, and evidence links;
3. a short “What am I looking at?” explanation;
4. a “Choose your reading path” table;
5. a current-state table with users, contribution, evidence, and limitations.

Long READMEs are allowed. Difficult language is allowed. The contract controls
the order in which complexity becomes visible; it does not flatten the work.

## Canonical project record

All classes maintain `project-record.yml`; classes D and F use the smallest
class-valid record. It is the factual substrate for repeated status,
contribution, evidence, industry, and link blocks. Generated blocks may be
surrounded by hand-written audience analysis, but may not be edited
independently.

Every material claim resolves to `assertion-evidence.v1`, whose canonical
`verification_state` is `unverified`, `verified`, `stale`, or `disputed`.
Project records separately carry a reader-facing claim posture such as
`implemented`, `partial`, `proposed`, `unknown`, or `contradicted`; posture never
substitutes for verification state. A proposed industry application is not a
deployment. A source path is not evidence of adoption, scale, performance, or
business outcome.

Canonical ownership must be resolved before generation. A personal mirror and an
organization repository may not both present themselves as the same canonical
project.

## Organ-Specific Required Sections

### ORGAN-I (Theory)
- Problem Statement
- Core Concepts
- Related Work
- Installation or Usage
- Examples
- Downstream Implementation
- Validation
- Roadmap
- Cross-References

### ORGAN-II (Art)
- Artistic Purpose
- Conceptual Approach
- Technical Overview
- Installation
- Working Examples or Demos
- Theory Implemented
- Portfolio or Exhibition Context
- Contributing

### ORGAN-III (Commerce)
- Product Overview
- Value Proposition
- Business Model
- Technical Architecture
- Getting Started
- Case Study
- Metrics and Proof
- Support and Governance

### ORGAN-IV (Orchestration)
- Orchestration Purpose
- Registry Overview
- Governance Rules
- How It Works
- Key Concepts (promotion/dependency/validation)
- Concrete Example Flow
- Contributing to Governance

### ORGAN-V (Public Process)
- Publication Purpose
- Publishing Guidelines
- Structure/Frontmatter Requirements
- Index or Corpus Navigation
- Subscription/Distribution
- Contributing
- Archive

### ORGAN-VI (Community)
- Community Purpose
- Participation Model
- Community Guidelines
- Archive Structure
- Access Model
- Contributing

### ORGAN-VII (Marketing)
- Distribution Strategy
- Audience Target
- Content Types
- Metrics
- Channels
- Publishing Calendar
- Templates or Playbooks

## README quality and reader-mode rubric

### Existence and Accessibility (0-20)
- README exists in root
- clear title + one-line description
- table of contents/navigation
- readable formatting

### Content Completeness (0-40)
- explicit problem statement
- complete setup/install instructions
- two or more working examples (where applicable)
- dependencies documented
- contributing guidance present

### Accuracy and Currency (0-20)
- links valid
- examples run
- docs match implementation
- freshness timestamp or clear status

### Portfolio Relevance (0-20)
- why repo exists is explicit
- connection to larger system is explicit
- features/value proposition clear
- evidence or impact signals present

The historical 0–100 README rubric remains a coarse completeness check. Reader-
mode conversion uses a separate 0–4 diagnostic across:

1. orientation;
2. technical depth;
3. conceptual depth;
4. commercial/operational relevance;
5. evidence and claim boundaries;
6. legitimate search-intent surface;
7. cross-linking.

Scores describe the documentation interface, not project worth. Rank conversion
by value, documentation gap, and reuse leverage—not by lowest score alone.

## Root Hygiene and Community Files

At minimum, each active repo should include:

- `README.md`
- `LICENSE`
- `.gitignore`
- `.github/CONTRIBUTING.md` (or org-level fallback)
- `.github/SECURITY.md` (or org-level fallback)
- `.github/CODE_OF_CONDUCT.md` (or org-level fallback)

Flagship and Standard repos should also include:

- pull request template
- issue templates for bug and feature/documentation requests

All reader-mode classes should also include:

- `project-record.yml`
- a claim-level evidence path

Classes A–C and E additionally include the required `docs/audiences/*.md`
routes for their declared class. Classes D and F keep their minimal usage,
redirect, archive, provenance, and status material in the root README; they do
not create a nominal audience edition merely to satisfy structure.

## Local Overlay Policy

Each organ may keep an overlay standards file in its `.github` repository:

- path: `README_STANDARDS.md`
- purpose: local additions and stricter checks
- requirement: must link back to this canonical policy
- rule: overlay cannot weaken canonical requirements

## Enforcement

The executable reference implementation lives in
[`organvm/organvm-engine`](https://github.com/organvm/organvm-engine):

```bash
organvm docs validate project-record.yml --schema path/to/project-record-v1.schema.json
organvm docs audit . --format markdown
organvm docs audit --workspace "$ORGANVM_WORKSPACE_DIR" --format json
```

Each organ superproject may retain `tools/audit_platform_standards.sh`, but it
should delegate reader-mode checks to the reference implementation rather than
reimplementing status or scoring vocabularies.

Each audit should check, at minimum:

1. required standards files exist;
2. README supplies the orientation appropriate to its class;
3. `project-record.yml` validates and its audience paths exist;
4. claim IDs, status vocabularies, and evidence references are internally sound;
5. local overlay links to this canonical policy.

Factual integrity errors fail CI. Editorial opportunities—thin orientation,
orphan docs, low rubric dimensions, duplicated prose, or missing semantic
cross-links—warn and enter the conversion queue. A rubric score alone never
blocks publication.

Any exception must be tracked via issue with owner + due date.
