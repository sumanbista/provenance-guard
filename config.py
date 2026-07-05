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

# --- Storage ---
# SQLite database file (holds the audit_log table; submissions/appeals added later).
DB_PATH = os.getenv("DB_PATH", "provenance.db")

# --- Detection tunables (see planning.md §1–§2) ---
# When an LLM call fails or its output can't be parsed, we fail CLOSED to this
# neutral score rather than guessing — a parse error must never push a
# submission toward an AI accusation.
LLM_FAILSAFE_SCORE = 0.5
