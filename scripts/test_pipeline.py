"""Full end-to-end detection test on the labeled calibration set (Milestone 4).

Runs BOTH signals (LLM + stylometry) and the confidence combiner on every sample
and prints the final verdict next to the expected group. This is the definitive
check that the tuned pipeline behaves before we wire it into /submit.

Makes live Groq calls (one per sample) — run it yourself so it uses your quota.

Usage:
    python scripts/test_pipeline.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from detection.llm_signal import classify_llm
from detection.stylometry import stylometry, _words
from detection.scoring import score
from scripts.test_llm_signal import SAMPLES
from scripts.calibrate_stylometry import group_of


def main():
    print(f"{'exp':<6}{'llm':>6}{'sty':>6}{'p_ai':>7}{'agree':>7}{'conf':>7}  {'verdict':<14} label")
    print("-" * 96)
    correct = 0
    total = 0
    for label, text in SAMPLES:
        exp = group_of(label)
        wc = len(_words(text))
        llm = classify_llm(text)["llm_score"]
        sty = stylometry(text)["sty_score"]
        r = score(llm, sty, wc)
        v = r["attribution"]
        # "correct" = didn't misclassify (human->ai or ai->human); uncertain is a safe pass
        ok = not (
            (exp == "HUMAN" and v == "likely-ai") or (exp == "AI" and v == "likely-human")
        )
        correct += ok
        total += 1
        flag = "" if ok else "  <-- MISCLASSIFIED"
        short = (label[:34] + "…") if len(label) > 34 else label
        print(f"{exp:<6}{llm:>6.2f}{sty:>6.2f}{r['p_ai']:>7.3f}{r['agreement']:>7.3f}"
              f"{r['confidence']:>7.3f}  {v:<14} {short}{flag}")
    print("-" * 96)
    print(f"no dangerous misclassifications: {correct}/{total}  "
          f"(uncertain counts as safe — we never falsely accuse)")


if __name__ == "__main__":
    main()
