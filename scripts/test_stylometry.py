"""Standalone test harness for the stylometry signal (Milestone 4).

Runs stylometry() directly on the SAME samples used for signal 1, with NO network
calls, so you can inspect the structural metrics and sty_score in isolation before
integration.

Usage (from the project root):
    python scripts/test_stylometry.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from detection.stylometry import stylometry
from scripts.test_llm_signal import SAMPLES


def main():
    for label, text in SAMPLES:
        print("=" * 70)
        print(f"SAMPLE: {label}")
        print(f"TEXT:   {text[:80]}{'...' if len(text) > 80 else ''}")
        result = stylometry(text)
        print(f"  sty_score : {result['sty_score']}  (0=human, 1=AI)")
        print("  metrics   :", json.dumps(result["metrics"], indent=2))
    print("=" * 70)


if __name__ == "__main__":
    main()
