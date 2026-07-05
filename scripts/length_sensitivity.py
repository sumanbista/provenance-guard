"""Empirically probe how stylometry behaves as text length shrinks.

Truncates each sample to a series of word counts and prints sty_score + the raw
metrics, so we can see (a) at what length the score stabilizes and (b) which
metrics are actually moving. Helps justify the MIN_WORDS gate and the tuning.

Usage:
    python scripts/length_sensitivity.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from detection.stylometry import stylometry, _words
from scripts.test_llm_signal import SAMPLES

LENGTHS = [20, 30, 40, 60, 80, 100, 120]


def truncate(text: str, n_words: int) -> str:
    # crude re-join is fine for a length probe (punctuation lost, but metrics
    # like burstiness/ttr are what we're watching)
    return " ".join(text.split()[:n_words])


def main():
    for label, text in SAMPLES:
        total = len(_words(text))
        print("=" * 78)
        print(f"SAMPLE: {label}  (full length: {total} words)")
        print(f"{'words':>6}{'sty':>7}{'burst':>8}{'punct':>8}{'ttr':>7}{'cv':>7}{'TTR':>7}")
        for n in LENGTHS:
            if n > total:
                break
            r = stylometry(truncate(text, n))
            m = r["metrics"]
            s = m["subscores"]
            print(f"{n:>6}{r['sty_score']:>7.2f}{s['burstiness']:>8.2f}"
                  f"{s['punctuation']:>8.2f}{s['ttr']:>7.2f}"
                  f"{m['sentence_len_cv']:>7.2f}{m['ttr']:>7.2f}")
    print("=" * 78)


if __name__ == "__main__":
    main()
