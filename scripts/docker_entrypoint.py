"""Container entrypoint: wait for DB, migrate, then serve health API."""

from __future__ import annotations

import os
import subprocess
import sys
import time

from sqlalchemy import create_engine, text


def wait_for_db(url: str, *, timeout_s: float = 60.0) -> None:
    engine = create_engine(url, pool_pre_ping=True)
    deadline = time.time() + timeout_s
    while True:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception as exc:
            if time.time() > deadline:
                print(f"database not ready: {type(exc).__name__}", file=sys.stderr)
                raise SystemExit(1) from exc
            time.sleep(1)


def main() -> None:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("DATABASE_URL missing", file=sys.stderr)
        raise SystemExit(1)
    print("A-04 backend: waiting for database...", flush=True)
    wait_for_db(url)
    print("database reachable; running alembic upgrade head", flush=True)
    subprocess.check_call([sys.executable, "-m", "alembic", "upgrade", "head"])
    os.execvp(
        sys.executable,
        [
            sys.executable,
            "-m",
            "uvicorn",
            "weaksignalradar.api.app:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ],
    )


if __name__ == "__main__":
    main()
