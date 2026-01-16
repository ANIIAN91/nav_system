"""Link schemas"""
from typing import Optional, List
from pydantic import BaseModel

class LinkBase(BaseModel):
    title: str
    url: str
    icon: Optional[str] = None

class LinkCreate(LinkBase):
    pass

class LinkUpdate(BaseModel):
    title: str
    url: str
    icon: Optional[str] = None
    category: Optional[str] = None

class LinkResponse(LinkBase):
    id: str

    class Config:
        from_attributes = True

class CategoryWithLinks(BaseModel):
    name: str
    auth_required: bool = False
    links: List[LinkResponse] = []

class LinksData(BaseModel):
    categories: List[CategoryWithLinks] = []

class ReorderRequest(BaseModel):
    direction: str  # up or down

class BatchReorderRequest(BaseModel):
    ids: List[str]  # List of link IDs or category names in new order

class FaviconRequest(BaseModel):
    url: str

class ImportRequest(BaseModel):
    data: dict
    format: str = "native"  # native or sunpanel
