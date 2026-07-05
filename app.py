"""Provenance Guard — Flask API.

Milestone 3: POST /submit runs the first detection signal (LLM-as-judge) and
returns a structured response with a unique content_id, the signal-1
attribution, and PLACEHOLDER confidence + label (real confidence scoring and
labels arrive in Milestones 4–5).
"""

import uuid

from flask import Flask, request, jsonify

from detection.llm_signal import classify_llm
from detection.stylometry import stylometry
from detection.scoring import score
from db import init_db, log_submission, recent_entries

app = Flask(__name__)

# Create the audit_log table on startup (no-op if it already exists).
init_db()


@app.get("/health")
def health():
    """Liveness check."""
    return jsonify({"status": "ok"})


@app.get("/log")
def get_log():
    """Return the most recent audit-log entries as JSON.

    For documentation and grading visibility only. In a real system this would
    require authentication — the audit log can contain sensitive decisions.
    """
    return jsonify({"entries": recent_entries()})


@app.post("/submit")
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
    status = "classified"

    # --- Audit log: one structured row, capturing BOTH signal scores ---
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
        "label": "Placeholder label — transparency labels arrive in Milestone 5.",
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
    # Port 5001 (not 5000): macOS AirPlay Receiver squats on port 5000.
    app.run(debug=True, port=5001)
