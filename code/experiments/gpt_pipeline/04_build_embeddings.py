#!/usr/bin/env python3

"""Compatibility wrapper around the official embedding pipeline.

Historically this directory carried its own embedding bootstrap step. The
official reproduction path now lives in ``code/04_build_embeddings.py``. This wrapper
executes that canonical script and mirrors the generated files into the legacy
``result_gpt/04_embedding`` directory for downstream compatibility.
"""

from __future__ import annotations

from pathlib import Path

from _canonical_runner import mirror_tree, run_canonical


if __name__ == "__main__":
    run_canonical("04_build_embeddings.py")

    base_dir = Path(__file__).resolve().parent
    code_dir = base_dir.parents[1]
    src = code_dir / "artifacts" / "04_embedding" / "bge_large_en_v1_5"
    dst = base_dir / "result_gpt" / "04_embedding"
    if src.exists():
        mirror_tree(src, dst)
