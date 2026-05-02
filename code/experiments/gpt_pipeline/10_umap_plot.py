#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
10_umap_plot.py

역할:
- results/runs/concat_features.npy, results/runs/final_labels.npy 로드
- 고정 파라미터 UMAP(n_neighbors=15, min_dist=0.1) + 고정 시드로 2D 임베딩
- 라벨 색상 산점도 저장: results/figs/umap_final.pdf

Figure 제목/캡션에 노트 표기: "for visualization only; metrics in original/kernel space"
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import yaml


BASE_DIR = Path(__file__).resolve().parent


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_config(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        return cfg or {}
    except Exception:
        return {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=str, default=str(BASE_DIR / "config.yaml"))
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    cfg = load_config(Path(args.config))
    out_cfg = cfg.get("output", {})

    output_root = Path(out_cfg.get("dir", "results"))
    if not output_root.is_absolute():
        output_root = (BASE_DIR / output_root).resolve()
    runs_dir = output_root / "runs"
    figs_dir = output_root / "figs"
    figs_dir.mkdir(parents=True, exist_ok=True)

    X_path = runs_dir / "concat_features.npy"
    y_path = runs_dir / "final_labels.npy"
    if not X_path.exists() or not y_path.exists():
        print(f"[10] 필요 파일이 없습니다: {X_path} 또는 {y_path}", file=sys.stderr)
        sys.exit(1)

    X = np.load(X_path)
    y = np.load(y_path)
    if X.ndim != 2:
        print(f"[10] X는 2D여야 합니다. shape={X.shape}", file=sys.stderr)
        sys.exit(1)
    if y.ndim != 1 or y.shape[0] != X.shape[0]:
        print(f"[10] 라벨 길이가 X와 다릅니다. len(y)={y.shape[0]}, N={X.shape[0]}", file=sys.stderr)
        sys.exit(1)

    # Sanitize any non-finite values
    X = np.nan_to_num(X.astype(np.float32, copy=False), nan=0.0, posinf=0.0, neginf=0.0)

    try:
        import umap  # type: ignore
    except Exception as exc:
        raise ImportError("UMAP가 필요합니다. 'pip install umap-learn'으로 설치하세요.") from exc

    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=15,
        min_dist=0.1,
        random_state=int(args.seed),
        metric="euclidean",
    )
    Z = reducer.fit_transform(X)

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.2, 5.0))
    sc = ax.scatter(Z[:, 0], Z[:, 1], c=y, cmap="tab20", s=22, linewidths=0.0)
    ax.set_xlabel("UMAP-1")
    ax.set_ylabel("UMAP-2")
    ax.set_title("UMAP of concat features (colored by K* labels)\nfor visualization only; metrics in original/kernel space")
    cbar = plt.colorbar(sc, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Cluster label (K*)")
    ax.grid(True, linestyle=":", alpha=0.3)

    out_path = figs_dir / "umap_final.pdf"
    ensure_parent_dir(out_path)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[10] 저장: {out_path}")


if __name__ == "__main__":
    main()


