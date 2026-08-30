from __future__ import annotations

import os

import httpx


class GitHubError(Exception):
    """Raised when the GitHub API returns an error."""


def github_headers() -> dict[str, str]:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise GitHubError("GITHUB_TOKEN is not set")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def github_get(client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
    resp = await client.get(url, **kwargs)
    if resp.status_code >= 400:
        raise GitHubError(f"GET {url} failed: {resp.status_code} {resp.text}")
    return resp
