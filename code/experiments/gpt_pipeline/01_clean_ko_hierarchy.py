#!/usr/bin/env python3

"""Legacy entrypoint kept for compatibility.

The canonical implementation now lives in ``code/preprocess/01_clean_ko_hierarchy.py``.
Running this file forwards execution there so the normalization logic has a
single source of truth.
"""

from __future__ import annotations

from _canonical_runner import run_canonical


if __name__ == "__main__":
    run_canonical("preprocess/01_clean_ko_hierarchy.py")
