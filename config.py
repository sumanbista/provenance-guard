"""Central configuration for Provenance Guard.

Secrets and tunables live here so the detection/logic modules never read the
environment directly. Values come from the .env file (loaded via python-dotenv).
"""

import os

from dotenv import load_dotenv

load_dotenv()

# --- Groq / LLM signal ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

# --- Server ---
# Defaults to port 5000. On macOS, free it first by turning OFF "AirPlay Receiver"
# (System Settings > General > AirDrop & Handoff). If you can't, run with PORT=5001.
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "5000"))
DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"

# --- Storage ---
# SQLite database file (holds the audit_log table; submissions/appeals added later).
DB_PATH = os.getenv("DB_PATH", "provenance.db")

# --- Rate limiting (Flask-Limiter) ---
# In-memory storage is fine for local/dev; a real deployment would use Redis.
RATE_LIMIT_STORAGE_URI = "memory://"
# Applied to POST /submit. See the README "Rate Limiting" section for the reasoning.
# Tuned to a real writer's cadence (submissions are naturally minutes apart), with
# layered burst/session/total caps that also bound Groq LLM cost (1 call per submit):
#   5/min  : burst  — a writer resubmitting after edits stays under; a flood script trips it.
#   30/hour: session — a heavy-but-legit drafting session fits; blocks paced abuse.
#   100/day: total  — bounds daily LLM cost; no writer analyzes 100 distinct pieces a day.
RATE_LIMIT_SUBMIT = "5 per minute; 30 per hour; 100 per day"

# --- Detection tunables (see planning.md §1–§2) ---
# When an LLM call fails or its output can't be parsed, we fail CLOSED to this
# neutral score rather than guessing — a parse error must never push a
# submission toward an AI accusation.
LLM_FAILSAFE_SCORE = 0.5

# --- Confidence scoring (planning.md §2). All initial values; tuned in M4. ---
WEIGHT_LLM = 0.6            # blend weight for signal 1 (more reliable)
WEIGHT_STY = 0.4            # blend weight for signal 2
MIN_WORDS = 60             # below this, text is too short to judge reliably
SHORT_TEXT_CONF_CAP = 0.30  # confidence ceiling for too-short text

# --- Stylometry metric calibration (tuned in M4 against a labeled sample set) ---
# Burstiness = coefficient of variation of sentence lengths. Humans are bursty
# (high CV); AI is uniform (low CV). Observed: AI ~0.13-0.38, human ~0.32-0.62.
STY_BURST_AI = 0.25    # CV at/below this -> fully AI-leaning subscore (1.0)
STY_BURST_HUMAN = 0.50  # CV at/above this -> fully human-leaning subscore (0.0)
# Punctuation variety: distinct marks used. Humans use more; AI is plainer.
STY_PUNCT_HUMAN = 3     # this many distinct marks (or more) -> fully human (0.0)
# Metric weights within the stylometry signal. Burstiness is the reliable
# discriminator; punctuation is a light secondary. TTR was DROPPED — on the
# calibration set its direction was reversed (AI had HIGHER diversity than
# humans), so it caused false positives on long human essays.
STY_W_BURST = 0.75
STY_W_PUNCT = 0.25

# Asymmetric verdict thresholds — it takes STRONGER evidence to say "AI"
# than to say "human" (the false-positive protection).
AI_CONF_THRESHOLD = 0.75        # "Likely AI" requires confidence >= this ...
AI_AGREEMENT_THRESHOLD = 0.5    # ... AND signal agreement >= this
HUMAN_CONF_THRESHOLD = 0.60     # "Likely human" only needs confidence >= this

# Attribution labels (internal verdict codes)
ATTR_AI = "likely-ai"
ATTR_HUMAN = "likely-human"
ATTR_UNCERTAIN = "uncertain"
