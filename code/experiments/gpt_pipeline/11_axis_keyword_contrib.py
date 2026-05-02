#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
11_axis_keyword_contrib.py

역할:
- 축 임베딩과 최종 레이블을 로드하여
  (a) 커널 얼라인먼트(정규화, 센터링 포함) 기반 전역 축 중요도
  (b) 클러스터별 축 중심성(평균 임베딩 대비 평균 코사인 유사도)
  를 계산하고 시각화 저장.

- raw terms가 있으면, TF–IDF 기반 클러스터별 Top-10 키워드를 CSV로 저장(없으면 생략).

산출:
- results/figs/axis_contrib_bars.pdf
- results/tables/top_keywords_per_cluster.csv (옵션)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple
import importlib.util
import sys

import numpy as np
import yaml


BASE_DIR = Path(__file__).resolve().parent


def import_utils_module() -> object:
    util_path = BASE_DIR / "05_utils_srmva.py"
    if not util_path.exists():
        print(f"[11] 유틸 파일이 없습니다: {util_path}", file=sys.stderr)
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


def center_kernel(K: np.ndarray) -> np.ndarray:
    n = K.shape[0]
    I = np.eye(n, dtype=np.float64)
    one_n = np.full((n, n), 1.0 / n, dtype=np.float64)
    H = I - one_n
    Kc = H @ K @ H
    return Kc


def kernel_alignment_centered(K1: np.ndarray, K2: np.ndarray) -> float:
    if K1.shape != K2.shape:
        return float("nan")
    K1 = np.nan_to_num(K1.astype(np.float64, copy=False), nan=0.0, posinf=0.0, neginf=0.0)
    K2 = np.nan_to_num(K2.astype(np.float64, copy=False), nan=0.0, posinf=0.0, neginf=0.0)
    K1c = center_kernel(K1)
    K2c = center_kernel(K2)
    num = float(np.sum(K1c * K2c))
    den = float(np.linalg.norm(K1c) * np.linalg.norm(K2c))
    if den <= 0.0 or not np.isfinite(den):
        return 0.0
    return num / den


def compute_global_axis_importance(axes_embeddings: Dict[str, np.ndarray], use_trace_normalize: bool, utils) -> Tuple[List[str], np.ndarray]:
    axis_names = sorted(axes_embeddings.keys())
    # Build per-axis cosine kernels (as in 06)
    axes_cos = {k: utils.l2_normalize_rows(v) for k, v in axes_embeddings.items()}
    K_axes: Dict[str, np.ndarray] = utils.build_axis_kernels(axes_cos, trace_normalize=use_trace_normalize)
    K_avg = utils.combine_kernels_average(K_axes)
    # Alignment per axis
    scores: List[float] = []
    for name in axis_names:
        Ka = K_axes[name].astype(np.float32, copy=False)
        score = kernel_alignment_centered(Ka, K_avg)
        scores.append(float(score))
    return axis_names, np.asarray(scores, dtype=np.float64)


def compute_cluster_axis_centrality(axes_embeddings: Dict[str, np.ndarray], labels: np.ndarray, utils) -> Tuple[List[str], np.ndarray]:
    axis_names = sorted(axes_embeddings.keys())
    y = labels.astype(np.int64, copy=False)
    clusters = np.unique(y)
    num_axes = len(axis_names)
    num_clusters = clusters.size
    centrality = np.zeros((num_axes, num_clusters), dtype=np.float64)
    # For each axis and cluster, compute mean cosine(x_i, centroid_c)
    for ai, name in enumerate(axis_names):
        E = axes_embeddings[name]
        E = utils.l2_normalize_rows(E)
        for cj, c in enumerate(clusters):
            idx = np.where(y == c)[0]
            if idx.size == 0:
                centrality[ai, cj] = np.nan
                continue
            Ec = E[idx]
            centroid = Ec.mean(axis=0, dtype=np.float64, keepdims=False)
            # normalize centroid
            cnorm = np.linalg.norm(centroid)
            if cnorm <= 1e-12:
                centrality[ai, cj] = 0.0
                continue
            centroid = (centroid / cnorm).astype(np.float32, copy=False)
            sims = (Ec @ centroid)
            # Clip numeric noise
            sims = np.clip(sims, -1.0, 1.0)
            centrality[ai, cj] = float(np.mean(sims))
    return axis_names, centrality


