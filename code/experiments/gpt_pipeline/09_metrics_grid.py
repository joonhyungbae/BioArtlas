#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
09_metrics_grid.py

역할:
- R-A(RA: multihot_features.npy, 선택) + R-B(RB: concat_features.npy) + R-C(RC: avg_kernel.npy)
- K ∈ [k_min, k_max], seed ∈ [0..seeds-1]
  * RA: k-means on features (있을 때만)
  * RB: k-means on features
  * RC: spectral on kernel
- 공통 메트릭 공간: concat_features에서 silhouette(cosine), Calinski–Harabasz, Davies–Bouldin 계산
- 평균±표준편차 집계, CSV/LaTeX 저장, 간결한 랭킹 요약 출력

산출:
- results/tables/table1_metrics.csv
- results/tables/table1_metrics.tex (열별 최고치 굵게)
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import importlib.util
import sys

import numpy as np
import yaml


BASE_DIR = Path(__file__).resolve().parent


def import_utils_module() -> object:
    util_path = BASE_DIR / "05_utils_srmva.py"
    if not util_path.exists():
        print(f"[09] 유틸 파일이 없습니다: {util_path}", file=sys.stderr)
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("utils_srmva", util_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore
    return module


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg or {}


def fmt_mean_std(mean: float, std: float, prec: int = 4) -> str:
    if not np.isfinite(mean) or not np.isfinite(std):
        return "nan"
    return f"{mean:.{prec}f}±{std:.{prec}f}"


def bold_best(values: List[str], best_idx: int) -> List[str]:
    out: List[str] = []
    for i, v in enumerate(values):
        if i == best_idx and v != "nan":
            out.append(f"\\textbf{{{v}}}")
        else:
            out.append(v)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=str, default=str(BASE_DIR / "config.yaml"))
    # Optional overrides for quick smoke tests
    ap.add_argument("--seeds", type=int, default=None)
    ap.add_argument("--k-min", type=int, default=None)
    ap.add_argument("--k-max", type=int, default=None)
    args = ap.parse_args()

    cfg = load_config(Path(args.config))
    exp_cfg = cfg.get("exp", {})
    out_cfg = cfg.get("output", {})

    k_range = exp_cfg.get("k_range", [5, 15])
    if not (isinstance(k_range, list) and len(k_range) == 2):
        print("[09] exp.k_range 형식이 잘못되었습니다. 예: [5, 15]", file=sys.stderr)
        sys.exit(1)
    k_min, k_max = int(k_range[0]), int(k_range[1])
    if args.k_min is not None:
        k_min = int(args.k_min)
    if args.k_max is not None:
        k_max = int(args.k_max)
    if k_min > k_max:
        k_min, k_max = k_max, k_min
    seeds = int(exp_cfg.get("seeds", 50))
    if args.seeds is not None:
        seeds = int(args.seeds)
    n_init = int(exp_cfg.get("n_init", 20))

    output_root = Path(out_cfg.get("dir", "results"))
    if not output_root.is_absolute():
        output_root = (BASE_DIR / output_root).resolve()
    runs_dir = output_root / "runs"
    tables_dir = output_root / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    # Inputs
    X_concat_path = runs_dir / "concat_features.npy"
    K_avg_path = runs_dir / "avg_kernel.npy"
    X_mh_path = runs_dir / "multihot_features.npy"
    if not X_concat_path.exists() or not K_avg_path.exists():
        print("[09] 필요 파일이 없습니다: concat_features.npy 또는 avg_kernel.npy", file=sys.stderr)
        sys.exit(1)
    X_concat = np.load(X_concat_path)
    K_full = np.load(K_avg_path)
    X_mh: Optional[np.ndarray] = np.load(X_mh_path) if X_mh_path.exists() else None
    # Sanitize any non-finite values from precomputed artifacts
    X_concat = np.nan_to_num(X_concat.astype(np.float32, copy=False), nan=0.0, posinf=0.0, neginf=0.0)
    K_full = np.nan_to_num(K_full.astype(np.float32, copy=False), nan=0.0, posinf=0.0, neginf=0.0)
    if X_mh is not None:
        X_mh = np.nan_to_num(X_mh.astype(np.float32, copy=False), nan=0.0, posinf=0.0, neginf=0.0)
    N = X_concat.shape[0]
    print(f"[09] N={N}, concat_dim={X_concat.shape[1]}, multihot={'yes' if X_mh is not None else 'no'}")

    utils = import_utils_module()

    # Storage: per (rep, method, K) -> list of metric dicts
    # rep in {RA, RB, RC}, method in {kmeans, spectral}
    perkey_results: Dict[Tuple[str, str, int], List[Dict[str, float]]] = {}

    Ks = list(range(k_min, k_max + 1))
    for K_clusters in Ks:
        print(f"[09] K={K_clusters} ...")
        for s in range(seeds):
            # RB: k-means on concat features
            labels_rb = utils.kmeans_labels_from_features(X_concat, K_clusters, seed=s, n_init=n_init)
            m_rb = utils.internal_metrics(X_concat, labels_rb)
            perkey_results.setdefault(("RB", "kmeans", K_clusters), []).append(m_rb)

            # RA: if available, k-means on multihot
            if X_mh is not None:
                labels_ra = utils.kmeans_labels_from_features(X_mh, K_clusters, seed=s, n_init=n_init)
                m_ra = utils.internal_metrics(X_concat, labels_ra)
                perkey_results.setdefault(("RA", "kmeans", K_clusters), []).append(m_ra)

            # RC: spectral on kernel
            labels_rc = utils.spectral_labels_from_kernel(K_full, K_clusters, seed=s)
            m_rc = utils.internal_metrics(X_concat, labels_rc)
            perkey_results.setdefault(("RC", "spectral", K_clusters), []).append(m_rc)

    # Aggregate mean/std per key
    rows: List[Dict[str, object]] = []
    for (rep, method, K_clusters), metrics_list in sorted(perkey_results.items(), key=lambda x: (x[0][2], x[0][0], x[0][1])):
        s_vals = np.array([d.get("silhouette_cosine", np.nan) for d in metrics_list], dtype=float)
        ch_vals = np.array([d.get("calinski_harabasz", np.nan) for d in metrics_list], dtype=float)
        db_vals = np.array([d.get("davies_bouldin", np.nan) for d in metrics_list], dtype=float)
        row = {
            "K": K_clusters,
            "rep": rep,
            "method": method,
            "silhouette_mean": float(np.nanmean(s_vals)),
            "silhouette_std": float(np.nanstd(s_vals, ddof=0)),
            "ch_mean": float(np.nanmean(ch_vals)),
            "ch_std": float(np.nanstd(ch_vals, ddof=0)),
            "db_mean": float(np.nanmean(db_vals)),
            "db_std": float(np.nanstd(db_vals, ddof=0)),
            "runs": int(np.sum(np.isfinite(s_vals)))
        }
        rows.append(row)

    # Save CSV
    csv_path = tables_dir / "table1_metrics.csv"
    ensure_parent_dir(csv_path)
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["K", "rep", "method", "silhouette_mean", "silhouette_std", "ch_mean", "ch_std", "db_mean", "db_std", "runs"])
        for r in rows:
            w.writerow([
                r["K"], r["rep"], r["method"],
                f"{r['silhouette_mean']:.6f}", f"{r['silhouette_std']:.6f}",
                f"{r['ch_mean']:.6f}", f"{r['ch_std']:.6f}",
                f"{r['db_mean']:.6f}", f"{r['db_std']:.6f}",
                r["runs"],
            ])
    print(f"[09] CSV 저장: {csv_path}")

    # Build LaTeX table with bold best per K per metric
    # Group rows by K and compare available reps/methods
    tex_lines: List[str] = []
    tex_lines.append("% Auto-generated by 09_metrics_grid.py")
    tex_lines.append("\\begin{tabular}{llrrrrr}")
    tex_lines.append("\\toprule")
    tex_lines.append("K & Rep & Method & Silhouette & CH & DB \\ ")
    tex_lines.append("\\midrule")

    for K_clusters in Ks:
        block = [r for r in rows if r["K"] == K_clusters]
        if not block:
            continue
        # Determine best indices per metric (handle all-NaN safely)
        sil_means = np.array([r["silhouette_mean"] for r in block], dtype=float)
        ch_means = np.array([r["ch_mean"] for r in block], dtype=float)
        db_means = np.array([r["db_mean"] for r in block], dtype=float)
        try:
            best_s_idx = int(np.nanargmax(sil_means))
        except ValueError:
            best_s_idx = -1
        try:
            best_c_idx = int(np.nanargmax(ch_means))
        except ValueError:
            best_c_idx = -1
        try:
            best_d_idx = int(np.nanargmin(db_means))
        except ValueError:
            best_d_idx = -1

        for idx, r in enumerate(block):
            sil = fmt_mean_std(r["silhouette_mean"], r["silhouette_std"], 4)
            ch = fmt_mean_std(r["ch_mean"], r["ch_std"], 2)
            db = fmt_mean_std(r["db_mean"], r["db_std"], 4)
            if idx == best_s_idx and sil != "nan":
                sil = f"\\textbf{{{sil}}}"
            if idx == best_c_idx and ch != "nan":
                ch = f"\\textbf{{{ch}}}"
            if idx == best_d_idx and db != "nan":
                db = f"\\textbf{{{db}}}"
            tex_lines.append(f"{K_clusters} & {r['rep']} & {r['method']} & {sil} & {ch} & {db} \\")
        tex_lines.append("\\midrule")

    tex_lines.append("\\bottomrule")
    tex_lines.append("\\end{tabular}")

    tex_path = tables_dir / "table1_metrics.tex"
    ensure_parent_dir(tex_path)
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write("\n".join(tex_lines))
    print(f"[09] LaTeX 저장: {tex_path}")

    # Concise ranking summary (by silhouette mean) per K
    print("[09] Ranking (by silhouette mean):")
    for K_clusters in Ks:
        block = [r for r in rows if r["K"] == K_clusters]
        if not block:
            continue
        block_sorted = sorted(block, key=lambda r: r["silhouette_mean"], reverse=True)
        disp = [f"{r['rep']}-{r['method']}({r['silhouette_mean']:.4f})" for r in block_sorted]
        print(f"  K={K_clusters}: ", ", ".join(disp))

    print("[09] 완료.")


if __name__ == "__main__":
    main()


