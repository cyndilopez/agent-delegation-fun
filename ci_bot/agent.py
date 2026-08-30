from __future__ import annotations

from pathlib import Path

from bot_shared.llm import create_agent

from ci_bot.models import CIFailureContext, DiagnosisOutput

_PROMPT_PATH = Path(__file__).parent / "prompt.md"
_MAX_LOG_CHARS = 20_000


def _load_system_prompt() -> str:
    return _PROMPT_PATH.read_text()


def _build_user_prompt(ctx: CIFailureContext) -> str:
    parts = [
        f"# CI failure: {ctx.workflow_name}",
        f"Repo: {ctx.owner}/{ctx.repo}",
        f"Branch: {ctx.head_branch}",
        f"Run ID: {ctx.run_id}",
        f"Failed job: {ctx.job_name}",
    ]
    if ctx.pr_number:
        parts.append(f"PR: #{ctx.pr_number} — {ctx.pr_title or ''}")

    logs = ctx.logs
    if len(logs) > _MAX_LOG_CHARS:
        logs = logs[-_MAX_LOG_CHARS:]
        logs = "... [truncated]\n" + logs

    parts.extend(["", "## CI logs", f"```\n{logs}\n```"])

    if ctx.files:
        parts.append("\n## PR changed files (context)")
        for f in ctx.files:
            parts.append(f"\n### {f.filename} ({f.status})")
            if f.patch:
                parts.append(f"```diff\n{f.patch}\n```")

    return "\n".join(parts)


async def run_diagnosis(ctx: CIFailureContext) -> DiagnosisOutput:
    agent = create_agent(_load_system_prompt(), DiagnosisOutput)
    result = await agent.run(_build_user_prompt(ctx))
    return result.output
