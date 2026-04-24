"""Favicon fetching utilities"""

from html.parser import HTMLParser
import logging
import re
from urllib.parse import quote, urljoin, urlparse

import httpx

from app.config import get_settings
from app.utils.security import is_safe_url

logger = logging.getLogger(__name__)

MAX_FAVICON_BYTES = 512 * 1024
MIN_FAVICON_BYTES = 16
ALLOWED_ICON_CONTENT_TYPES = {
    "image/x-icon": ".ico",
    "image/vnd.microsoft.icon": ".ico",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
SNIFFABLE_ICON_CONTENT_TYPES = {
    "",
    "application/octet-stream",
    "binary/octet-stream",
    "application/ico",
    "application/x-ico",
    "application/x-icon",
}
HTML_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
ICON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
}


class IconLinkParser(HTMLParser):
    """Extract common favicon link tags from a page head."""

    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "link":
            return

        attr_map = {key.lower(): value for key, value in attrs if key and value}
        href = attr_map.get("href")
        rel = attr_map.get("rel", "").lower()
        rel_tokens = set(rel.split())
        if href and (
            "icon" in rel_tokens
            or "apple-touch-icon" in rel_tokens
            or "apple-touch-icon-precomposed" in rel_tokens
        ):
            self.hrefs.append(href)


def _content_type(response: httpx.Response) -> str:
    return response.headers.get("content-type", "").split(";", 1)[0].strip().lower()


def _content_length_too_large(response: httpx.Response) -> bool:
    try:
        return int(response.headers.get("content-length", "0")) > MAX_FAVICON_BYTES
    except ValueError:
        return False


def _validated_icon_extension(response: httpx.Response) -> tuple[str | None, str]:
    if response.status_code != 200:
        return None, f"HTTP {response.status_code}"
    if _content_length_too_large(response):
        return None, "图标文件过大"
    if len(response.content) < MIN_FAVICON_BYTES:
        return None, "内容过小"
    if len(response.content) > MAX_FAVICON_BYTES:
        return None, "图标文件过大"

    content_type = _content_type(response)
    extension = ALLOWED_ICON_CONTENT_TYPES.get(content_type)
    if extension is None and (
        content_type in SNIFFABLE_ICON_CONTENT_TYPES or content_type.startswith("image/")
    ):
        extension = _sniff_icon_extension(response.content)
    if extension is None:
        return None, f"不支持的图标类型: {content_type or 'unknown'}"
    return extension, ""


def _sniff_icon_extension(content: bytes) -> str | None:
    if content.startswith(b"\x00\x00\x01\x00") or content.startswith(b"\x00\x00\x02\x00"):
        return ".ico"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if content.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return ".webp"
    return None


def _unsupported_proxy_error(exc: Exception) -> bool:
    detail = str(exc)
    return "Unknown scheme for proxy URL" in detail or "socksio" in detail


async def _get_with_safe_redirects(
    client: httpx.AsyncClient,
    url: str,
    *,
    headers: dict[str, str],
    max_redirects: int = 5,
) -> httpx.Response:
    current_url = url
    for _ in range(max_redirects + 1):
        is_safe, error_msg = is_safe_url(current_url)
        if not is_safe:
            raise ValueError(error_msg)

        response = await client.get(current_url, headers=headers)
        if response.status_code not in {301, 302, 303, 307, 308}:
            return response

        location = response.headers.get("location")
        if not location:
            return response

        current_url = urljoin(str(response.url), location)

    raise ValueError("重定向次数过多")


async def _safe_get(
    url: str,
    *,
    headers: dict[str, str],
    timeout: float,
) -> httpx.Response:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            return await _get_with_safe_redirects(client, url, headers=headers)
    except Exception as exc:
        if not _unsupported_proxy_error(exc):
            raise

        logger.warning("Configured proxy is not supported by httpx, retrying favicon request without proxy")
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            return await _get_with_safe_redirects(client, url, headers=headers)


