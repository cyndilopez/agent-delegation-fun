from __future__ import annotations

import base64

import httpx

from bot_shared.github_auth import GitHubError, github_get, github_headers

ARCHITECTURE_PATH = "docs/architecture.md"
README_PATH = "README.md"


async def fetch_file(owner: str, repo: str, path: str, ref: str) -> str | None:
    async with httpx.AsyncClient(headers=github_headers(), timeout=60.0) as client:
        resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
            params={"ref": ref},
        )
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            raise GitHubError(f"Failed to fetch {path}: {resp.status_code} {resp.text}")

        data = resp.json()
        content = data.get("content", "")
        encoding = data.get("encoding", "base64")
        if encoding == "base64":
            return base64.b64decode(content).decode("utf-8")
        return content
