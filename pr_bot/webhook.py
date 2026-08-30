"""GitHub webhook handler for pull_request opened events."""

from __future__ import annotations

from fastapi import FastAPI, Request

from pr_bot.agent import run_review
from pr_bot.github import fetch_pr_context, post_review

app = FastAPI()


@app.post("/webhook/github")
async def github_webhook(request: Request) -> dict[str, str]:
    payload = await request.json()

    if "pull_request" not in payload:
        return {"status": "ignored", "reason": "unhandled-event"}

    action = payload.get("action")
    if action != "opened":
        return {"status": "ignored", "reason": "unhandled-action"}

    repo = payload.get("repository") or {}
    owner = (repo.get("owner") or {}).get("login")
    repo_name = repo.get("name")
    pr = payload["pull_request"]
    number = pr.get("number")

    if not owner or not repo_name or not number:
        return {"status": "ignored", "reason": "missing-repository"}

    ctx = await fetch_pr_context(owner, repo_name, number)
    review = await run_review(ctx)
    await post_review(owner, repo_name, number, review)
    return {"status": "ok"}
