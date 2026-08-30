"""Handle workflow_run webhook events for CI failures."""

from __future__ import annotations

from ci_bot.agent import run_diagnosis
from ci_bot.github import fetch_failure_context, post_diagnosis_comment


async def handle_workflow_run(payload: dict) -> dict[str, object]:
    action = payload.get("action")
    if action != "completed":
        return {"status": "ignored", "reason": "unhandled-action"}

    workflow_run = payload.get("workflow_run") or {}
    if workflow_run.get("conclusion") != "failure":
        return {"status": "ignored", "reason": "not-failed"}

    repo = payload.get("repository") or {}
    owner = (repo.get("owner") or {}).get("login")
    repo_name = repo.get("name")
    run_id = workflow_run.get("id")

    if not owner or not repo_name or not run_id:
        return {"status": "ignored", "reason": "missing-repository"}

    head_branch = workflow_run.get("head_branch")
    if not head_branch:
        return {"status": "ignored", "reason": "missing-head-branch"}

    ctx = await fetch_failure_context(owner, repo_name, run_id)
    diagnosis = await run_diagnosis(ctx)

    if not ctx.pr_number:
        return {
            "status": "skipped",
            "reason": "no-open-pr",
            "summary": diagnosis.summary,
        }

    comment = await post_diagnosis_comment(owner, repo_name, ctx.pr_number, ctx, diagnosis)
    return {
        "status": "ok",
        "pr": ctx.pr_number,
        "comment_url": comment.get("html_url"),
        "summary": diagnosis.summary,
    }
