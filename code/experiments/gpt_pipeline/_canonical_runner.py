#!/usr/bin/env python3

"""Helpers for forwarding legacy experiment entrypoints to canonical scripts."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys


BASE_DIR = Path(__file__).resolve().parent
CODE_DIR = BASE_DIR.parents[1]


def run_canonical(relative_script: str) -> None:
    """Execute a script under ``code/`` while preserving CLI arguments."""
    target = CODE_DIR / relative_script
    if not target.exists():
        raise SystemExit(f"Canonical script not found: {target}")

    print(f"[gpt_pipeline] Forwarding to canonical script: {target}")
    subprocess.run(
        [sys.executable, str(target), *sys.argv[1:]],
        cwd=CODE_DIR,
        check=True,
    )


def mirror_tree(src: Path, dst: Path) -> None:
    """Mirror a generated artifact tree into a legacy compatibility location."""
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    print(f"[gpt_pipeline] Mirrored artifacts: {src} -> {dst}")
