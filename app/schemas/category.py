"""Category schemas"""
from typing import Optional, List
from pydantic import BaseModel

class CategoryBase(BaseModel):
    name: str
    auth_required: bool = False

class CategoryCreate(CategoryBase):
    links: List = []

class CategoryUpdate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int

    class Config:
        from_attributes = True
