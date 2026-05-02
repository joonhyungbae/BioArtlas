#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
13_mkkm_train.py

역할:
- SimpleMKKM 스타일의 축 가중치 w_v 학습.
  초기 w_v=1/V에서 시작 → K = Σ w_v K^(v) → 스펙트럴 임베딩 + k-means → 라벨
  → 각 축 커널의 (intra − inter) 유사도 점수 기반으로 w 갱신(비음수, 합=1)
  → 수렴(tol) 혹은 max_iter 도달까지 반복.

입력 옵션:
- --K <int>                : 클러스터 수(필수가 아니며, 미제공 시 PAC 곡선에서 argmin PAC 자동 추정)
- --seeds 50               : 시드 수
- --max_iter 50            : 최대 반복 수
- --tol 1e-4               : 가중치 변화 수렴 기준(L1)

산출:
- results/runs/mkkm_weights.npy        : 평균 최종 가중치 (V,)
- results/runs/mkkm_kernel.npy         : 평균 가중치로 결합한 최종 커널 (N,N)
- results/runs/mkkm_labels_seed*.npy   : 시드별 라벨
- results/tables/mkkm_metrics.csv      : 09와 호환되는 메트릭 CSV
- results/figs/axis_weights_mkkm.pdf   : 축 가중치 막대그래프
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Tuple
import importlib.util
import sys

import numpy as np
import yaml


BASE_DIR = Path(__file__).resolve().parent
EPS = 1e-12


def import_utils_module() -> object:
    util_path = BASE_DIR / "05_utils_srmva.py"
    if not util_path.exists():
        print(f"[13] 유틸 파일이 없습니다: {util_path}", file=sys.stderr)
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


def weighted_combine_kernels(kernels: List[np.ndarray], weights: np.ndarray) -> np.ndarray:
    assert len(kernels) == weights.size
    K_sum = np.zeros_like(kernels[0], dtype=np.float64)
    for w, K in zip(weights, kernels):
        K_sum += float(w) * K.astype(np.float64, copy=False)
    K_sum = 0.5 * (K_sum + K_sum.T)
    K_sum = np.nan_to_num(K_sum, nan=0.0, posinf=0.0, neginf=0.0)
    return K_sum.astype(np.float32)


def intra_inter_score(K: np.ndarray, labels: np.ndarray) -> Tuple[float, float, float]:
    """Return (intra_mean, inter_mean, score=intra-inter) over i<j pairs.
    Diagonal self-similarities are ignored.
    """
    n = K.shape[0]
    iu = np.triu_indices(n, k=1)
    lab = labels.astype(np.int64, copy=False)
    same = (lab[iu[0]] == lab[iu[1]])
    vals = K[iu]
    if np.any(same):
        intra_mean = float(np.mean(vals[same]))
    else:
        intra_mean = 0.0
    if np.any(~same):
        inter_mean = float(np.mean(vals[~same]))
    else:
        inter_mean = 0.0
    return intra_mean, inter_mean, intra_mean - inter_mean


def update_weights_from_labels(K_axes: List[np.ndarray], labels: np.ndarray, w_prev: np.ndarray, alpha: float = 0.6) -> np.ndarray:
    """Compute new weights from (intra-inter) scores per axis, with damping alpha.
    Ensures non-negativity and sum-to-1.
    """
    scores = []
    for K in K_axes:
        _, __, s = intra_inter_score(K, labels)
        scores.append(max(0.0, float(s)))
    scores_arr = np.asarray(scores, dtype=np.float64)
    if not np.any(scores_arr > 0):
        # fallback to previous weights if all scores are zero
        w_new = w_prev.copy()
    else:
        scores_norm = scores_arr / max(float(np.sum(scores_arr)), EPS)
        w_new = (1.0 - alpha) * w_prev + alpha * scores_norm
    # project to simplex
    w_new = np.maximum(w_new, 0.0)
    ssum = float(np.sum(w_new))
    if ssum <= 0:
        w_new = np.ones_like(w_new) / w_new.size
    else:
        w_new = w_new / ssum
    return w_new.astype(np.float64)


