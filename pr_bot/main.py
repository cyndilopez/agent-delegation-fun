"""CLI for the PR review agent."""

from __future__ import annotations

import argparse
import asyncio
import sys

from pr_bot.agent import run_review
from pr_bot.github import GitHubError, fetch_pr_context, parse_pr_url, post_review
from pr_bot.models import ReviewOutput

_SEVERITY_ORDER = ("blocker", "high", "medium", "question")


def _print_review(review: ReviewOutput) -> None:
    print(f"Verdict: {review.verdict}\n")
    print(f"Summary:\n{review.summary}\n")

    if not review.findings:
        print("No findings.")
        return

    for severity in _SEVERITY_ORDER:
        items = [f for f in review.findings if f.severity == severity]
        if not items:
            continue
        print(f"### {severity.title()}")
        for f in items:
            loc = f" (`{f.location}`)" if f.location else ""
            print(f"- **{f.title}**{loc}: {f.issue}")
        print()


async def _review_pr(
    owner: str,
    repo: str,
    number: int,
    *,
    post: bool,
) -> int:
    print(f"Fetching PR: {owner}/{repo}#{number}\n")
    ctx = await fetch_pr_context(owner, repo, number)
    print(f"Reviewing: {ctx.title}\n")
    review = await run_review(ctx)
    _print_review(review)

    if post:
        result = await post_review(owner, repo, number, review)
        print(f"Posted review: {result.get('html_url', 'ok')}")
    else:
        print("Dry run — review not posted (use --post to publish to GitHub)")

    return 0


async def _cmd_review(args: argparse.Namespace) -> int:
    try:
        owner, repo, number = parse_pr_url(args.pr_url)
        return await _review_pr(owner, repo, number, post=args.post)
    except (ValueError, GitHubError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run("bots.app:app", host="0.0.0.0", port=args.port, reload=False)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PR review agent")
    sub = parser.add_subparsers(dest="command", required=True)

    review = sub.add_parser("review", help="Review a GitHub pull request")
    review.add_argument("pr_url", help="GitHub PR URL")
    review.add_argument(
        "--post",
        action="store_true",
        help="Post the review to GitHub (default: dry run, print only)",
    )
    review.set_defaults(func=lambda args: asyncio.run(_cmd_review(args)))

    serve = sub.add_parser("serve", help="Start webhook server (PR review + CI diagnose)")
    serve.add_argument("--port", type=int, default=8765)
    serve.set_defaults(func=_cmd_serve)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
