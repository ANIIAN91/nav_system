#!/usr/bin/env python3
"""
Database backup and restore script
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.database import async_session
from app.models import Category, Link, Setting, VisitLog, UpdateLog
from app.config import get_settings

settings = get_settings()

async def backup_to_json(output_dir: Path = None):
    """Backup database to JSON files"""
    if output_dir is None:
        output_dir = settings.data_dir / "backups"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = output_dir / f"backup_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    async with async_session() as db:
        # Backup categories and links
        result = await db.execute(select(Category).order_by(Category.sort_order))
        categories = result.scalars().all()

        links_data = {"categories": []}
        for cat in categories:
            result = await db.execute(
                select(Link).where(Link.category_id == cat.id).order_by(Link.sort_order)
            )
            links = result.scalars().all()

            links_data["categories"].append({
                "name": cat.name,
                "auth_required": cat.auth_required,
                "links": [
                    {
                        "id": str(link.id),
                        "title": link.title,
                        "url": link.url,
                        "icon": link.icon
                    }
                    for link in links
                ]
            })

        with open(backup_dir / "links.json", "w", encoding="utf-8") as f:
            json.dump(links_data, f, ensure_ascii=False, indent=2)

        # Backup settings
        result = await db.execute(select(Setting))
        settings_list = result.scalars().all()
        settings_data = {}
        for s in settings_list:
            try:
                settings_data[s.key] = json.loads(s.value)
            except:
                settings_data[s.key] = s.value

        with open(backup_dir / "settings.json", "w", encoding="utf-8") as f:
            json.dump(settings_data, f, ensure_ascii=False, indent=2)

        # Backup visit logs
        result = await db.execute(select(VisitLog).order_by(VisitLog.created_at.desc()))
        visits = result.scalars().all()
        visits_data = [
            {
                "ip": v.ip,
                "path": v.path,
                "user_agent": v.user_agent,
                "time": v.created_at.strftime("%Y-%m-%d %H:%M:%S") if v.created_at else ""
            }
            for v in visits
        ]

        with open(backup_dir / "visit_log.json", "w", encoding="utf-8") as f:
            json.dump(visits_data, f, ensure_ascii=False, indent=2)

        # Backup update logs
        result = await db.execute(select(UpdateLog).order_by(UpdateLog.created_at.desc()))
        updates = result.scalars().all()
        updates_data = [
            {
                "action": u.action,
                "target_type": u.target_type,
                "target_name": u.target_name,
                "details": u.details,
                "username": u.username,
                "time": u.created_at.strftime("%Y-%m-%d %H:%M:%S") if u.created_at else ""
            }
            for u in updates
        ]

        with open(backup_dir / "update_log.json", "w", encoding="utf-8") as f:
            json.dump(updates_data, f, ensure_ascii=False, indent=2)

    print(f"Backup completed: {backup_dir}")
    return backup_dir

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Database backup utility")
    parser.add_argument("--output", "-o", help="Output directory for backup")
    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else None
    await backup_to_json(output_dir)

if __name__ == "__main__":
    asyncio.run(main())
