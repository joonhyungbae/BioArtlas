#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
12_year_distribution.py

역할:
- data/ids.csv(Year 포함)과 results/runs/final_labels.npy를 로드
- 군집별 연도 분포(violinplot) 시각화 및 중앙값/사분위수 범위(IQR) 산출

산출:
- results/figs/year_distribution.pdf
- results/tables/year_stats.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import List

import numpy as np
import yaml


BASE_DIR = Path(__file__).resolve().parent


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg or {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=str, default=str(BASE_DIR / "config.yaml"))
    ap.add_argument("--plot", type=str, choices=["violin", "box"], default="violin")
    args = ap.parse_args()

    # Config
    cfg = load_config(Path(args.config))
    data_cfg = cfg.get("data", {})
    out_cfg = cfg.get("output", {})

    ids_csv = Path(data_cfg.get("ids_csv", "data/ids.csv"))
    if not ids_csv.is_absolute():
        ids_csv = (BASE_DIR / ids_csv).resolve()

    output_root = Path(out_cfg.get("dir", "results"))
    if not output_root.is_absolute():
        output_root = (BASE_DIR / output_root).resolve()
    runs_dir = output_root / "runs"
    figs_dir = output_root / "figs"
    tables_dir = output_root / "tables"
    figs_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    labels_path = runs_dir / "final_labels.npy"
    if not ids_csv.exists() or not labels_path.exists():
        print(f"[12] 필요 파일이 없습니다: {ids_csv} 또는 {labels_path}", file=sys.stderr)
        sys.exit(1)

    try:
        import pandas as pd  # type: ignore
    except Exception as exc:
        raise ImportError("pandas가 필요합니다. 'pip install pandas'로 설치하세요.") from exc

    # Load inputs
    df = pd.read_csv(ids_csv)
    y = np.load(labels_path)
    if y.ndim != 1:
        print("[12] final_labels.npy 은 1D여야 합니다.", file=sys.stderr)
        sys.exit(1)
    if len(df) != y.shape[0]:
        print(f"[12] ids.csv 행 수와 라벨 길이가 다릅니다: {len(df)} vs {y.shape[0]}", file=sys.stderr)
        sys.exit(1)

    # Prepare Year column
    if "Year" not in df.columns:
        print("[12] ids.csv에 'Year' 컬럼이 없습니다.", file=sys.stderr)
        sys.exit(1)
    years = pd.to_numeric(df["Year"], errors="coerce")
    valid_mask = years.notna()
    if valid_mask.sum() == 0:
        print("[12] 유효한 연도 값이 없습니다.", file=sys.stderr)
        sys.exit(1)

    years = years.astype(float).to_numpy()
    labels = y.astype(int, copy=False)

    # Filter invalid rows
    years_v = years[valid_mask.to_numpy()]
    labels_v = labels[valid_mask.to_numpy()]

    clusters = np.unique(labels_v)

    # Compute stats per cluster
    rows: List[str] = ["cluster,n,median,q1,q3,iqr"]
    stats = {}
    for c in clusters:
        idx = np.where(labels_v == c)[0]
        vals = years_v[idx]
        if vals.size == 0:
            med = q1 = q3 = iqr = np.nan
        else:
            q1 = float(np.percentile(vals, 25))
            q3 = float(np.percentile(vals, 75))
            med = float(np.median(vals))
            iqr = float(q3 - q1)
        rows.append(f"{int(c)},{vals.size},{med:.3f},{q1:.3f},{q3:.3f},{iqr:.3f}")
        stats[int(c)] = vals

    # Save stats CSV
    csv_path = tables_dir / "year_stats.csv"
    ensure_parent_dir(csv_path)
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("\n".join(rows))
    print(f"[12] 저장: {csv_path}")

    # Plot distribution
    import matplotlib.pyplot as plt

    # Prepare data grouped
    data = [stats[int(c)] for c in clusters]
    labels_txt = [str(int(c)) for c in clusters]

    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    if args.plot == "violin":
        vp = ax.violinplot(data, showmeans=False, showmedians=True, showextrema=False)
        # Color tweak
        for body in vp['bodies']:
            body.set_facecolor('#4C78A8')
            body.set_edgecolor('black')
            body.set_alpha(0.7)
    else:
        bp = ax.boxplot(data, showfliers=False, labels=None)
        for element in ['boxes', 'whiskers', 'caps', 'medians']:
            for item in bp[element]:
                item.set_color('#4C78A8')

    ax.set_xticks(np.arange(1, len(labels_txt) + 1))
    ax.set_xticklabels(labels_txt)
    ax.set_xlabel("Cluster")
    ax.set_ylabel("Year")
    ax.set_title("Year distribution per cluster (median/IQR)")
    ax.grid(True, axis='y', linestyle=':', alpha=0.3)

    out_fig = figs_dir / "year_distribution.pdf"
    ensure_parent_dir(out_fig)
    fig.tight_layout()
    fig.savefig(out_fig, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[12] 저장: {out_fig}")

    print("[12] 완료.")


if __name__ == "__main__":
    main()


