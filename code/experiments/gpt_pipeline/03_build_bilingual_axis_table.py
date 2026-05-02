#!/usr/bin/env python3

"""Legacy entrypoint kept for compatibility.

The canonical implementation now lives in ``code/preprocess/03_build_bilingual_axis_table.py``.
Running this file forwards execution there so processed bilingual axis tables are
built from one maintained code path.
"""

from __future__ import annotations

from _canonical_runner import run_canonical


if __name__ == "__main__":
    run_canonical("preprocess/03_build_bilingual_axis_table.py")