def infer_K_from_pac(tables_dir: Path) -> int | None:
    path = tables_dir / "stability_curve.csv"
    if not path.exists():
        return None
    try:
        import csv
        with open(path, "r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            rows = [(int(row["K"]), float(row["PAC"])) for row in r]
        if not rows:
            return None
        rows_sorted = sorted(rows, key=lambda x: (x[1], x[0]))
        return rows_sorted[0][0]
    except Exception:
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=str, default=str(BASE_DIR / "config.yaml"))
    ap.add_argument("--K", type=int, default=0)
    ap.add_argument("--seeds", type=int, default=50)
    ap.add_argument("--max_iter", type=int, default=50)
    ap.add_argument("--tol", type=float, default=1e-4)
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
    runs_dir.mkdir(parents=True, exist_ok=True)
    figs_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    utils = import_utils_module()

    # Load features for metrics space and axis embeddings for kernels
    concat_path = runs_dir / "concat_features.npy"
    if not embeddings_npz.exists() or not concat_path.exists():
        print(f"[13] 필요 파일이 없습니다: {embeddings_npz} 또는 {concat_path}", file=sys.stderr)
        sys.exit(1)
    X_concat = np.load(concat_path)
    X_concat = np.nan_to_num(X_concat.astype(np.float32, copy=False), nan=0.0, posinf=0.0, neginf=0.0)

    axes_embeddings: Dict[str, np.ndarray] = utils.load_embeddings(str(embeddings_npz))
    axis_names = sorted(axes_embeddings.keys())

    # Build axis cosine kernels with optional trace normalization
    use_trace_normalize = bool(exp_cfg.get("use_trace_normalize", True))
    axes_cos = {k: utils.l2_normalize_rows(v) for k, v in axes_embeddings.items()}
    K_axes_dict: Dict[str, np.ndarray] = utils.build_axis_kernels(axes_cos, trace_normalize=use_trace_normalize)
    K_axes: List[np.ndarray] = [K_axes_dict[name] for name in axis_names]
    V = len(K_axes)
    if V == 0:
        print("[13] 축 커널이 없습니다.", file=sys.stderr)
        sys.exit(1)

    # Determine K
    K_clusters = int(args.K)
    if K_clusters <= 0:
        inferred = infer_K_from_pac(tables_dir)
        if inferred is None:
            print("[13] --K를 지정하거나 stability_curve.csv로부터 추정이 가능해야 합니다.", file=sys.stderr)
            sys.exit(1)
        K_clusters = int(inferred)
    print(f"[13] K={K_clusters}, seeds={args.seeds}, max_iter={args.max_iter}, tol={args.tol}")

    # Per-seed optimization
    per_seed_weights: List[np.ndarray] = []
    metrics_list: List[Dict[str, float]] = []
    for s in range(int(args.seeds)):
        rng = np.random.RandomState(s)
        w = np.ones(V, dtype=np.float64) / V
        last_w = w.copy()
        for it in range(int(args.max_iter)):
            # Combine kernel
            K_comb = weighted_combine_kernels(K_axes, w)
            # Spectral + k-means labels
            labels = utils.spectral_labels_from_kernel(K_comb, K_clusters=K_clusters, seed=s)
            # Update weights from labels
            w = update_weights_from_labels(K_axes, labels, w_prev=w, alpha=0.6)
            # Check convergence
            diff = float(np.sum(np.abs(w - last_w)))
            if diff < float(args.tol):
                break
            last_w = w.copy()
        per_seed_weights.append(w.astype(np.float64))
        # Save labels per seed
        labels_path = runs_dir / f"mkkm_labels_seed{s}.npy"
        np.save(labels_path, labels)
        # Metrics in common space
        m = utils.internal_metrics(X_concat, labels)
        metrics_list.append(m)

    # Aggregate weights across seeds
    W = np.vstack(per_seed_weights)  # (S, V)
    w_mean = W.mean(axis=0)
    w_mean = np.maximum(w_mean, 0.0)
    w_mean = w_mean / max(float(np.sum(w_mean)), EPS)

    # Final kernel from mean weights
    K_final = weighted_combine_kernels(K_axes, w_mean)

    # Save artifacts
    weights_path = runs_dir / "mkkm_weights.npy"
    kernel_path = runs_dir / "mkkm_kernel.npy"
    np.save(weights_path, w_mean.astype(np.float32))
    np.save(kernel_path, K_final)
    print(f"[13] 저장: {weights_path} (shape={w_mean.shape}), {kernel_path} (shape={K_final.shape})")

    # Metrics CSV (compatible with Table 1 merge)
    import csv
    s_vals = np.array([d.get("silhouette_cosine", np.nan) for d in metrics_list], dtype=float)
    ch_vals = np.array([d.get("calinski_harabasz", np.nan) for d in metrics_list], dtype=float)
    db_vals = np.array([d.get("davies_bouldin", np.nan) for d in metrics_list], dtype=float)
    row = {
        "K": K_clusters,
        "rep": "MK",
        "method": "mkkm",
        "silhouette_mean": float(np.nanmean(s_vals)),
        "silhouette_std": float(np.nanstd(s_vals, ddof=0)),
        "ch_mean": float(np.nanmean(ch_vals)),
        "ch_std": float(np.nanstd(ch_vals, ddof=0)),
        "db_mean": float(np.nanmean(db_vals)),
        "db_std": float(np.nanstd(db_vals, ddof=0)),
        "runs": int(np.sum(np.isfinite(s_vals))),
    }
    metrics_csv = tables_dir / "mkkm_metrics.csv"
    with open(metrics_csv, "w", encoding="utf-8", newline="") as f:
        wcsv = csv.writer(f)
        wcsv.writerow(["K", "rep", "method", "silhouette_mean", "silhouette_std", "ch_mean", "ch_std", "db_mean", "db_std", "runs"])
        wcsv.writerow([
            row["K"], row["rep"], row["method"],
            f"{row['silhouette_mean']:.6f}", f"{row['silhouette_std']:.6f}",
            f"{row['ch_mean']:.6f}", f"{row['ch_std']:.6f}",
            f"{row['db_mean']:.6f}", f"{row['db_std']:.6f}",
            row["runs"],
        ])
    print(f"[13] 저장: {metrics_csv}")

    # Plot axis weights
    import matplotlib.pyplot as plt
    order = np.argsort(w_mean)[::-1]
    names_sorted = [axis_names[i] for i in order]
    weights_sorted = w_mean[order]
    fig, ax = plt.subplots(figsize=(7.8, 4.6))
    ax.barh(range(len(names_sorted)), weights_sorted[::-1], color="#F58518")
    ax.set_yticks(range(len(names_sorted)))
    ax.set_yticklabels(names_sorted[::-1])
    ax.set_xlabel("Weight")
    ax.set_title("MK-KMeans learned axis weights")
    ax.grid(True, axis="x", linestyle=":", alpha=0.3)
    out_fig = figs_dir / "axis_weights_mkkm.pdf"
    ensure_parent_dir(out_fig)
    fig.tight_layout()
    fig.savefig(out_fig, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[13] 저장: {out_fig}")

    print("[13] 완료.")


if __name__ == "__main__":
    main()


