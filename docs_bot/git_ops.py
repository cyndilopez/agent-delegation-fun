"""Git operations for docs_bot PR creation."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import httpx

from bot_shared.github_auth import GitHubError, github_headers
from docs_bot.models import FileEdit


class GitError(Exception):
    """Raised when a git operation fails."""


def _run(cmd: list[str], *, cwd: Path | None = None) -> None:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise GitError(
            f"Command failed: {' '.join(cmd)}\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )


def _repo_url(owner: str, repo: str) -> str:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise GitError("GITHUB_TOKEN is not set")
    return f"https://x-access-token:{token}@github.com/{owner}/{repo}.git"


def create_branch_with_edits(
    owner: str,
    repo: str,
    *,
    base_branch: str,
    new_branch: str,
    edits: list[FileEdit],
    commit_message: str,
) -> None:
    if not edits:
        raise GitError("No edits to apply")

    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        _run(["git", "clone", "--depth", "1", "--branch", base_branch, _repo_url(owner, repo), str(workdir)])
        _run(["git", "checkout", "-b", new_branch], cwd=workdir)

        for edit in edits:
            path = workdir / edit.path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(edit.content)

        _run(["git", "add", "-A"], cwd=workdir)
        _run(
            [
                "git",
                "-c",
                "user.email=bot@local",
                "-c",
                "user.name=agent-bot",
                "commit",
                "-m",
                commit_message,
            ],
            cwd=workdir,
        )
        _run(["git", "push", "-u", "origin", new_branch, "--force-with-lease"], cwd=workdir)


async def find_open_pull_request(owner: str, repo: str, head_branch: str) -> dict | None:
    async with httpx.AsyncClient(headers=github_headers(), timeout=60.0) as client:
        resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/pulls",
            params={"head": f"{owner}:{head_branch}", "state": "open", "per_page": 1},
        )
        if resp.status_code >= 400:
            raise GitHubError(f"Failed to list PRs: {resp.status_code} {resp.text}")
        items = resp.json()
        return items[0] if items else None


async def open_pull_request(
    owner: str,
    repo: str,
    *,
    head_branch: str,
    base_branch: str,
    title: str,
    body: str,
) -> dict:
    existing = await find_open_pull_request(owner, repo, head_branch)
    if existing:
        return existing

    payload = {"title": title, "head": head_branch, "base": base_branch, "body": body}
    async with httpx.AsyncClient(headers=github_headers(), timeout=60.0) as client:
        resp = await client.post(f"https://api.github.com/repos/{owner}/{repo}/pulls", json=payload)
        if resp.status_code >= 400:
            raise GitHubError(f"Failed to open PR: {resp.status_code} {resp.text}")
        return resp.json()
