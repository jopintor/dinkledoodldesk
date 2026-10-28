# Contributing to DinkDesk

The Week 15 QA report has to show our git history of fixes, so small, well-named commits and PRs matter.

## Workflow

1. Pick an issue on the GitHub Projects board and assign yourself. Move it to **In progress**.
2. Update `main` and branch from it:
   ```bash
   git switch main
   git pull
   git switch -c feat/12-chat-widget
   ```
3. Commit as you go (see the message convention below). Push your branch and open a pull request into `main`
   early, as a draft if it is not ready.
4. Before marking it ready, run the checks CI runs:
   - backend: `ruff check . && ruff format --check . && pytest`
   - frontend: `npm run lint && npm run build`
5. Ask one teammate to review. Fix comments with new commits (don't force-push over a review).
6. Merge with **Squash and merge** once CI is green and it is approved. Delete the branch.
   Write `Closes #12` in the PR description so the issue closes itself.

Never push directly to `main`, and never commit `.env`, API keys, or the course PDFs.

## Branch names

`<type>/<issue-number>-<short-description>`, lowercase with hyphens:

| Type | For |
|---|---|
| `feat/` | New feature (`feat/7-rag-ingest`) |
| `fix/` | Bug fix (`fix/31-cors-tunnel`) |
| `docs/` | Documentation only |
| `test/` | Tests, eval, load tests |
| `chore/` | Tooling, CI, Docker, dependencies |
| `refactor/` | Code change with no behaviour change |

## Commit messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <summary in imperative mood, max ~72 chars>

<optional body: what and why, not how>

Refs #12
```

- **type**: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`, `perf`, `ci`
- **scope** (optional): `backend`, `frontend`, `rag`, `tools`, `guardrails`, `n8n`, `infra`, `kb`, `eval`, `docs`

Examples:

```
feat(rag): ingest knowledge-base markdown into Chroma
fix(frontend): show error when the API tunnel is down
test(guardrails): add prompt-injection cases to golden set
```

The squash-merge commit uses the PR title, so give PRs a Conventional Commit title too.

## Code style

- Python: `ruff` (lint + format), type hints, docstrings on public functions.
- TypeScript: `eslint` (Next.js config); API calls only through `frontend/src/lib/api.ts`.
- LLM access only through `backend/app/llm/`.