def _icon_urls_from_html(page_url: str, html: str) -> list[str]:
    parser = IconLinkParser()
    parser.feed(html)

    urls: list[str] = []
    seen: set[str] = set()
    for href in parser.hrefs:
        icon_url = urljoin(page_url, href)
        if icon_url in seen:
            continue
        if is_safe_url(icon_url)[0]:
            urls.append(icon_url)
            seen.add(icon_url)
            logger.info(f"Found icon in HTML: {icon_url}")
    return urls


async def fetch_favicon(url: str) -> dict:
    """Fetch favicon from a website and save it"""
    try:
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "https://" + url
            parsed = urlparse(url)

        is_safe, error_msg = is_safe_url(url)
        if not is_safe:
            logger.warning(f"Unsafe URL rejected: {url} - {error_msg}")
            return {"icon": None, "message": error_msg, "error": True}

        base_url = f"{parsed.scheme}://{parsed.netloc}"
        icons_dir = get_settings().static_dir / "icons"
        icons_dir.mkdir(parents=True, exist_ok=True)

        icon_urls = [
            f"{base_url}/favicon.ico",
            f"{base_url}/favicon.png",
            f"{base_url}/apple-touch-icon.png",
        ]

        # Try to parse icon links from HTML
        try:
            response = await _safe_get(url, headers=HTML_HEADERS, timeout=15.0)
            if response.status_code == 200:
                icon_urls = _icon_urls_from_html(str(response.url), response.text) + icon_urls
        except httpx.TimeoutException:
            logger.warning(f"Timeout while fetching HTML from {url}")
        except httpx.HTTPError as e:
            logger.warning(f"HTTP error while fetching HTML from {url}: {e}")
        except Exception as e:
            logger.warning(f"Error parsing HTML from {url}: {e}")

        # Try to download icons
        last_error = None
        for icon_url in icon_urls:
            if not is_safe_url(icon_url)[0]:
                continue

            try:
                response = await _safe_get(icon_url, headers=ICON_HEADERS, timeout=15.0)
                ext, validation_error = _validated_icon_extension(response)
                if ext:
                    filename = re.sub(r"[^a-zA-Z0-9_-]+", "_", parsed.netloc).strip("_") + ext
                    filepath = icons_dir / filename

                    with open(filepath, "wb") as f:
                        f.write(response.content)

                    logger.info(f"Successfully fetched icon from {icon_url} -> {filename}")
                    return {"icon": filename, "message": "图标获取成功"}
                else:
                    last_error = validation_error
            except httpx.TimeoutException:
                last_error = "请求超时"
                logger.warning(f"Timeout while fetching icon from {icon_url}")
            except httpx.HTTPError as e:
                last_error = f"网络错误: {str(e)}"
                logger.warning(f"HTTP error while fetching icon from {icon_url}: {e}")
            except Exception as e:
                last_error = f"错误: {str(e)}"
                logger.warning(f"Error downloading icon from {icon_url}: {e}")
                continue

        # Try public favicon services as fallbacks. They do not receive the full URL path.
        fallback_urls = [
            f"https://icons.duckduckgo.com/ip3/{quote(parsed.hostname or parsed.netloc)}.ico",
            f"https://www.google.com/s2/favicons?domain={quote(parsed.netloc)}&sz=128",
        ]
        for fallback_url in fallback_urls:
            try:
                response = await _safe_get(fallback_url, headers=ICON_HEADERS, timeout=10.0)
                ext, validation_error = _validated_icon_extension(response)
                if ext:
                    filename = re.sub(r"[^a-zA-Z0-9_-]+", "_", parsed.netloc).strip("_") + ext
                    filepath = icons_dir / filename

                    with open(filepath, "wb") as f:
                        f.write(response.content)

                    logger.info(f"Successfully fetched icon from fallback service -> {filename}")
                    return {"icon": filename, "message": "图标获取成功 (使用备用服务)"}
                last_error = validation_error
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Fallback favicon service failed: {e}")

        error_msg = "未能获取图标"
        if last_error:
            error_msg += f" ({last_error})"
        logger.info(f"Failed to fetch favicon for {url}: {error_msg}")
        return {"icon": None, "message": error_msg}

    except Exception as e:
        logger.error(f"Unexpected error in fetch_favicon for {url}: {e}", exc_info=True)
        return {"icon": None, "message": f"获取图标时发生错误: {str(e)}"}
