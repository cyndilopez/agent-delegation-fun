from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from bot_shared.llm import create_agent

from pr_bot.models import PullRequestContext, ReviewOutput

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_PROMPT_PATH = Path(__file__).parent / "prompt.md"
_MAX_PATCH_CHARS = 12_000


def _load_system_prompt() -> str:
    return _PROMPT_PATH.read_text()


def _build_user_prompt(ctx: PullRequestContext) -> str:
    parts = [
        f"# PR: {ctx.owner}/{ctx.repo}#{ctx.number}",
        f"**{ctx.title}**",
        f"Branch: {ctx.head_branch} → {ctx.base_branch}",
        "",
    ]

    if ctx.body.strip():
        parts.extend(["## Description", ctx.body.strip(), ""])

    parts.append("## Diff")
    for f in ctx.files:
        parts.append(f"\n### {f.filename} ({f.status})")
        if f.patch:
            patch = f.patch
            if len(patch) > _MAX_PATCH_CHARS:
                patch = patch[:_MAX_PATCH_CHARS] + "\n... [truncated]"
            parts.append(f"```diff\n{patch}\n```")
        else:
            parts.append("(no patch)")

    return "\n".join(parts)


@lru_cache(maxsize=1)
def _get_agent():
    return create_agent(_load_system_prompt(), ReviewOutput)


async def run_review(ctx: PullRequestContext) -> ReviewOutput:
    """Run the review agent against a pull request context."""
    result = await _get_agent().run(_build_user_prompt(ctx))
    return result.output
