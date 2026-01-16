"""Favicon fetching utilities"""
import re
import logging
from urllib.parse import urlparse, urljoin
from pathlib import Path

import httpx

from app.config import get_settings
from app.utils.security import is_safe_url

settings = get_settings()
logger = logging.getLogger(__name__)

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
        icons_dir = settings.static_dir / "icons"
        icons_dir.mkdir(parents=True, exist_ok=True)

        icon_urls = [
            f"{base_url}/favicon.ico",
            f"{base_url}/favicon.png",
            f"{base_url}/apple-touch-icon.png",
        ]

        # Try to parse icon links from HTML
        try:
            async with httpx.AsyncClient(
                timeout=15.0,
                follow_redirects=False
            ) as client:
                response = await client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    }
                )
                if response.status_code == 200:
                    html = response.text
                    patterns = [
                        r'<link[^>]*rel=["\'](?:shortcut )?icon["\'][^>]*href=["\']([^"\']+)["\']',
                        r'<link[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\'](?:shortcut )?icon["\']',
                        r'<link[^>]*rel=["\']apple-touch-icon["\'][^>]*href=["\']([^"\']+)["\']',
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, html, re.IGNORECASE)
                        if match:
                            icon_url = match.group(1)
                            if not icon_url.startswith('http'):
                                icon_url = urljoin(base_url, icon_url)
                            if is_safe_url(icon_url)[0]:
                                icon_urls.insert(0, icon_url)
                                logger.info(f"Found icon in HTML: {icon_url}")
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
                async with httpx.AsyncClient(
                    timeout=15.0,
                    follow_redirects=False
                ) as client:
                    response = await client.get(
                        icon_url,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                        }
                    )
                    if response.status_code == 200 and len(response.content) > 100:
                        content_type = response.headers.get("content-type", "")
                        ext = ".ico"
                        if "png" in content_type or icon_url.endswith(".png"):
                            ext = ".png"
                        elif "svg" in content_type or icon_url.endswith(".svg"):
                            ext = ".svg"
                        elif "jpeg" in content_type or "jpg" in content_type:
                            ext = ".jpg"

                        filename = parsed.netloc.replace(".", "_").replace(":", "_") + ext
                        filepath = icons_dir / filename

                        with open(filepath, "wb") as f:
                            f.write(response.content)

                        logger.info(f"Successfully fetched icon from {icon_url} -> {filename}")
                        return {"icon": filename, "message": "图标获取成功"}
                    else:
                        last_error = f"HTTP {response.status_code} or content too small"
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

        error_msg = f"未能获取图标"
        if last_error:
            error_msg += f" ({last_error})"

        # Try Google's favicon service as fallback
        try:
            google_favicon_url = f"https://www.google.com/s2/favicons?domain={parsed.netloc}&sz=128"
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(google_favicon_url)
                if response.status_code == 200 and len(response.content) > 100:
                    filename = parsed.netloc.replace(".", "_").replace(":", "_") + ".png"
                    filepath = icons_dir / filename

                    with open(filepath, "wb") as f:
                        f.write(response.content)

                    logger.info(f"Successfully fetched icon from Google favicon service -> {filename}")
                    return {"icon": filename, "message": "图标获取成功 (使用 Google 服务)"}
        except Exception as e:
            logger.warning(f"Google favicon service also failed: {e}")

        logger.info(f"Failed to fetch favicon for {url}: {error_msg}")
        return {"icon": None, "message": error_msg}

    except Exception as e:
        logger.error(f"Unexpected error in fetch_favicon for {url}: {e}", exc_info=True)
        return {"icon": None, "message": f"获取图标时发生错误: {str(e)}"}
