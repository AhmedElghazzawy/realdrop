# RealDrop documentation

Organised by audience. Start with the vision, then the architecture overview.

## Product: what and why

| Document | Contents |
|---|---|
| [Vision](product/vision.md) | Problem, personas, value propositions, launch scope, non-goals, success measures |
| [Use cases](product/use-cases.md) | Actors and use cases UC-01 to UC-12 with acceptance criteria |
| [Roadmap](product/roadmap.md) | Phases to launch (27 Nov 2026), latest-finish dates, cut lines |

## Architecture: how it is built

| Document | Contents |
|---|---|
| [Overview](architecture/overview.md) | C4 context and container diagrams, layers and the dependency rule, key flows, quality attributes |
| [Data model](architecture/data-model.md) | Conventions, ERD, tables, glitch filter, real-drop rule |
| [AI design](architecture/ai-design.md) | Catalog tagger, look analyzer, matching, stylist loop, grounding guard, profile ranking |
| [Decisions (ADRs)](architecture/decisions/README.md) | Every significant decision, its context and consequences |

## Engineering: how to work on it

| Document | Contents |
|---|---|
| [Local development](engineering/setup.md) | Prerequisites, first run, everyday commands, troubleshooting |
| [Testing and evals](engineering/testing-and-evals.md) | Testing strategy per layer, AI eval suites and thresholds |
| [Design system](engineering/design-system.md) | UI direction, tokens, components |
| [Contributing](../CONTRIBUTING.md) | Branches, commits, PRs, definition of done |

## Operations: how it runs

| Document | Contents |
|---|---|
| [Deployment](operations/deployment.md) | Neon, GitHub Actions, Render, Vercel setup and limits |
| [Runbook](operations/runbook.md) | Daily checks and what to do when something fails |
| [Data sources](data-sources/README.md) | Per-brand feasibility, robots.txt and terms decisions |

## Keeping docs true

Docs change in the same PR as the behaviour they describe. A changed decision gets a new ADR. The
data model must match the Alembic migrations; the architecture's dependency rule is enforced by
`apps/api/tests/test_architecture.py`.
