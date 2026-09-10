"""GitHub API helpers for fetching PRs and posting reviews."""

from __future__ import annotations

import os
import re

import httpx

from pr_bot.models import ChangedFile, PullRequestContext, ReviewOutput

PR_URL_RE = re.compile(
    r"github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)",
    re.IGNORECASE,
)

_EVENT_BY_VERDICT = {
    "approve": "APPROVE",
    "comment": "COMMENT",
    "request_changes": "REQUEST_CHANGES",
}


class GitHubError(Exception):
    """Raised when the GitHub API returns an error."""


def parse_pr_url(url: str) -> tuple[str, str, int]:
    match = PR_URL_RE.search(url.strip())
    if not match:
        raise ValueError(f"Not a GitHub PR URL: {url}")
    return match.group("owner"), match.group("repo"), int(match.group("number"))


def _headers() -> dict[str, str]:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise GitHubError("GITHUB_TOKEN is not set")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def fetch_pr_context(owner: str, repo: str, number: int) -> PullRequestContext:
    async with httpx.AsyncClient(headers=_headers(), timeout=60.0) as client:
        pr_resp = await client.get(f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}")
        if pr_resp.status_code >= 400:
            raise GitHubError(f"Failed to fetch PR: {pr_resp.status_code} {pr_resp.text}")

        files_resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}/files"
        )
        if files_resp.status_code >= 400:
            raise GitHubError(f"Failed to fetch PR files: {files_resp.status_code} {files_resp.text}")

        pr = pr_resp.json()
        files_data = files_resp.json()

    files = [
        ChangedFile(
            filename=item["filename"],
            patch=item.get("patch"),
            status=item.get("status", "modified"),
        )
        for item in files_data
    ]

    return PullRequestContext(
        owner=owner,
        repo=repo,
        number=number,
        title=pr["title"],
        body=pr.get("body") or "",
        author_login=(pr.get("user") or {}).get("login") or "",
        base_branch=pr["base"]["ref"],
        head_branch=pr["head"]["ref"],
        files=files,
    )


async def _authenticated_login(client: httpx.AsyncClient) -> str:
    resp = await client.get("https://api.github.com/user")
    if resp.status_code >= 400:
        raise GitHubError(f"Failed to fetch authenticated user: {resp.status_code} {resp.text}")
    login = resp.json().get("login")
    if not login:
        raise GitHubError("GitHub user response missing login")
    return login


def _review_event(verdict: str, *, self_review: bool) -> str:
    event = _EVENT_BY_VERDICT[verdict]
    if self_review and event in {"APPROVE", "REQUEST_CHANGES"}:
        return "COMMENT"
    return event


def _review_body(review: ReviewOutput) -> str:
    parts = [review.summary]
    inline_keys: set[tuple[str, int]] = set()

    for finding in review.findings:
        location = finding.location or "general"
        if location != "general" and ":" in location:
            path, _, line_str = location.partition(":")
            try:
                line = int(line_str.strip())
                inline_keys.add((path.strip(), line))
            except ValueError:
                pass
        parts.append(f"- **[{finding.severity}] {finding.title}** ({location}): {finding.issue}")

    return "\n\n".join(parts)


def _inline_comments(review: ReviewOutput) -> list[dict[str, object]]:
    comments: list[dict[str, object]] = []
    seen: set[tuple[str, int]] = set()

    for finding in review.findings:
        if not finding.location or ":" not in finding.location:
            continue
        path, _, line_str = finding.location.partition(":")
        try:
            line = int(line_str.strip())
        except ValueError:
            continue

        key = (path.strip(), line)
        if key in seen:
            continue
        seen.add(key)

        comments.append(
            {
                "path": path.strip(),
                "line": line,
                "side": "RIGHT",
                "body": f"**[{finding.severity}] {finding.title}**\n\n{finding.issue}",
            }
        )

    return comments


async def post_review(
    owner: str,
    repo: str,
    number: int,
    review: ReviewOutput,
    *,
    author_login: str = "",
) -> dict:
    comments = _inline_comments(review)
    body = _review_body(review)

    async with httpx.AsyncClient(headers=_headers(), timeout=60.0) as client:
        bot_login = await _authenticated_login(client)
        self_review = bool(
            author_login and author_login.lower() == bot_login.lower()
        )
        event = _review_event(review.verdict, self_review=self_review)
        if self_review and event == "COMMENT" and review.verdict != "comment":
            body = (
                f"_Review verdict `{review.verdict}` downgraded to comment because "
                f"the bot cannot {review.verdict.replace('_', ' ')} its own pull request._\n\n"
                f"{body}"
            )

        payload: dict[str, object] = {"body": body, "event": event}
        if comments:
            payload["comments"] = comments

        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}/reviews"
        resp = await client.post(url, json=payload)
        if resp.status_code >= 400 and comments:
            # Inline comments fail when the line is not part of the diff.
            resp = await client.post(url, json={"body": body, "event": event})
        if resp.status_code >= 400:
            raise GitHubError(f"Failed to post review: {resp.status_code} {resp.text}")
        return resp.json()
