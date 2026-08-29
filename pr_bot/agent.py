from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_ai import Agent

from pr_bot.models import PullRequestContext, ReviewOutput

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


def _model_name() -> str:
    explicit = os.getenv("PR_BOT_MODEL")
    if explicit:
        return explicit
    if os.getenv("OPENAI_API_KEY"):
        return "openai:gpt-4o-mini"
    return "test"


@lru_cache(maxsize=1)
def _get_agent() -> Agent[None, ReviewOutput]:
    return Agent(
        _model_name(),
        output_type=ReviewOutput,
        system_prompt=_load_system_prompt(),
    )


async def run_review(ctx: PullRequestContext) -> ReviewOutput:
    """Run the review agent against a pull request context."""
    result = await _get_agent().run(_build_user_prompt(ctx))
    return result.output
