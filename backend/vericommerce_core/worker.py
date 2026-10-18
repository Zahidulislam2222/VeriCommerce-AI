"""Bounded durable worker; signal-aware and restart-safe."""

from __future__ import annotations

import os
import signal
import time
from types import FrameType

from .database import check_runtime_role, transaction
from .jobs import process_one
from .settings import get_settings


def run() -> None:
    settings = get_settings()
    running = True

    def stop(_: int, __: FrameType | None) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    with transaction(settings) as db:
        check_runtime_role(db)
    heartbeat = settings.worker_heartbeat_path
    heartbeat.parent.mkdir(parents=True, exist_ok=True)
    while running:
        try:
            worked = process_one(settings)
            with transaction(settings) as db:
                db.execute("DELETE FROM demo_sessions WHERE mode='demo' AND expires_at<=now()")
            descriptor = os.open(heartbeat, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
            with os.fdopen(descriptor, "w") as stream:
                stream.write(str(time.time()))
            if not worked:
                time.sleep(settings.worker_poll_seconds)
        except Exception as exc:
            print("Worker retry after infrastructure error:", type(exc).__name__, flush=True)
            time.sleep(settings.worker_retry_seconds)


if __name__ == "__main__":
    run()
