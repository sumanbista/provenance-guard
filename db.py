"""SQLite storage for Provenance Guard.

Milestone 3: a single append-only `audit_log` table. Every attribution decision
writes one structured row (timestamp, content_id, attribution, signal-1 score,
etc.). The log is extended with the second signal in Milestone 4 and with appeal
events in Milestone 5.

We chose SQLite-only storage (see planning.md): mutable state and the audit log
live in one database, and GET /log reads the audit_log table directly.
"""

import sqlite3
from datetime import datetime, timezone

from config import DB_PATH


def _connect() -> sqlite3.Connection:
    """Open a fresh connection with dict-like row access.

    A connection-per-operation keeps things thread-safe under Flask's dev
    server without extra locking.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist. Safe to call on every startup."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id  TEXT    NOT NULL,
                creator_id  TEXT,
                timestamp   TEXT    NOT NULL,
                event       TEXT    NOT NULL DEFAULT 'submission',
                attribution TEXT,
                confidence  REAL,
                llm_score   REAL,
                status      TEXT
            )
            """
        )


def _utc_now_iso() -> str:
    """Current UTC time as an ISO-8601 string with a trailing Z."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def log_submission(
    *,
    content_id: str,
    creator_id: str | None,
    attribution: str,
    confidence: float,
    llm_score: float,
    status: str,
) -> dict:
    """Append one submission decision to the audit log. Returns the row written."""
    entry = {
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": _utc_now_iso(),
        "event": "submission",
        "attribution": attribution,
        "confidence": confidence,
        "llm_score": llm_score,
        "status": status,
    }
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO audit_log
                (content_id, creator_id, timestamp, event, attribution,
                 confidence, llm_score, status)
            VALUES (:content_id, :creator_id, :timestamp, :event, :attribution,
                    :confidence, :llm_score, :status)
            """,
            entry,
        )
    return entry


def recent_entries(limit: int = 20) -> list[dict]:
    """Return the most recent audit-log entries (newest first). For GET /log."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
