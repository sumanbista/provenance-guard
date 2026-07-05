"""Standalone test harness for the LLM signal (Milestone 3).

Run this to call classify_llm() directly on a few known samples and eyeball the
scores BEFORE the signal is wired into the /submit endpoint.

Usage (from the project root, venv active):
    python scripts/test_llm_signal.py
"""

import sys
from pathlib import Path

# Allow running as a script from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from detection.llm_signal import classify_llm

SAMPLES = [
    (
        "Clearly human-written (should score low)",
        "ok so i finally tried that new ramen place downtown and honestly?underwhelming. the broth was fine but they put WAY too much sodium in it and i was thirsty for like three hours after. my friend got the spicy version and said it was better. probably won't go back unless someone drags me there"
    ),
    (
        "Clearly AI-generated (should score high)",
        "Artificial intelligence represents a transformative paradigm shift in modern society. It is important to note that while the benefits of AI are numerous, it is equally essential to consider the ethical implications. Furthermore, stakeholders across various sectors must collaborate to ensure responsible deployment."
    ),
    (
        "Borderline: lightly edited AI output (should ideally score mid-range)",
        "I've been thinking a lot about remote work lately. There are genuine tradeoffs — flexibility and no commute on one side, isolation and blurred work-life boundaries on the other. Studies show productivity varies widely by individual and role type."
    ),
]


def main():
    for label, text in SAMPLES:
        print("=" * 70)
        print(f"SAMPLE: {label}")
        print(f"TEXT:   {text[:80]}{'...' if len(text) > 80 else ''}")
        result = classify_llm(text)
        print(f"  llm_score : {result['llm_score']}  (0=human, 1=AI)")
        print(f"  reason    : {result['reason']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
