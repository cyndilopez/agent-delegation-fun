from __future__ import annotations

from pydantic import BaseModel, Field

from pr_bot.models import ChangedFile


class DiagnosisOutput(BaseModel):
    summary: str
    root_cause: str
    suggested_fix: str


class CIFailureContext(BaseModel):
    owner: str
    repo: str
    head_branch: str
    workflow_name: str
    run_id: int
    job_name: str
    logs: str
    pr_number: int | None = None
    pr_title: str | None = None
    files: list[ChangedFile] = Field(default_factory=list)
