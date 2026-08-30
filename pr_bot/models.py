from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReviewFinding(BaseModel):
    title: str
    location: str | None = None
    issue: str
    severity: Literal["blocker", "high", "medium", "question"] = "medium"


class ReviewOutput(BaseModel):
    summary: str
    verdict: Literal["comment", "request_changes"]
    findings: list[ReviewFinding] = Field(default_factory=list)


class ChangedFile(BaseModel):
    filename: str
    patch: str | None = None
    status: str = "modified"


class PullRequestContext(BaseModel):
    owner: str
    repo: str
    number: int
    title: str
    body: str = ""
    base_branch: str = "main"
    head_branch: str = "feature"
    files: list[ChangedFile] = Field(default_factory=list)
