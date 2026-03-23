"""Category schemas"""
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class CategoryBase(BaseModel):
    name: str
    auth_required: bool = False

class CategoryCreate(CategoryBase):
    links: List = []

class CategoryUpdate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
