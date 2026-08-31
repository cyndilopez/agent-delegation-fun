from __future__ import annotations

from pydantic import BaseModel, Field

from pr_bot.models import ChangedFile


class FileEdit(BaseModel):
    path: str
    content: str


class DocUpdateOutput(BaseModel):
    docs_changed: bool
    summary: str
    commit_message: str = "docs: update project docs"
    pr_title: str = "docs: update project docs"
    pr_body: str = ""
    edits: list[FileEdit] = Field(default_factory=list)


class DocReviewContext(BaseModel):
    owner: str
    repo: str
    number: int
    title: str
    body: str = ""
    base_branch: str = "main"
    head_branch: str = "feature"
    architecture_doc: str = ""
    readme: str = ""
    files: list[ChangedFile] = Field(default_factory=list)
