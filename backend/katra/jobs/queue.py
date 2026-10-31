"""A small Postgres-backed job queue (no Redis needed).

Workers claim jobs with SELECT ... FOR UPDATE SKIP LOCKED, so several can run safely.
"""

import logging
import traceback
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from katra.models import Job, JobStatus
from katra.models.base import utcnow

log = logging.getLogger("katra.jobs")

Handler = Callable[[Session, dict[str, Any]], None]
HANDLERS: dict[str, Handler] = {}


def handler(job_type: str) -> Callable[[Handler], Handler]:
    def register(fn: Handler) -> Handler:
        HANDLERS[job_type] = fn
        return fn

    return register


def enqueue(db: Session, job_type: str, payload: dict[str, Any]) -> Job:
    """Adds the job to the caller's transaction; it runs once the caller commits."""
    job = Job(type=job_type, payload=payload)
    db.add(job)
    return job


def run_one(db: Session) -> bool:
    """Claim and run a single due job. Returns False if there was nothing to do."""
    job = db.scalar(
        select(Job)
        .where(Job.status == JobStatus.QUEUED, Job.run_after <= utcnow())
        .order_by(Job.run_after)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if job is None:
        db.rollback()
        return False
    job.status = JobStatus.RUNNING
    job.attempts += 1
    db.commit()

    try:
        fn = HANDLERS.get(job.type)
        if fn is None:
            raise LookupError(f"No handler for job type {job.type!r}")
        fn(db, job.payload)
        job.status = JobStatus.DONE
        job.error = None
        db.commit()
    except Exception:
        db.rollback()
        log.exception("Job %s (%s) failed", job.id, job.type)
        job.error = traceback.format_exc()[-4000:]
        if job.attempts >= job.max_attempts:
            job.status = JobStatus.FAILED
        else:
            job.status = JobStatus.QUEUED
            job.run_after = utcnow() + timedelta(seconds=10 * 2**job.attempts)
        db.commit()
    return True
