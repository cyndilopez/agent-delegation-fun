"""CI diagnosis agent CLI."""

from __future__ import annotations

import argparse
import asyncio
import sys

from ci_bot.agent import run_diagnosis
from ci_bot.github import GitHubError, fetch_failure_context, parse_run_url, post_diagnosis_comment


async def _diagnose_run(owner: str, repo: str, run_id: int) -> int:
    ctx = await fetch_failure_context(owner, repo, run_id)
    if not ctx.pr_number:
        raise GitHubError("No open PR for this branch — cannot post comment.")

    diagnosis = await run_diagnosis(ctx)
    await post_diagnosis_comment(owner, repo, ctx.pr_number, ctx, diagnosis)
    return 0


async def _cmd_diagnose(args: argparse.Namespace) -> int:
    try:
        if args.run_url:
            owner, repo, run_id = parse_run_url(args.run_url)
        else:
            owner, repo, run_id = args.owner, args.repo, args.run_id
        return await _diagnose_run(owner, repo, run_id)
    except (ValueError, GitHubError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CI failure diagnosis agent")
    sub = parser.add_subparsers(dest="command", required=True)

    diagnose = sub.add_parser("diagnose", help="Diagnose a failed run and post a PR comment")
    diagnose.add_argument("run_url", nargs="?", help="GitHub Actions run URL")
    diagnose.add_argument("--owner", help="Repo owner (with --run-id)")
    diagnose.add_argument("--repo", help="Repo name (with --run-id)")
    diagnose.add_argument("--run-id", type=int, help="Actions run ID (with --owner/--repo)")
    diagnose.set_defaults(func=lambda args: asyncio.run(_cmd_diagnose(args)))

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
