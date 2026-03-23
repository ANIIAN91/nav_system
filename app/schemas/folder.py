"""Folder schemas."""

from pydantic import BaseModel, Field


class FolderRenameRequest(BaseModel):
    new_name: str


class FolderSummary(BaseModel):
    name: str
    path: str
    article_count: int = 0


class FolderListResponse(BaseModel):
    folders: list[FolderSummary] = Field(default_factory=list)
