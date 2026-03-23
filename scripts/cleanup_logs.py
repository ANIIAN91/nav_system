#!/usr/bin/env python3
"""Manual log retention cleanup utility."""

import argparse
import asyncio

from app.config import get_settings
from app.database import async_session
from app.services.log import run_log_cleanup_job


async def cleanup_logs(max_visits: int | None, max_updates: int | None) -> dict[str, int]:
    """Run visit/update log retention cleanup."""
    return await run_log_cleanup_job(
        async_session,
        max_visits=max_visits,
        max_updates=max_updates,
    )


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Nav System 日志清理工具")
    parser.add_argument(
        "--max-visits",
        type=int,
        default=settings.max_visit_records,
        help="保留的访问记录数量上限",
    )
    parser.add_argument(
        "--max-updates",
        type=int,
        default=settings.max_update_records,
        help="保留的更新记录数量上限",
    )
    args = parser.parse_args()

    result = asyncio.run(cleanup_logs(args.max_visits, args.max_updates))
    print(f"已删除访问记录: {result['deleted_visits']}")
    print(f"已删除更新记录: {result['deleted_updates']}")
    print(f"当前访问记录保留数: {result['remaining_visits']}")
    print(f"当前更新记录保留数: {result['remaining_updates']}")


if __name__ == "__main__":
    main()
