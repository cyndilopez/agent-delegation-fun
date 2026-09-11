# agent-delegation-fun

This repo is a playground for GitHub-triggered Python agents. Each agent uses [pydantic-ai](https://ai.pydantic.dev/) with Claude to read repo context (PR diffs, CI logs, or architecture docs) and take a structured action on GitHub — post a review, comment with a CI diagnosis, or open a follow-up docs PR. A unrelated blackjack simulator lives under `casino/` for local test data.

The agents share a thin `bot_shared/` layer (LLM client, GitHub auth) and run behind one FastAPI webhook server. For deeper structure, see `docs/architecture.md`.

## Running the agent layer

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add ANTHROPIC_API_KEY, GITHUB_TOKEN, etc.
```

**Webhook mode** (production-style):

```bash
python -m pr_bot.main serve --port 8765
```

Forward GitHub webhooks to `http://localhost:8765/webhook/github` (e.g. via [smee.io](https://smee.io)). Subscribe to **Pull requests** and **Workflow runs**. Webhook deliveries are logged at INFO when the server starts with `python -m pr_bot.main serve`.

**CLI mode** (manual runs):

```bash
python -m pr_bot.main review <pr-url>
python -m ci_bot.main diagnose <actions-run-url>
python -m docs_bot.main check <pr-url>
```

## Agents and triggers

| Agent | Trigger | What it does |
|---|---|---|
| `pr_bot` | `pull_request` opened | Fetches the PR diff, runs a structured code review, posts comments on GitHub |
| `ci_bot` | `workflow_run` completed (failure) | Fetches CI logs, diagnoses the failure, posts a comment on the linked PR |
| `docs_bot` | `pull_request` opened (non-`docs/*` branches only) | Compares the PR to current docs; if architecture or this README need updates, opens one follow-up docs PR |

## AI tools used

- **Claude** (`claude-haiku-4-5` by default) via pydantic-ai for all agent reasoning and structured output
- **Cursor** for implementation, debugging, and iterating on prompts locally
- **GitHub API** for PRs, reviews, Actions logs, and opening docs branches/PRs
- **smee.io** for local webhook forwarding during development

Org-linked Anthropic keys use `ANTHROPIC_WORKSPACE_ID` (sent as `anthropic-workspace-id`).

## Casino simulator

Separate demo app — see [`casino/README.md`](casino/README.md). Quick start: `python -m casino.simulate`
