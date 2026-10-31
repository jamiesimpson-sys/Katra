import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from katra.jobs import queue
from katra.models import AuditLog, Job, JobStatus
from katra.services import audit


def test_audit_log_is_append_only(db):
    audit.record(db, "test.event", user_id=None)
    db.commit()
    for stmt in (
        "UPDATE audit_log SET action = 'x'",
        "DELETE FROM audit_log",
        "TRUNCATE audit_log",
    ):
        with pytest.raises(DBAPIError, match="append-only"):
            db.execute(text(stmt))
        db.rollback()
    assert db.scalar(select(AuditLog.action)) == "test.event"


def test_job_runs_and_completes(db):
    seen = []
    queue.handler("test.ok")(lambda _db, payload: seen.append(payload["n"]))
    queue.enqueue(db, "test.ok", {"n": 1})
    db.commit()

    assert queue.run_one(db) is True
    assert seen == [1]
    assert db.scalar(select(Job.status)) == JobStatus.DONE
    assert queue.run_one(db) is False


def test_failing_job_is_retried_then_marked_failed(db):
    def boom(_db, _payload):
        raise RuntimeError("nope")

    queue.handler("test.boom")(boom)
    job = queue.enqueue(db, "test.boom", {})
    job.max_attempts = 2
    db.commit()

    queue.run_one(db)
    db.refresh(job)
    assert job.status == JobStatus.QUEUED and job.attempts == 1 and "nope" in job.error

    # Make the retry due now.
    job.run_after = job.created_at
    db.commit()
    queue.run_one(db)
    db.refresh(job)
    assert job.status == JobStatus.FAILED and job.attempts == 2
