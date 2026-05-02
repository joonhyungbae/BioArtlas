#!/usr/bin/env python3

"""Legacy entrypoint kept for compatibility.

The canonical implementation now lives in ``code/preprocess/02_review_ko_en_labels.py``.
Running this file forwards execution there so the QA/fix logic stays in one
place.
"""

from __future__ import annotations

from _canonical_runner import run_canonical


if __name__ == "__main__":
    run_canonical("preprocess/02_review_ko_en_labels.py")
