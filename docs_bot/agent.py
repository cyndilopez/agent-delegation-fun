from __future__ import annotations

from pathlib import Path

from bot_shared.llm import create_agent

from docs_bot.models import DocReviewContext, DocUpdateOutput

_PROMPT_PATH = Path(__file__).parent / "prompt.md"
_MAX_PATCH_CHARS = 12_000
_MAX_DOC_CHARS = 30_000


def _load_system_prompt() -> str:
    return _PROMPT_PATH.read_text()


def _build_user_prompt(ctx: DocReviewContext) -> str:
    parts = [
        f"# Source PR: {ctx.owner}/{ctx.repo}#{ctx.number}",
        f"**{ctx.title}**",
        f"Branch: {ctx.head_branch} → {ctx.base_branch}",
        "",
    ]

    if ctx.body.strip():
        parts.extend(["## PR description", ctx.body.strip(), ""])

    doc = ctx.architecture_doc
    if len(doc) > _MAX_DOC_CHARS:
        doc = doc[:_MAX_DOC_CHARS] + "\n... [truncated]"
    parts.extend(["## Current docs/architecture.md", f"```markdown\n{doc}\n```", ""])

    readme = ctx.readme
    if len(readme) > _MAX_DOC_CHARS:
        readme = readme[:_MAX_DOC_CHARS] + "\n... [truncated]"
    parts.extend(["## Current README.md", f"```markdown\n{readme}\n```", ""])

    parts.append("## PR diff")
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


async def run_doc_review(ctx: DocReviewContext) -> DocUpdateOutput:
    agent = create_agent(_load_system_prompt(), DocUpdateOutput)
    result = await agent.run(_build_user_prompt(ctx))
    return result.output
