#!/usr/bin/env python3
"""Rename legacy domain-named favicon files to keyed-hash names.

旧版本按域名保存图标（如 github_com.png），任何人都能通过 /static/icons/ 试探收藏过哪些站点。
本脚本把链接引用的旧图标复制为哈希文件名，更新数据库后删除旧文件。

用法：python -m scripts.migrate_icon_names [--dry-run]
"""

import argparse
import asyncio
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from sqlalchemy import select

from app.config import get_settings
from app.database import get_async_session_factory
from app.models import Link
from app.utils.favicon import icon_filename

LEGACY_EXTENSIONS = (".ico", ".png", ".jpg", ".webp", ".gif", ".svg")


def legacy_stems(netloc: str) -> set[str]:
    """Domain-based stems produced by earlier versions of the favicon fetcher."""
    return {
        netloc.replace(".", "_").replace(":", "_"),
        re.sub(r"[^a-zA-Z0-9_-]+", "_", netloc).strip("_"),
    }


def hashed_name_for_legacy_icon(link_url: str, icon: str) -> str | None:
    """Return the new name if icon matches the legacy naming of the link's domain."""
    netloc = urlparse(link_url).netloc
    if not netloc:
        return None
    for stem in legacy_stems(netloc):
        for ext in LEGACY_EXTENSIONS:
            if icon == stem + ext:
                return icon_filename(netloc, ext)
    return None


async def migrate_icon_names(session_factory, icons_dir: Path, dry_run: bool) -> dict[str, str]:
    """Copy legacy icons to hashed names, update links, then delete the legacy files."""
    renamed: dict[str, str] = {}

    async with session_factory() as db:
        links = (await db.execute(select(Link).where(Link.icon.is_not(None)))).scalars().all()
        for link in links:
            new_name = hashed_name_for_legacy_icon(link.url, link.icon)
            if new_name is None:
                continue
            old_path, new_path = icons_dir / link.icon, icons_dir / new_name
            if not old_path.exists() and not new_path.exists():
                print(f"跳过（文件不存在）: {link.icon}")
                continue
            renamed[link.icon] = new_name
            if dry_run:
                continue
            if not new_path.exists():
                shutil.copy2(old_path, new_path)
            link.icon = new_name

        if not dry_run:
            await db.commit()

    if not dry_run:
        for old_name in renamed:
            (icons_dir / old_name).unlink(missing_ok=True)
    return renamed


def main() -> None:
    parser = argparse.ArgumentParser(description="将按域名命名的旧图标迁移为哈希文件名")
    parser.add_argument("--dry-run", action="store_true", help="只列出将要迁移的图标，不做修改")
    args = parser.parse_args()

    # 与应用相同的方式加载 .env：哈希依赖 SECRET_KEY，必须与运行中的应用一致
    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
    settings = get_settings()
    if not settings.secret_key:
        raise SystemExit("SECRET_KEY 未设置，无法生成与应用一致的图标文件名")

    icons_dir = settings.static_dir / "icons"
    renamed = asyncio.run(migrate_icon_names(get_async_session_factory(), icons_dir, args.dry_run))
    for old_name, new_name in renamed.items():
        print(f"{old_name} -> {new_name}")
    action = "将迁移" if args.dry_run else "已迁移"
    print(f"{action} {len(renamed)} 个图标文件")


if __name__ == "__main__":
    main()
