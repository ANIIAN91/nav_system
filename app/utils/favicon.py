"""Favicon fetching utilities"""
import re
from urllib.parse import urlparse, urljoin
from pathlib import Path

import httpx

from app.config import get_settings
from app.utils.security import is_safe_url

settings = get_settings()

async def fetch_favicon(url: str) -> dict:
    """Fetch favicon from a website and save it"""
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
        parsed = urlparse(url)

    is_safe, error_msg = is_safe_url(url)
    if not is_safe:
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
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
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
    except Exception:
        pass

    # Try to download icons
    for icon_url in icon_urls:
        if not is_safe_url(icon_url)[0]:
            continue

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(icon_url, headers={"User-Agent": "Mozilla/5.0"})
                if response.status_code == 200 and len(response.content) > 100:
                    content_type = response.headers.get("content-type", "")
                    ext = ".ico"
                    if "png" in content_type or icon_url.endswith(".png"):
                        ext = ".png"
                    elif "svg" in content_type or icon_url.endswith(".svg"):
                        ext = ".svg"
                    elif "jpeg" in content_type or "jpg" in content_type:
                        ext = ".jpg"

                    filename = parsed.netloc.replace(".", "_") + ext
                    filepath = icons_dir / filename

                    with open(filepath, "wb") as f:
                        f.write(response.content)

                    return {"icon": filename, "message": "图标获取成功"}
        except Exception:
            continue

    return {"icon": None, "message": "未能获取图标"}
