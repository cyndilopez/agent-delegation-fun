"""Unified webhook server for pr_bot, ci_bot, and docs_bot."""

from __future__ import annotations

import json
import logging

from fastapi import BackgroundTasks, FastAPI, Request

from ci_bot.handler import handle_workflow_run
from docs_bot.handler import handle_pr_for_docs
from pr_bot.agent import run_review
from pr_bot.github import fetch_pr_context, post_review

logger = logging.getLogger(__name__)

app = FastAPI()

_PR_REVIEW_ACTIONS = {"opened"}
_DOCS_BOT_ACTIONS = {"opened"}


async def _run_pull_request(payload: dict) -> None:
    try:
        result = await handle_pull_request(payload)
        logger.info("pull_request handled: %s", result)
    except Exception:
        logger.exception("pull_request handler failed")


async def _run_workflow_run(payload: dict) -> None:
    try:
        result = await handle_workflow_run(payload)
        logger.info("workflow_run handled: %s", result)
    except Exception:
        logger.exception("workflow_run handler failed")


async def handle_pull_request(payload: dict) -> dict[str, object]:
    action = payload.get("action")
    repo = payload.get("repository") or {}
    owner = (repo.get("owner") or {}).get("login")
    repo_name = repo.get("name")
    pr = payload.get("pull_request") or {}
    number = pr.get("number")

    if not owner or not repo_name or not number:
        return {"status": "ignored", "reason": "missing-repository"}

    review_result: dict[str, object] | None = None
    if action in _PR_REVIEW_ACTIONS:
        try:
            ctx = await fetch_pr_context(owner, repo_name, number)
            review = await run_review(ctx)
            await post_review(owner, repo_name, number, review, author_login=ctx.author_login)
            review_result = {"status": "ok"}
        except Exception as exc:
            logger.exception("pull_request review failed")
            review_result = {"status": "error", "reason": "review-failed", "message": str(exc)}
    elif action not in _DOCS_BOT_ACTIONS:
        return {"status": "ignored", "reason": "unhandled-action"}

    docs_result: dict[str, object] = {"status": "skipped", "reason": "unhandled-action"}
    if action in _DOCS_BOT_ACTIONS:
        try:
            docs_result = await handle_pr_for_docs(payload)
        except Exception:
            logger.exception("docs_bot failed after review posted")
            if review_result and review_result.get("status") == "ok":
                return {"status": "partial", "reason": "docs-failed", "review": "posted"}
            docs_result = {"status": "error", "reason": "docs-failed"}

    if review_result:
        return {"status": "ok", "action": action, "review": review_result, "docs": docs_result}
    return {"status": "ok", "action": action, "docs": docs_result}


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, object]:
    event = request.headers.get("X-GitHub-Event", "")
    delivery_id = request.headers.get("X-GitHub-Delivery", "")

    try:
        body = await request.body()
        if not body.strip():
            logger.warning("webhook empty body event=%s delivery_id=%s", event, delivery_id)
            return {"status": "error", "reason": "empty-body"}
        payload = json.loads(body)
    except Exception:
        logger.exception(
            "webhook invalid json event=%s delivery_id=%s",
            event,
            delivery_id,
        )
        return {"status": "error", "reason": "invalid-json"}

    action = payload.get("action")
    logger.info(
        "github webhook received event=%s action=%s delivery_id=%s",
        event,
        action,
        delivery_id,
    )

    if event == "pull_request":
        background_tasks.add_task(_run_pull_request, payload)
        return {"status": "accepted", "event": event, "action": action}
    if event == "workflow_run":
        background_tasks.add_task(_run_workflow_run, payload)
        return {"status": "accepted", "event": event, "action": action}

    return {"status": "ignored", "reason": "unhandled-event"}
