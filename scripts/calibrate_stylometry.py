"""Measure real stylometry metric ranges on the labeled calibration set.

No network. Runs every sample through the raw metrics, groups by HUMAN vs AI
(inferred from each sample's label), and prints per-sample values plus the
min/mean/max per group — so we can set each metric's normalization band and
weights to fit reality instead of guessing.

Usage:
    python scripts/calibrate_stylometry.py
"""

import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from detection.stylometry import stylometry, _words
from scripts.test_llm_signal import SAMPLES


def group_of(label: str) -> str:
    low = label.lower()
    if "human" in low:
        return "HUMAN"
    if "ai" in low or "borderline" in low:
        return "AI"
    return "?"


def main():
    rows = []
    print(f"{'group':<6}{'words':>6}{'cv':>7}{'msl':>7}{'punct':>7}{'ttr':>7}{'sty':>7}  label")
    print("-" * 92)
    for label, text in SAMPLES:
        g = group_of(label)
        r = stylometry(text)
        m = r["metrics"]
        wc = len(_words(text))
        rows.append((g, wc, m["sentence_len_cv"], m["distinct_punctuation"], m["ttr"], r["sty_score"], m["mean_sentence_len"]))
        short = (label[:40] + "…") if len(label) > 40 else label
        print(f"{g:<6}{wc:>6}{m['sentence_len_cv']:>7.2f}{m['mean_sentence_len']:>7.1f}"
              f"{m['distinct_punctuation']:>7}{m['ttr']:>7.2f}{r['sty_score']:>7.2f}  {short}")

    print("-" * 88)
    for g in ("HUMAN", "AI"):
        sel = [r for r in rows if r[0] == g]
        if not sel:
            continue
        def stat(i):
            vals = [r[i] for r in sel]
            return f"{min(vals):.2f} / {statistics.mean(vals):.2f} / {max(vals):.2f}"
        print(f"{g} (n={len(sel)})  min/mean/max")
        print(f"   words : {stat(1)}")
        print(f"   cv    : {stat(2)}   (burstiness; HIGH=human, LOW=AI)")
        print(f"   msl   : {stat(6)}   (mean sentence length; LONG=AI?)")
        print(f"   punct : {stat(3)}   (distinct marks)")
        print(f"   ttr   : {stat(4)}   (lexical diversity)")
        print(f"   sty   : {stat(5)}   (current combined score)")


if __name__ == "__main__":
    main()
