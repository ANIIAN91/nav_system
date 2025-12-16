#!/usr/bin/env python3
"""
Data migration script: JSON to PostgreSQL
Migrates existing data from JSON files to PostgreSQL database.
"""
import asyncio
import json
import sys
import uuid
import os
from pathlib import Path
from urllib.parse import quote_plus

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine
from app.database import async_session, init_db
from app.models import Category, Link, Setting, VisitLog, UpdateLog
from app.config import get_settings

settings = get_settings()

async def ensure_database_exists():
    """Check if database exists, create if not"""
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "password")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "postgres")

    # If using default postgres database, skip creation
    if db_name == "postgres":
        print(f"Using default database: postgres")
        return True

    # Connect to default postgres database to check/create target database
    encoded_password = quote_plus(db_password)
    admin_url = f"postgresql+asyncpg://{db_user}:{encoded_password}@{db_host}:{db_port}/postgres"

    try:
        engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
        async with engine.connect() as conn:
            # Check if database exists
            result = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                {"dbname": db_name}
            )
            exists = result.scalar() is not None

            if not exists:
                print(f"Database '{db_name}' does not exist, creating...")
                await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                print(f"Database '{db_name}' created successfully!")
            else:
                print(f"Database '{db_name}' already exists")

        await engine.dispose()
        return True
    except Exception as e:
        print(f"Error checking/creating database: {e}")
        return False

async def migrate_links():
    """Migrate links.json to database"""
    links_file = settings.data_dir / "links.json"
    if not links_file.exists():
        print("links.json not found, skipping...")
        return

    with open(links_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    async with async_session() as db:
        for sort_order, cat_data in enumerate(data.get("categories", [])):
            # Check if category exists
            result = await db.execute(select(Category).where(Category.name == cat_data["name"]))
            category = result.scalar_one_or_none()

            if not category:
                category = Category(
                    name=cat_data["name"],
                    auth_required=cat_data.get("auth_required", False),
                    sort_order=sort_order
                )
                db.add(category)
                await db.flush()
                print(f"Created category: {cat_data['name']}")

            # Add links
            for link_order, link_data in enumerate(cat_data.get("links", [])):
                link_id = link_data.get("id")
                if link_id:
                    try:
                        link_uuid = uuid.UUID(link_id)
                    except:
                        link_uuid = uuid.uuid4()
                else:
                    link_uuid = uuid.uuid4()

                link = Link(
                    id=link_uuid,
                    category_id=category.id,
                    title=link_data.get("title", ""),
                    url=link_data.get("url", ""),
                    icon=link_data.get("icon"),
                    sort_order=link_order
                )
                db.add(link)
                print(f"  Added link: {link_data.get('title')}")

        await db.commit()
    print("Links migration completed!")

async def migrate_settings():
    """Migrate settings.json to database"""
    settings_file = settings.data_dir / "settings.json"
    if not settings_file.exists():
        print("settings.json not found, skipping...")
        return

    with open(settings_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    async with async_session() as db:
        for key, value in data.items():
            if isinstance(value, list):
                value = json.dumps(value)
            elif value is None:
                value = ""
            else:
                value = str(value)

            result = await db.execute(select(Setting).where(Setting.key == key))
            setting = result.scalar_one_or_none()

            if setting:
                setting.value = value
            else:
                db.add(Setting(key=key, value=value))
            print(f"Set setting: {key}")

        await db.commit()
    print("Settings migration completed!")

async def migrate_visit_logs():
    """Migrate visit_log.json to database"""
    log_file = settings.data_dir / "visit_log.json"
    if not log_file.exists():
        print("visit_log.json not found, skipping...")
        return

    with open(log_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    async with async_session() as db:
        for record in data[:settings.max_visit_records]:  # Limit records
            from datetime import datetime
            created_at = None
            if record.get("time"):
                try:
                    created_at = datetime.strptime(record["time"], "%Y-%m-%d %H:%M:%S")
                except:
                    pass

            log = VisitLog(
                ip=record.get("ip"),
                path=record.get("path"),
                user_agent=record.get("user_agent"),
                created_at=created_at
            )
            db.add(log)

        await db.commit()
    print(f"Visit logs migration completed! ({len(data)} records)")

async def migrate_update_logs():
    """Migrate update_log.json to database"""
    log_file = settings.data_dir / "update_log.json"
    if not log_file.exists():
        print("update_log.json not found, skipping...")
        return

    with open(log_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    async with async_session() as db:
        for record in data[:settings.max_update_records]:  # Limit records
            from datetime import datetime
            created_at = None
            if record.get("time"):
                try:
                    created_at = datetime.strptime(record["time"], "%Y-%m-%d %H:%M:%S")
                except:
                    pass

            log = UpdateLog(
                action=record.get("action"),
                target_type=record.get("target_type"),
                target_name=record.get("target_name"),
                details=record.get("details"),
                username=record.get("username"),
                created_at=created_at
            )
            db.add(log)

        await db.commit()
    print(f"Update logs migration completed! ({len(data)} records)")

async def main():
    """Run all migrations"""
    print("=" * 50)
    print("Nav System Data Migration")
    print("JSON -> PostgreSQL")
    print("=" * 50)

    print("\nChecking database...")
    if not await ensure_database_exists():
        print("Failed to ensure database exists. Exiting.")
        return

    print("\nInitializing tables...")
    await init_db()

    print("\nMigrating links...")
    await migrate_links()

    print("\nMigrating settings...")
    await migrate_settings()

    print("\nMigrating visit logs...")
    await migrate_visit_logs()

    print("\nMigrating update logs...")
    await migrate_update_logs()

    print("\n" + "=" * 50)
    print("Migration completed successfully!")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
