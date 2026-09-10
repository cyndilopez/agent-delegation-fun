"""Unified webhook server for pr_bot, ci_bot, and docs_bot."""

from __future__ import annotations

from fastapi import FastAPI, Request

from ci_bot.handler import handle_workflow_run
from docs_bot.handler import handle_pr_for_docs
from pr_bot.agent import run_review
from pr_bot.github import GitHubError, fetch_pr_context, post_review

app = FastAPI()


async def handle_pull_request_opened(payload: dict) -> dict[str, object]:
    action = payload.get("action")
    if action != "opened":
        return {"status": "ignored", "reason": "unhandled-action"}

    repo = payload.get("repository") or {}
    owner = (repo.get("owner") or {}).get("login")
    repo_name = repo.get("name")
    pr = payload.get("pull_request") or {}
    number = pr.get("number")

    if not owner or not repo_name or not number:
        return {"status": "ignored", "reason": "missing-repository"}

    try:
        ctx = await fetch_pr_context(owner, repo_name, number)
        review = await run_review(ctx)
        await post_review(owner, repo_name, number, review, author_login=ctx.author_login)
    except GitHubError as exc:
        logger.exception("pull_request review failed")
        return {"status": "error", "reason": "github-error", "message": str(exc)}
    except Exception:
        logger.exception("pull_request review failed")
        raise

    try:
        docs_result = await handle_pr_for_docs(payload)
    except Exception:
        logger.exception("docs_bot failed after review posted")
        return {"status": "partial", "reason": "docs-failed", "review": "posted"}

    return {"status": "ok", "docs": docs_result}


@app.post("/webhook/github")
async def github_webhook(request: Request) -> dict[str, object]:
    event = request.headers.get("X-GitHub-Event", "")
    payload = await request.json()

    if event == "pull_request":
        return await handle_pull_request_opened(payload)
    if event == "workflow_run":
        return await handle_workflow_run(payload)

    return {"status": "ignored", "reason": "unhandled-event"}
