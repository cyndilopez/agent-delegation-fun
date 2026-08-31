"""Docs update agent CLI."""

from __future__ import annotations

import argparse
import asyncio
import sys

from docs_bot.git_ops import GitError, create_branch_with_edits, open_pull_request
from docs_bot.handler import build_doc_review_context
from docs_bot.agent import run_doc_review
from pr_bot.github import GitHubError, parse_pr_url


async def _check_pr(owner: str, repo: str, number: int) -> int:
    doc_ctx = await build_doc_review_context(owner, repo, number)
    update = await run_doc_review(doc_ctx)
    if not update.docs_changed or not update.edits:
        return 0

    branch = f"docs/arch-update-pr-{number}"
    create_branch_with_edits(
        owner,
        repo,
        base_branch=doc_ctx.base_branch,
        new_branch=branch,
        edits=update.edits,
        commit_message=update.commit_message,
    )
    await open_pull_request(
        owner,
        repo,
        head_branch=branch,
        base_branch=doc_ctx.base_branch,
        title=update.pr_title,
        body=update.pr_body or update.summary,
    )
    return 0


async def _cmd_check(args: argparse.Namespace) -> int:
    try:
        owner, repo, number = parse_pr_url(args.pr_url)
        return await _check_pr(owner, repo, number)
    except (ValueError, GitHubError, GitError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Project docs update agent")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="Check a PR and open a docs PR if docs need updating")
    check.add_argument("pr_url", help="GitHub PR URL")
    check.set_defaults(func=lambda args: asyncio.run(_cmd_check(args)))

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
