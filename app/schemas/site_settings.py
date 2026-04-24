"""Site settings schemas."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config import GITHUB_URL, VERSION

ALLOWED_LINK_SIZES = {"small", "medium", "large"}


class PublicSiteSettingsBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    icp: str = ""
    copyright: str = ""
    article_page_title: str = "文章"
    site_title: str = "个人主页导航"
    link_size: str = "medium"
    github_url: str = GITHUB_URL
    timezone: str = "Asia/Shanghai"

    @field_validator("link_size")
    @classmethod
    def validate_link_size(cls, value: str) -> str:
        if value not in ALLOWED_LINK_SIZES:
            raise ValueError("link_size 必须是 small、medium 或 large")
        return value


class SiteSettingsBase(PublicSiteSettingsBase):
    protected_article_paths: list[str] = Field(default_factory=list)


class SiteSettingsUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    icp: str | None = None
    copyright: str | None = None
    article_page_title: str | None = None
    site_title: str | None = None
    link_size: str | None = None
    protected_article_paths: list[str] | None = None
    github_url: str | None = None
    timezone: str | None = None

    @field_validator("link_size")
    @classmethod
    def validate_optional_link_size(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value not in ALLOWED_LINK_SIZES:
            raise ValueError("link_size 必须是 small、medium 或 large")
        return value


class PublicSiteSettingsResponse(PublicSiteSettingsBase):
    version: str = VERSION


class SiteSettingsResponse(SiteSettingsBase):
    version: str = VERSION


class SiteSettingsUpdateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    settings: SiteSettingsResponse
