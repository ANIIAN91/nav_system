"""HTTP helpers for the API layer."""

from fastapi import HTTPException

from app.application.errors import ApplicationError


def raise_http_error(exc: ApplicationError) -> None:
    """Raise an HTTPException from an application-layer exception."""
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
