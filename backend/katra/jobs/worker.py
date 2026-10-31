"""Worker entrypoint: python -m katra.jobs.worker"""

import logging
import signal
import time

from katra.db.session import get_sessionmaker
from katra.jobs.queue import run_one

log = logging.getLogger("katra.worker")
_running = True


def _stop(*_: object) -> None:
    global _running
    _running = False


def main(poll_seconds: float = 1.0) -> None:
    logging.basicConfig(level=logging.INFO)
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    log.info("Worker started")
    while _running:
        with get_sessionmaker()() as db:
            did_work = run_one(db)
        if not did_work:
            time.sleep(poll_seconds)
    log.info("Worker stopped")


if __name__ == "__main__":
    main()
