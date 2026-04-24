"""Category schemas"""
from typing import List

from pydantic import BaseModel, ConfigDict, field_validator

CATEGORY_NAME_ERROR = "分类名称不能为空，且不能包含 / 或 \\"

class CategoryBase(BaseModel):
    name: str
    auth_required: bool = False

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        name = value.strip()
        if not name or "/" in name or "\\" in name:
            raise ValueError(CATEGORY_NAME_ERROR)
        return name

class CategoryCreate(CategoryBase):
    links: List = []

class CategoryUpdate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
