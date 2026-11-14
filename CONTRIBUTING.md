# Contributing

How changes get from an idea to `main`. Setup first: [`docs/engineering/setup.md`](docs/engineering/setup.md).

## Workflow

1. **Start from a use case or roadmap item.** Larger changes get a short plan (goal, files, steps,
   risks, tests) before code; a change to an architecture decision gets an ADR
   ([template](docs/architecture/decisions/template.md)).
2. **Branch** from `main`: `feat/shop-the-look`, `fix/rollup-race`, `docs/use-cases`.
3. **Write the test first** for bug fixes; new behaviour comes with tests, new AI behaviour with eval
   cases.
4. **Run `make check`** before pushing. CI runs the same checks on every push and PR.
5. **Open a PR** using the template. Small PRs (under ~400 changed lines) get reviewed faster.
6. **Merge** when CI is green. `main` is always deployable; never push on top of a red `main`.

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org): `type(scope): summary` in the
imperative, under 72 characters, then a body that explains **why**.

| Type | For |
|---|---|
| `feat` | New user-visible behaviour |
| `fix` | A bug fix |
| `refactor` | Code change with no behaviour change |
| `perf` | Performance improvement |
| `test` | Tests only |
| `docs` | Documentation only |
| `ci` / `chore` | Build, CI, tooling, dependencies |

Scopes in use: `collector`, `pipeline`, `pricing`, `catalog`, `advisor`, `ai`, `web`, `api`, `db`.

## Code standards

- **Python:** type hints everywhere (`mypy`), `ruff` for lint and format, Pydantic at every boundary,
  async SQLAlchemy. Respect the dependency rule in the
  [architecture overview](docs/architecture/overview.md#3-components-and-layers-api-package-realdrop).
- **TypeScript:** strict mode, server components by default, UI strings only in `src/i18n/{en,tr}.ts`,
  design tokens only (no raw hex in components).
- **Domain rules that are never broken:** money in integer minor units; discounts only from
  `pricing/`; Turkish-safe lowercasing (`tr_lower`); UTC timestamps with Istanbul calendar days;
  polite collection (robots.txt, identified User-Agent, rate limits, stop on 403).
- **Database:** schema changes only through Alembic migrations, reviewed by hand, reflected in
  [`docs/architecture/data-model.md`](docs/architecture/data-model.md).
- **Secrets:** only `.env.example` is committed. Never log secrets, personal data or full prompts.

## Definition of done

- [ ] `make check` passes locally and CI is green
- [ ] Tests cover the new behaviour; AI changes have eval cases meeting their threshold
- [ ] Docs updated (and an ADR if a decision changed)
- [ ] No secrets or personal data in the diff
- [ ] The commit or PR explains why
