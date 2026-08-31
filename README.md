# agent-delegation-fun

Local Python agents that act on your GitHub repo.

## Agents

- **pr_bot**: Reviews pull requests (triggered by `pull_request` opened)
- **ci_bot**: Diagnoses CI failures (triggered by `workflow_run` completed with failure)
- **docs_bot**: Updates architecture and README docs when PRs change the system structure (triggered by `pull_request` opened)

Each agent uses pydantic-ai + Claude to reason about context and act.

## Running the webhook server

```bash
python -m pr_bot.main serve
```

This starts a FastAPI webhook server on port 8765 that listens for GitHub webhook events.

## CLI

Each agent has a CLI for manual testing:

```bash
# Review a PR
python -m pr_bot.main review <pr-url>

# Diagnose a failed CI run
python -m ci_bot.main diagnose <run-url>

# Check a PR and open a docs update PR if needed
python -m docs_bot.main check <pr-url>
```

## Configuration

Set environment variables (see `.env.example`):

- `ANTHROPIC_API_KEY`, `ANTHROPIC_WORKSPACE_ID` — Claude API
- `GITHUB_TOKEN` — GitHub API token (needs `repo`, `actions:read`, `contents:write` scopes)
- `PR_BOT_MODEL` — optional model override (default: claude-haiku-4-5)

## Casino simulator

Unrelated demo app: `python -m casino.simulate`
