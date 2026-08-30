"""GitHub Actions API helpers for CI failure handling."""

from __future__ import annotations

import io
import re
import zipfile

import httpx

from bot_shared.github_auth import GitHubError, github_get, github_headers
from ci_bot.models import CIFailureContext, DiagnosisOutput
from pr_bot.github import fetch_pr_context
from pr_bot.models import ChangedFile

RUN_URL_RE = re.compile(
    r"github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/actions/runs/(?P<run_id>\d+)",
    re.IGNORECASE,
)


def parse_run_url(url: str) -> tuple[str, str, int]:
    match = RUN_URL_RE.search(url.strip())
    if not match:
        raise ValueError(f"Not a GitHub Actions run URL: {url}")
    return match.group("owner"), match.group("repo"), int(match.group("run_id"))


async def _fetch_job_logs(client: httpx.AsyncClient, owner: str, repo: str, job_id: int) -> str:
    resp = await client.get(
        f"https://api.github.com/repos/{owner}/{repo}/actions/jobs/{job_id}/logs",
        follow_redirects=True,
    )
    if resp.status_code >= 400:
        raise GitHubError(f"Failed to fetch job logs: {resp.status_code} {resp.text}")

    if not resp.content:
        return ""

    try:
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            chunks: list[str] = []
            for name in zf.namelist():
                chunks.append(zf.read(name).decode("utf-8", errors="replace"))
            return "\n".join(chunks)
    except zipfile.BadZipFile:
        return resp.text


async def _find_open_pr(
    client: httpx.AsyncClient, owner: str, repo: str, head_branch: str
) -> tuple[int | None, str | None, list[ChangedFile]]:
    resp = await github_get(
        client,
        f"https://api.github.com/repos/{owner}/{repo}/pulls",
        params={"head": f"{owner}:{head_branch}", "state": "open"},
    )
    pulls = resp.json()
    if not pulls:
        return None, None, []

    pr = pulls[0]
    number = pr["number"]
    ctx = await fetch_pr_context(owner, repo, number)
    return number, ctx.title, ctx.files


async def fetch_failure_context(owner: str, repo: str, run_id: int) -> CIFailureContext:
    async with httpx.AsyncClient(headers=github_headers(), timeout=120.0) as client:
        run_resp = await github_get(
            client, f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}"
        )
        run = run_resp.json()

        if run.get("conclusion") != "failure":
            raise GitHubError(f"Run {run_id} did not fail (conclusion={run.get('conclusion')})")

        head_branch = (run.get("head_branch") or "").strip()
        if not head_branch:
            raise GitHubError(f"Run {run_id} has no head_branch")

        jobs_resp = await github_get(
            client,
            f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/jobs",
        )
        jobs = jobs_resp.json().get("jobs", [])
        failed_jobs = [j for j in jobs if j.get("conclusion") == "failure"]
        if not failed_jobs:
            raise GitHubError(f"Run {run_id} has no failed jobs")

        job = failed_jobs[0]
        logs = await _fetch_job_logs(client, owner, repo, job["id"])
        pr_number, pr_title, files = await _find_open_pr(client, owner, repo, head_branch)

    return CIFailureContext(
        owner=owner,
        repo=repo,
        head_branch=head_branch,
        workflow_name=run.get("name") or "workflow",
        run_id=run_id,
        job_name=job.get("name") or "job",
        logs=logs,
        pr_number=pr_number,
        pr_title=pr_title,
        files=files,
    )


def _diagnosis_body(ctx: CIFailureContext, diagnosis: DiagnosisOutput) -> str:
    run_url = f"https://github.com/{ctx.owner}/{ctx.repo}/actions/runs/{ctx.run_id}"
    parts = [
        "## CI failure diagnosis",
        "",
        diagnosis.summary,
        "",
        f"**Workflow:** {ctx.workflow_name} · **Job:** {ctx.job_name} · "
        f"[Run #{ctx.run_id}]({run_url})",
        "",
        "### Root cause",
        "",
        diagnosis.root_cause,
        "",
        "### Suggested fix",
        "",
        diagnosis.suggested_fix,
    ]
    return "\n".join(parts)


async def post_diagnosis_comment(
    owner: str, repo: str, pr_number: int, ctx: CIFailureContext, diagnosis: DiagnosisOutput
) -> dict:
    async with httpx.AsyncClient(headers=github_headers(), timeout=60.0) as client:
        resp = await client.post(
            f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments",
            json={"body": _diagnosis_body(ctx, diagnosis)},
        )
        if resp.status_code >= 400:
            raise GitHubError(f"Failed to post comment: {resp.status_code} {resp.text}")
        return resp.json()
