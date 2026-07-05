"""Side-by-side comparison of both signals (Milestone 4).

Runs signal 1 (LLM, network) and signal 2 (stylometry, local) on the same samples
and reports where they agree and disagree. Divergence is informative: it shows
each signal's blind spots and is exactly what should drive the score toward
"uncertain" (see planning.md §2).

Usage (from the project root, venv active, GROQ_API_KEY set):
    python scripts/compare_signals.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from detection.llm_signal import classify_llm
from detection.stylometry import stylometry
from scripts.test_llm_signal import SAMPLES


def main():
    print(f"{'SAMPLE':<48}{'llm':>7}{'sty':>7}{'|diff|':>8}  verdict")
    print("-" * 80)
    for label, text in SAMPLES:
        llm = classify_llm(text)["llm_score"]
        sty = stylometry(text)["sty_score"]
        diff = abs(llm - sty)
        agree = "AGREE" if diff <= 0.25 else "DISAGREE"
        short = (label[:45] + "...") if len(label) > 45 else label
        print(f"{short:<48}{llm:>7.2f}{sty:>7.2f}{diff:>8.2f}  {agree}")
    print("-" * 80)
    print("agreement = 1 - |llm - sty|;  large |diff| => signals disagree => push toward Uncertain")


if __name__ == "__main__":
    main()
