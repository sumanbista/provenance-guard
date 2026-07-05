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
                sty_score   REAL,
                status      TEXT,
                appeal_reasoning TEXT
            )
            """
        )
        # submissions: current mutable state + the original decision, keyed by content_id.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                content_id  TEXT PRIMARY KEY,
                creator_id  TEXT,
                timestamp   TEXT NOT NULL,
                attribution TEXT,
                confidence  REAL,
                llm_score   REAL,
                sty_score   REAL,
                status      TEXT NOT NULL
            )
            """
        )
        # appeals: one structured record per appeal (the appeal queue).
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS appeals (
                appeal_id        TEXT PRIMARY KEY,
                content_id       TEXT NOT NULL,
                creator_reasoning TEXT NOT NULL,
                timestamp        TEXT NOT NULL
            )
            """
        )
        # Migrate older databases created before these columns existed.
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(audit_log)").fetchall()]
        if "sty_score" not in cols:
            conn.execute("ALTER TABLE audit_log ADD COLUMN sty_score REAL")
        if "appeal_reasoning" not in cols:
            conn.execute("ALTER TABLE audit_log ADD COLUMN appeal_reasoning TEXT")


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
    sty_score: float,
    status: str,
) -> dict:
    """Append one submission decision to the audit log. Returns the row written.

    Captures BOTH signals' individual scores (llm_score, sty_score) alongside the
    combined confidence, so a reviewer can see exactly why a verdict was reached.
    """
    entry = {
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": _utc_now_iso(),
        "event": "submission",
        "attribution": attribution,
        "confidence": confidence,
        "llm_score": llm_score,
        "sty_score": sty_score,
        "status": status,
        "appeal_reasoning": None,
    }
    _insert_audit(entry)
    return entry


def _insert_audit(entry: dict) -> None:
    """Insert one row into audit_log. `entry` must contain all logged columns."""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO audit_log
                (content_id, creator_id, timestamp, event, attribution,
                 confidence, llm_score, sty_score, status, appeal_reasoning)
            VALUES (:content_id, :creator_id, :timestamp, :event, :attribution,
                    :confidence, :llm_score, :sty_score, :status, :appeal_reasoning)
            """,
            entry,
        )


def insert_submission(
    *,
    content_id: str,
    creator_id: str | None,
    attribution: str,
    confidence: float,
    llm_score: float,
    sty_score: float,
    status: str,
) -> None:
    """Store the current state + original decision for a submission."""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO submissions
                (content_id, creator_id, timestamp, attribution, confidence,
                 llm_score, sty_score, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (content_id, creator_id, _utc_now_iso(), attribution, confidence,
             llm_score, sty_score, status),
        )


def get_submission(content_id: str) -> dict | None:
    """Return the submission row for a content_id, or None if it doesn't exist."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM submissions WHERE content_id = ?", (content_id,)
        ).fetchone()
    return dict(row) if row else None


def update_submission_status(content_id: str, status: str) -> None:
    """Update the mutable status of a submission (e.g. -> 'under_review')."""
    with _connect() as conn:
        conn.execute(
            "UPDATE submissions SET status = ? WHERE content_id = ?",
            (status, content_id),
        )


def record_appeal(
    *,
    appeal_id: str,
    content_id: str,
    creator_reasoning: str,
    original: dict,
) -> dict:
    """Record an appeal: insert the appeal row, flip the submission status to
    'under_review', and log an appeal event in the audit log ALONGSIDE the
    original decision (attribution/confidence/scores copied from `original`).

    Returns the audit-log entry written.
    """
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO appeals (appeal_id, content_id, creator_reasoning, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (appeal_id, content_id, creator_reasoning, _utc_now_iso()),
        )
    update_submission_status(content_id, "under_review")

    entry = {
        "content_id": content_id,
        "creator_id": original.get("creator_id"),
        "timestamp": _utc_now_iso(),
        "event": "appeal",
        "attribution": original.get("attribution"),
        "confidence": original.get("confidence"),
        "llm_score": original.get("llm_score"),
        "sty_score": original.get("sty_score"),
        "status": "under_review",
        "appeal_reasoning": creator_reasoning,
    }
    _insert_audit(entry)
    return entry


def recent_entries(limit: int = 20) -> list[dict]:
    """Return the most recent audit-log entries (newest first). For GET /log."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
