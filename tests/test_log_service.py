"""Log service tests."""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.models import UpdateLog, VisitLog
from app.services.log import LogService, run_log_cleanup_job


@pytest.mark.asyncio
async def test_record_visit_only_inserts_single_row(test_db):
    """Recording a visit should only stage a single insert on the hot path."""
    service = LogService(test_db)

    await service.record_visit("127.0.0.1", "/", "pytest")
    await test_db.commit()

    result = await test_db.execute(select(VisitLog))
    visits = result.scalars().all()
    assert len(visits) == 1
    assert visits[0].ip == "127.0.0.1"
    assert visits[0].path == "/"


@pytest.mark.asyncio
async def test_cleanup_old_visits_keeps_newest_rows(test_db):
    """Visit retention should remove the oldest rows first."""
    now = datetime.utcnow()
    test_db.add_all(
        [
            VisitLog(ip="1", path="/old-1", created_at=now - timedelta(minutes=3)),
            VisitLog(ip="2", path="/old-2", created_at=now - timedelta(minutes=2)),
            VisitLog(ip="3", path="/new-1", created_at=now - timedelta(minutes=1)),
            VisitLog(ip="4", path="/new-2", created_at=now),
        ]
    )
    await test_db.commit()

    deleted = await LogService(test_db).cleanup_old_visits(max_records=2)
    await test_db.commit()

    assert deleted == 2
    result = await test_db.execute(select(VisitLog).order_by(VisitLog.created_at.asc()))
    remaining = result.scalars().all()
    assert [visit.path for visit in remaining] == ["/new-1", "/new-2"]


@pytest.mark.asyncio
async def test_cleanup_old_updates_keeps_newest_rows(test_db):
    """Update retention should remove the oldest rows first."""
    now = datetime.utcnow()
    test_db.add_all(
        [
            UpdateLog(action="add", target_type="link", target_name="old-1", created_at=now - timedelta(minutes=3)),
            UpdateLog(action="add", target_type="link", target_name="old-2", created_at=now - timedelta(minutes=2)),
            UpdateLog(action="add", target_type="link", target_name="new-1", created_at=now - timedelta(minutes=1)),
            UpdateLog(action="add", target_type="link", target_name="new-2", created_at=now),
        ]
    )
    await test_db.commit()

    deleted = await LogService(test_db).cleanup_old_updates(max_records=2)
    await test_db.commit()

    assert deleted == 2
    result = await test_db.execute(select(UpdateLog).order_by(UpdateLog.created_at.asc()))
    remaining = result.scalars().all()
    assert [update.target_name for update in remaining] == ["new-1", "new-2"]


@pytest.mark.asyncio
async def test_run_log_cleanup_job_reports_deleted_and_remaining_counts(test_db):
    """Cleanup job should return both deleted and remaining totals."""
    now = datetime.utcnow()
    test_db.add_all(
        [
            VisitLog(ip="1", path="/old", created_at=now - timedelta(minutes=2)),
            VisitLog(ip="2", path="/new", created_at=now),
            UpdateLog(action="add", target_type="link", target_name="old", created_at=now - timedelta(minutes=2)),
            UpdateLog(action="add", target_type="link", target_name="new", created_at=now),
        ]
    )
    await test_db.commit()

    @asynccontextmanager
    async def session_factory():
        yield test_db

    summary = await run_log_cleanup_job(session_factory, max_visits=1, max_updates=1)

    assert summary == {
        "deleted_visits": 1,
        "deleted_updates": 1,
        "remaining_visits": 1,
        "remaining_updates": 1,
    }
