"""CLI for the PR review agent."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from pr_bot.agent import run_review
from pr_bot.models import PullRequestContext, ReviewOutput

_FIXTURE = Path(__file__).parent / "fixtures" / "sample_pr.json"
_SEVERITY_ORDER = ("blocker", "high", "medium", "question")


def _load_context(path: Path) -> PullRequestContext:
    data = json.loads(path.read_text())
    return PullRequestContext.model_validate(data)


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


async def _cmd_demo() -> int:
    ctx = _load_context(_FIXTURE)
    print(f"Reviewing: {ctx.owner}/{ctx.repo}#{ctx.number} — {ctx.title}\n")
    review = await run_review(ctx)
    _print_review(review)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PR review agent")
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="Review the bundled sample PR fixture")
    demo.set_defaults(func=lambda _: asyncio.run(_cmd_demo()))

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
