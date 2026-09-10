"""CLI for the PR review agent."""

from __future__ import annotations

import argparse
import asyncio
import sys

from pr_bot.agent import run_review
from pr_bot.github import GitHubError, fetch_pr_context, parse_pr_url, post_review


async def _review_pr(owner: str, repo: str, number: int) -> int:
    ctx = await fetch_pr_context(owner, repo, number)
    review = await run_review(ctx)
    await post_review(owner, repo, number, review, author_login=ctx.author_login)
    return 0


async def _cmd_review(args: argparse.Namespace) -> int:
    try:
        owner, repo, number = parse_pr_url(args.pr_url)
        return await _review_pr(owner, repo, number)
    except (ValueError, GitHubError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _cmd_serve(args: argparse.Namespace) -> int:
    import logging

    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("bots.app").info(
        "starting webhook server (background tasks + self-review fix enabled)"
    )
    uvicorn.run("bots.app:app", host="0.0.0.0", port=args.port, reload=False)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PR review agent")
    sub = parser.add_subparsers(dest="command", required=True)

    review = sub.add_parser("review", help="Review a GitHub pull request and post to GitHub")
    review.add_argument("pr_url", help="GitHub PR URL")
    review.set_defaults(func=lambda args: asyncio.run(_cmd_review(args)))

    serve = sub.add_parser("serve", help="Start webhook server (PR review, CI diagnose, docs)")
    serve.add_argument("--port", type=int, default=8765)
    serve.set_defaults(func=_cmd_serve)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
