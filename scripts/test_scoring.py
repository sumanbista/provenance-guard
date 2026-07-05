"""Verify the confidence-scoring combiner against the planning.md thresholds.

No network — feeds fixed (llm, sty, word_count) triples into score() so we can
confirm the math and the three verdict categories are all reachable, and that the
thresholds match the spec exactly.

Usage:
    python scripts/test_scoring.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from detection.scoring import score

# (label, llm_score, sty_score, word_count)
CASES = [
    ("Clearly human, signals agree  (llm .20 / sty .11)", 0.20, 0.11, 120),
    ("Tuned long AI (real numbers)  (llm .90 / sty .92)", 0.90, 0.92, 120),
    ("Strong AI, signals agree      (llm .95 / sty .90)", 0.95, 0.90, 120),
    ("Strong human, signals agree   (llm .05 / sty .10)", 0.05, 0.10, 120),
    ("Formal human (Human-3 case)   (llm .20 / sty .63)", 0.20, 0.63, 144),
    ("High LLM but sty disagrees    (llm .90 / sty .30)", 0.90, 0.30, 120),
    ("Too short (< MIN_WORDS)       (llm .95 / sty .95)", 0.95, 0.95, 30),
]


def main():
    header = f"{'CASE':<50}{'p_ai':>7}{'agree':>7}{'conf':>7}  {'verdict'}"
    print(header)
    print("-" * len(header))
    seen = set()
    for label, llm, sty, wc in CASES:
        r = score(llm, sty, wc)
        seen.add(r["attribution"])
        print(f"{label:<50}{r['p_ai']:>7.3f}{r['agreement']:>7.3f}{r['confidence']:>7.3f}  {r['attribution']}")
    print("-" * len(header))
    print(f"distinct verdict categories reached: {sorted(seen)}")


if __name__ == "__main__":
    main()
