"""Provenance Guard — Flask API.

Milestone 3: POST /submit runs the first detection signal (LLM-as-judge) and
returns a structured response with a unique content_id, the signal-1
attribution, and PLACEHOLDER confidence + label (real confidence scoring and
labels arrive in Milestones 4–5).
"""

import uuid

from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import RATE_LIMIT_STORAGE_URI, RATE_LIMIT_SUBMIT, HOST, PORT, DEBUG
from detection.llm_signal import classify_llm
from detection.stylometry import stylometry
from detection.scoring import score
from labels import label_for
from db import (
    init_db,
    log_submission,
    recent_entries,
    insert_submission,
    get_submission,
    record_appeal,
)

app = Flask(__name__)

# Create the audit_log table on startup (no-op if it already exists).
init_db()

# Rate limiter — keyed by client IP. Protects /submit from flooding/abuse.
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri=RATE_LIMIT_STORAGE_URI,
)


@app.errorhandler(429)
def ratelimit_handler(e):
    """Return a JSON body (not HTML) when a rate limit is exceeded."""
    return jsonify({
        "error": "Rate limit exceeded. Please slow down and try again later.",
        "limit": str(e.description),
    }), 429


@app.get("/health")
def health():
    """Liveness check."""
    return jsonify({"status": "ok"})


@app.post("/appeal")
def appeal():
    """Let a creator contest a classification.

    Expects a JSON body with:
      - "content_id"        (str, required) — the id returned by /submit
      - "creator_reasoning" (str, required) — why they believe it's misclassified

    Updates the submission's status to "under_review", records the appeal in the
    appeals table, and logs an appeal event ALONGSIDE the original decision in the
    audit log. No automated re-classification is performed — a human reviews it.
    """
    data = request.get_json(silent=True) or {}
    content_id = data.get("content_id")
    reasoning = data.get("creator_reasoning")

    if not content_id or not str(content_id).strip():
        return jsonify({"error": "Field 'content_id' is required."}), 400
    if not reasoning or not str(reasoning).strip():
        return jsonify({"error": "Field 'creator_reasoning' is required."}), 400

    original = get_submission(content_id)
    if original is None:
        return jsonify({"error": f"No submission found for content_id '{content_id}'."}), 404

    appeal_id = str(uuid.uuid4())
    record_appeal(
        appeal_id=appeal_id,
        content_id=content_id,
        creator_reasoning=reasoning,
        original=original,
    )

    return jsonify({
        "content_id": content_id,
        "appeal_id": appeal_id,
        "status": "under_review",
        "message": "Appeal received. Your submission is now under review by a human.",
    })


@app.get("/log")
def get_log():
    """Return the most recent audit-log entries as JSON.

    For documentation and grading visibility only. In a real system this would
    require authentication — the audit log can contain sensitive decisions.
    """
    return jsonify({"entries": recent_entries()})


@app.post("/submit")
@limiter.limit(RATE_LIMIT_SUBMIT)
def submit():
    """Accept a piece of text for attribution analysis.

    Expects a JSON body with:
      - "text"        (str, required)  — the content to analyze
      - "creator_id"  (str, optional)  — who submitted it

    Returns a structured response including a unique content_id, the signal-1
    attribution, and placeholder confidence + label.
    """
    data = request.get_json(silent=True) or {}

    # Accept "text" (Milestone 3) or "content" (planning.md contract).
    text = data.get("text") or data.get("content")
    creator_id = data.get("creator_id")

    if not text or not str(text).strip():
        return jsonify({"error": "Field 'text' is required and cannot be empty."}), 400

    content_id = str(uuid.uuid4())

    # --- Detection pipeline: two independent signals ---
    llm = classify_llm(text)              # signal 1 (semantic)
    sty = stylometry(text)                # signal 2 (structural)
    word_count = sty["metrics"]["word_count"]

    # --- Confidence scoring: combine both signals ---
    result = score(llm["llm_score"], sty["sty_score"], word_count)
    attribution = result["attribution"]
    confidence = result["confidence"]
    label = label_for(attribution, confidence)
    status = "classified"

    # --- Persist current state (for later appeals) + audit-log the decision ---
    insert_submission(
        content_id=content_id,
        creator_id=creator_id,
        attribution=attribution,
        confidence=confidence,
        llm_score=llm["llm_score"],
        sty_score=sty["sty_score"],
        status=status,
    )
    log_submission(
        content_id=content_id,
        creator_id=creator_id,
        attribution=attribution,
        confidence=confidence,
        llm_score=llm["llm_score"],
        sty_score=sty["sty_score"],
        status=status,
    )

    return jsonify({
        "content_id": content_id,
        "creator_id": creator_id,
        "attribution": attribution,
        "confidence": confidence,
        "label": label,
        "signals": {
            "llm": {
                "llm_score": llm["llm_score"],
                "reason": llm["reason"],
            },
            "stylometry": {
                "sty_score": sty["sty_score"],
                "metrics": sty["metrics"],
            },
        },
        "scoring": {
            "p_ai": result["p_ai"],
            "agreement": result["agreement"],
            "direction": result["direction"],
            "too_short": result["too_short"],
        },
        "status": status,
    })


if __name__ == "__main__":
    # Host/port/debug come from config (env-overridable). Defaults to port 5000;
    # on macOS free it first by disabling "AirPlay Receiver", or run with PORT=5001.
    app.run(debug=DEBUG, host=HOST, port=PORT)
