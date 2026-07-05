"""Signal 2 — Stylometric heuristics (structural), pure Python.

Measures the statistical *shape* of a text rather than its meaning, and returns a
single AI-likelihood in [0, 1]. This is the structural counterpart to the LLM
signal (see planning.md §1). Guiding intuition: **more uniform / less varied
writing reads as more AI-like**; human writing tends to be bursty and varied.

The score combines two metrics (weights in config), each normalized to [0, 1]:
  1. Sentence-length burstiness (coefficient of variation)  -- primary
  2. Punctuation variety (distinct marks used)              -- light secondary

Type-token ratio (lexical diversity) is still computed and reported for
transparency, but was DROPPED from the score during Milestone 4 tuning: on the
labeled calibration set its direction was reversed (AI text had *higher*
diversity than long human essays), so including it produced false positives.

Calibration constants live in config.py and were tuned against a labeled set.
"""

import re
import statistics

from config import (
    STY_BURST_AI,
    STY_BURST_HUMAN,
    STY_PUNCT_HUMAN,
    STY_W_BURST,
    STY_W_PUNCT,
)

# Punctuation marks whose *variety* signals human expressiveness.
_PUNCT_MARKS = {",", ";", ":", "—", "(", ")", '"', "'", "!", "?", "…"}

# TTR is length-sensitive, so we compute it over a fixed leading window of words.
_TTR_WINDOW = 200


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _sentences(text: str) -> list[str]:
    """Split into sentences on ., !, ?, and newlines (newlines help poems/lists)."""
    parts = re.split(r"[.!?\n]+", text)
    return [p.strip() for p in parts if p.strip()]


def _words(text: str) -> list[str]:
    """Word tokens (letters and apostrophes), lowercased."""
    return [w.lower() for w in re.findall(r"[A-Za-z']+", text)]


def stylometry(text: str) -> dict:
    """Score `text` with the stylometry signal.

    Returns:
        {
          "sty_score": float in [0,1],   # probability the text is AI-generated
          "metrics": { ...raw metric values and per-metric subscores... }
        }
    """
    words = _words(text)
    word_count = len(words)
    sentences = _sentences(text)
    sentence_lengths = [len(_words(s)) for s in sentences]
    sentence_lengths = [n for n in sentence_lengths if n > 0]

    # --- Metric 1 (primary): sentence-length burstiness (coeff. of variation) ---
    if len(sentence_lengths) >= 2:
        mean_len = statistics.mean(sentence_lengths)
        std_len = statistics.pstdev(sentence_lengths)
        cv = (std_len / mean_len) if mean_len > 0 else 0.0
    else:
        # Too few sentences to have variation; treat as uniform (AI-leaning).
        mean_len = float(sentence_lengths[0]) if sentence_lengths else 0.0
        cv = 0.0
    burst_sub = _clamp((STY_BURST_HUMAN - cv) / (STY_BURST_HUMAN - STY_BURST_AI))

    # --- Metric 2 (secondary): punctuation variety (distinct marks present) ---
    distinct_punct = sum(1 for mark in _PUNCT_MARKS if mark in text)
    punct_sub = _clamp((STY_PUNCT_HUMAN - distinct_punct) / STY_PUNCT_HUMAN)

    # --- Reported for transparency only; NOT part of the score (see module doc) ---
    window = words[:_TTR_WINDOW]
    ttr = (len(set(window)) / len(window)) if window else 0.0

    sty_score = round(STY_W_BURST * burst_sub + STY_W_PUNCT * punct_sub, 4)

    return {
        "sty_score": sty_score,
        "metrics": {
            "word_count": word_count,
            "sentence_count": len(sentence_lengths),
            "mean_sentence_len": round(mean_len, 2),
            "sentence_len_cv": round(cv, 4),
            "distinct_punctuation": distinct_punct,
            "ttr": round(ttr, 4),  # reported, not scored
            "subscores": {
                "burstiness": round(burst_sub, 4),
                "punctuation": round(punct_sub, 4),
            },
        },
    }
