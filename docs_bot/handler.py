"""Handle pull_request opened events for documentation updates."""

from __future__ import annotations

from pathlib import Path

from docs_bot.agent import run_doc_review
from docs_bot.git_ops import GitError, create_branch_with_edits, open_pull_request
from docs_bot.github import ARCHITECTURE_PATH, README_PATH, fetch_file
from docs_bot.models import DocReviewContext
from pr_bot.github import fetch_pr_context

_REPO_ROOT = Path(__file__).resolve().parent.parent
_FALLBACK_ARCHITECTURE = _REPO_ROOT / "docs" / "architecture.md"
_FALLBACK_README = _REPO_ROOT / "README.md"


def _load_doc(content: str | None, fallback: Path) -> str:
    if content is not None:
        return content
    if fallback.is_file():
        return fallback.read_text()
    return ""


async def build_doc_review_context(owner: str, repo: str, number: int) -> DocReviewContext:
    pr_ctx = await fetch_pr_context(owner, repo, number)
    architecture_doc = await fetch_file(owner, repo, ARCHITECTURE_PATH, pr_ctx.base_branch)
    readme = await fetch_file(owner, repo, README_PATH, pr_ctx.base_branch)

    return DocReviewContext(
        owner=owner,
        repo=repo,
        number=number,
        title=pr_ctx.title,
        body=pr_ctx.body,
        base_branch=pr_ctx.base_branch,
        head_branch=pr_ctx.head_branch,
        architecture_doc=_load_doc(architecture_doc, _FALLBACK_ARCHITECTURE),
        readme=_load_doc(readme, _FALLBACK_README),
        files=pr_ctx.files,
    )


async def handle_pr_for_docs(payload: dict) -> dict[str, object]:
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

    doc_ctx = await build_doc_review_context(owner, repo_name, number)
    update = await run_doc_review(doc_ctx)
    if not update.docs_changed:
        return {"status": "skipped", "reason": "no-doc-change", "summary": update.summary}

    if not update.edits:
        return {"status": "skipped", "reason": "no-edits", "summary": update.summary}

    branch = f"docs/arch-update-pr-{number}"
    try:
        create_branch_with_edits(
            owner,
            repo_name,
            base_branch=doc_ctx.base_branch,
            new_branch=branch,
            edits=update.edits,
            commit_message=update.commit_message,
        )
        docs_pr = await open_pull_request(
            owner,
            repo_name,
            head_branch=branch,
            base_branch=doc_ctx.base_branch,
            title=update.pr_title,
            body=update.pr_body or update.summary,
        )
    except GitError as exc:
        return {"status": "error", "reason": "git-failed", "message": str(exc)}

    return {
        "status": "ok",
        "docs_pr": docs_pr.get("html_url"),
        "summary": update.summary,
    }
