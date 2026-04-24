"""Asset-related use cases."""

from app.application.errors import BadRequestError
from app.core import validate_safe_external_url
from app.utils.favicon import fetch_favicon


class FetchFaviconUseCase:
    async def execute(self, url: str) -> dict:
        try:
            normalized_url = validate_safe_external_url(url, infer_https=True)
        except ValueError as exc:
            raise BadRequestError(str(exc)) from exc

        result = await fetch_favicon(normalized_url)
        if result.get("error"):
            raise BadRequestError(result["message"])
        return result
