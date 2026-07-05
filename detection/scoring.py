"""Confidence scoring — combine the two signals into one calibrated verdict.

Implements planning.md §2 exactly:

    p_ai       = WEIGHT_LLM*llm + WEIGHT_STY*sty
    agreement  = 1 - |llm - sty|
    base_conf  = |p_ai - 0.5| * 2
    confidence = base_conf * (0.5 + 0.5*agreement)
    direction  = "AI" if p_ai >= 0.5 else "human"

Verdict (asymmetric — false-positive protection), evaluated in order:
    1. word_count < MIN_WORDS            -> uncertain, confidence capped
    2. AI  & conf>=0.75 & agreement>=0.5 -> likely-ai
    3. human & conf>=0.60                -> likely-human
    4. otherwise                         -> uncertain
"""

from config import (
    WEIGHT_LLM,
    WEIGHT_STY,
    MIN_WORDS,
    SHORT_TEXT_CONF_CAP,
    AI_CONF_THRESHOLD,
    AI_AGREEMENT_THRESHOLD,
    HUMAN_CONF_THRESHOLD,
    ATTR_AI,
    ATTR_HUMAN,
    ATTR_UNCERTAIN,
)


def score(llm_score: float, sty_score: float, word_count: int) -> dict:
    """Combine both signals into a single calibrated verdict.

    Args:
        llm_score:  signal 1 AI-likelihood in [0,1]
        sty_score:  signal 2 AI-likelihood in [0,1]
        word_count: number of words in the submission (for the length gate)

    Returns:
        {
          "attribution": "likely-ai" | "likely-human" | "uncertain",
          "confidence":  float in [0,1],
          "p_ai":        float in [0,1],
          "agreement":   float in [0,1],
          "direction":   "AI" | "human",
          "too_short":   bool,
        }
    """
    p_ai = WEIGHT_LLM * llm_score + WEIGHT_STY * sty_score
    agreement = 1 - abs(llm_score - sty_score)
    base_conf = abs(p_ai - 0.5) * 2
    confidence = base_conf * (0.5 + 0.5 * agreement)
    direction = "AI" if p_ai >= 0.5 else "human"

    # 1. Too short to judge reliably -> uncertain, confidence capped.
    if word_count < MIN_WORDS:
        return {
            "attribution": ATTR_UNCERTAIN,
            "confidence": round(min(confidence, SHORT_TEXT_CONF_CAP), 4),
            "p_ai": round(p_ai, 4),
            "agreement": round(agreement, 4),
            "direction": direction,
            "too_short": True,
        }

    # 2/3/4. Asymmetric verdict.
    if direction == "AI" and confidence >= AI_CONF_THRESHOLD and agreement >= AI_AGREEMENT_THRESHOLD:
        attribution = ATTR_AI
    elif direction == "human" and confidence >= HUMAN_CONF_THRESHOLD:
        attribution = ATTR_HUMAN
    else:
        attribution = ATTR_UNCERTAIN

    return {
        "attribution": attribution,
        "confidence": round(confidence, 4),
        "p_ai": round(p_ai, 4),
        "agreement": round(agreement, 4),
        "direction": direction,
        "too_short": False,
    }
