from __future__ import annotations

from pydantic import BaseModel


class FileEdit(BaseModel):
    path: str
    content: str
