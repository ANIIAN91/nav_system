"""Application-level exceptions."""


class ApplicationError(Exception):
    """Base application error that carries an HTTP-compatible status code."""

    status_code = 400

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class BadRequestError(ApplicationError):
    """400 error for invalid requests."""


class UnauthorizedError(ApplicationError):
    """401 error."""

    status_code = 401


class ForbiddenError(ApplicationError):
    """403 error."""

    status_code = 403


class NotFoundError(ApplicationError):
    """404 error."""

    status_code = 404
