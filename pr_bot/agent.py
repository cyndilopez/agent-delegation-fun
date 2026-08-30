from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai import Agent

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


def _model_name() -> str:
    explicit = os.getenv("PR_BOT_MODEL")
    if explicit:
        return explicit
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise ValueError("ANTHROPIC_API_KEY is not set (add it to .env)")
    return "anthropic:claude-haiku-4-5"


def _anthropic_model_id(model: str) -> str:
    prefix = "anthropic:"
    return model[len(prefix) :] if model.startswith(prefix) else model


@lru_cache(maxsize=1)
def _get_agent() -> Agent[None, ReviewOutput]:
    model = _model_name()
    system_prompt = _load_system_prompt()
    workspace_id = os.getenv("ANTHROPIC_WORKSPACE_ID")
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if workspace_id and api_key and model.startswith("anthropic:"):
        from anthropic import AsyncAnthropic
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider

        client = AsyncAnthropic(
            api_key=api_key,
            default_headers={"anthropic-workspace-id": workspace_id},
        )
        provider = AnthropicProvider(anthropic_client=client)
        anthropic_model = AnthropicModel(_anthropic_model_id(model), provider=provider)
        return Agent(anthropic_model, output_type=ReviewOutput, system_prompt=system_prompt)

    return Agent(model, output_type=ReviewOutput, system_prompt=system_prompt)


async def run_review(ctx: PullRequestContext) -> ReviewOutput:
    """Run the review agent against a pull request context."""
    result = await _get_agent().run(_build_user_prompt(ctx))
    return result.output
