"""Favicon validation tests."""

import httpx

from app.utils.favicon import MAX_FAVICON_BYTES, _validated_icon_extension


def make_response(content_type: str, content: bytes, *, content_length: str | None = None) -> httpx.Response:
    headers = {"content-type": content_type}
    if content_length is not None:
        headers["content-length"] = content_length
    return httpx.Response(200, headers=headers, content=content)


def test_favicon_validation_accepts_known_image_types():
    """Known raster favicon content types should map to safe extensions."""
    response = make_response("image/png; charset=binary", b"x" * 128)

    extension, error = _validated_icon_extension(response)

    assert extension == ".png"
    assert error == ""


def test_favicon_validation_rejects_non_image_content():
    """HTML or unknown content should not be saved as an icon."""
    response = make_response("text/html", b"<html>" + b"x" * 128)

    extension, error = _validated_icon_extension(response)

    assert extension is None
    assert "不支持" in error


def test_favicon_validation_rejects_svg_by_default():
    """SVG favicons are not saved without an explicit sanitization step."""
    response = make_response("image/svg+xml", b"<svg>" + b"x" * 128)

    extension, error = _validated_icon_extension(response)

    assert extension is None
    assert "不支持" in error


def test_favicon_validation_rejects_oversized_content():
    """Oversized icon responses should be rejected before writing to disk."""
    response = make_response("image/png", b"x" * (MAX_FAVICON_BYTES + 1))

    extension, error = _validated_icon_extension(response)

    assert extension is None
    assert "过大" in error


def test_favicon_validation_rejects_oversized_content_length_header():
    """A large Content-Length header should reject the response."""
    response = make_response("image/png", b"x" * 128, content_length=str(MAX_FAVICON_BYTES + 1))

    extension, error = _validated_icon_extension(response)

    assert extension is None
    assert "过大" in error