def try_build_keywords_top10(cfg: dict, labels: np.ndarray, out_csv: Path) -> None:
    data_cfg = cfg.get("data", {})
    raw_csv = data_cfg.get("raw_terms_csv")
    meta_json = data_cfg.get("meta_json")
    if not raw_csv or not meta_json:
        return
    csv_path = Path(raw_csv)
    if not csv_path.is_absolute():
        csv_path = (BASE_DIR / csv_path).resolve()
    mj_path = Path(meta_json)
    if not mj_path.is_absolute():
        mj_path = (BASE_DIR / mj_path).resolve()
    if not csv_path.exists() or not mj_path.exists():
        return
    try:
        import pandas as pd  # type: ignore
    except Exception:
        return
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
    except Exception:
        return
    try:
        with open(mj_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        axes_list = meta.get("axes")
        if not isinstance(axes_list, list) or not axes_list:
            return
        axis_columns = [str(x) for x in axes_list]
        df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
        # Build per-sample document by concatenating comma-separated tokens across axis columns
        docs: List[str] = []
        for i in range(len(df)):
            tokens: List[str] = []
            for col in axis_columns:
                if col in df.columns:
                    text = df.at[i, col]
                    if isinstance(text, str) and text.strip():
                        parts = [t.strip().lower() for t in text.split(',') if t.strip()]
                        tokens.extend(parts)
            docs.append(" ".join(tokens))
        # Fit TF-IDF
        tfidf = TfidfVectorizer(min_df=1, token_pattern=r"(?u)\b\w[\w\-\+\.]*\b")
        X = tfidf.fit_transform(docs)  # (N, V)
        vocab = np.array(tfidf.get_feature_names_out())
        y = labels.astype(np.int64, copy=False)
        clusters = np.unique(y)
        rows: List[Tuple[int, int, str, float]] = []
        for c in clusters:
            idx = np.where(y == c)[0]
            if idx.size == 0:
                continue
            vec = X[idx].mean(axis=0)  # (1, V)
            if hasattr(vec, "A1"):
                mean_scores = vec.A1
            else:
                mean_scores = np.asarray(vec).ravel()
            order = np.argsort(mean_scores)[::-1]
            topk = order[:10]
            for rank, j in enumerate(topk, start=1):
                term = vocab[j]
                score = float(mean_scores[j])
                rows.append((int(c), int(rank), term, score))
        # Save CSV
        ensure_parent_dir(out_csv)
        with open(out_csv, "w", encoding="utf-8") as f:
            f.write("cluster,rank,term,score\n")
            for c, r, term, score in rows:
                f.write(f"{c},{r}," + term.replace(",", " ") + f",{score:.6f}\n")
    except Exception:
        # silent skip on any unforeseen parsing/vectorization error
        return


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=str, default=str(BASE_DIR / "config.yaml"))
    args = ap.parse_args()

    cfg = load_config(Path(args.config))
    data_cfg = cfg.get("data", {})
    exp_cfg = cfg.get("exp", {})
    out_cfg = cfg.get("output", {})

    embeddings_npz = Path(data_cfg.get("embeddings_npz", "data/processed/embeddings/bge_large_en_v1_5/embeddings_axes.npz"))
    if not embeddings_npz.is_absolute():
        embeddings_npz = (BASE_DIR / embeddings_npz).resolve()

    output_root = Path(out_cfg.get("dir", "results"))
    if not output_root.is_absolute():
        output_root = (BASE_DIR / output_root).resolve()
    runs_dir = output_root / "runs"
    figs_dir = output_root / "figs"
    tables_dir = output_root / "tables"
    figs_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    labels_path = runs_dir / "final_labels.npy"
    if not embeddings_npz.exists() or not labels_path.exists():
        print(f"[11] 필요 파일이 없습니다: {embeddings_npz} 또는 {labels_path}", file=sys.stderr)
        sys.exit(1)

    utils = import_utils_module()

    # Load axis embeddings and labels
    axes_embeddings: Dict[str, np.ndarray] = utils.load_embeddings(str(embeddings_npz))
    labels = np.load(labels_path)
    if labels.ndim != 1:
        print("[11] final_labels.npy 은 1D여야 합니다.", file=sys.stderr)
        sys.exit(1)

    use_trace_normalize = bool(exp_cfg.get("use_trace_normalize", True))

    # (a) Global axis importance via centered kernel alignment
    axis_names, glob_scores = compute_global_axis_importance(axes_embeddings, use_trace_normalize, utils)

    # (b) Per-cluster axis centrality (mean cosine to cluster centroid)
    _, centrality = compute_cluster_axis_centrality(axes_embeddings, labels, utils)

    # Plot bars and heatmap
    import matplotlib.pyplot as plt
    import matplotlib as mpl

    # Sort axes by global importance
    order = np.argsort(glob_scores)[::-1]
    axis_sorted = [axis_names[i] for i in order]
    scores_sorted = glob_scores[order]

    clusters = np.unique(labels.astype(np.int64, copy=False))
    # Reorder centrality rows to match sorted axes
    centrality_sorted = centrality[order, :]

    fig = plt.figure(figsize=(10.5, 5.2))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.1, 1.6])

    # Left: bar chart of global axis importance
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.barh(range(len(axis_sorted)), scores_sorted[::-1], color="#4C78A8")
    ax1.set_yticks(range(len(axis_sorted)))
    ax1.set_yticklabels(axis_sorted[::-1])
    ax1.set_xlabel("Centered kernel alignment to avg kernel")
    ax1.set_title("Global axis importance (alignment)")
    ax1.grid(True, axis="x", linestyle=":", alpha=0.3)

    # Right: heatmap of per-cluster axis centrality
    ax2 = fig.add_subplot(gs[0, 1])
    im = ax2.imshow(centrality_sorted, aspect="auto", cmap="viridis", vmin=-1.0, vmax=1.0, interpolation="nearest")
    ax2.set_yticks(range(len(axis_sorted)))
    ax2.set_yticklabels(axis_sorted)
    ax2.set_xticks(range(clusters.size))
    ax2.set_xticklabels([str(int(c)) for c in clusters])
    ax2.set_xlabel("Cluster")
    ax2.set_title("Axis centrality per cluster (mean cosine)")
    cbar = fig.colorbar(im, ax=ax2, fraction=0.046, pad=0.04)
    cbar.set_label("Mean cosine")

    fig.suptitle("Axis contributions: alignment (global) and centrality (per-cluster)")
    fig.tight_layout(rect=[0, 0.02, 1, 0.96])

    out_fig = figs_dir / "axis_contrib_bars.pdf"
    ensure_parent_dir(out_fig)
    fig.savefig(out_fig, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[11] 저장: {out_fig}")

    # Optional: Top-10 keywords per cluster via TF–IDF
    out_kw = tables_dir / "top_keywords_per_cluster.csv"
    try_build_keywords_top10(cfg, labels, out_kw)
    if out_kw.exists():
        print(f"[11] 저장: {out_kw}")

    print("[11] 완료.")


if __name__ == "__main__":
    main()


