#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
08_consensus_stability.py

역할:
- results/runs/avg_kernel.npy (필수), results/runs/concat_features.npy (있으면 사용 가능) 로드
- K ∈ [k_min, k_max], seed ∈ [0, seeds-1]에 대해 부트스트랩 반복:
  * 부트스트랩 인덱스 b로 부분 커널 K[b, b]
  * 스펙트럴 클러스터링 → 라벨 수집
  * K별 컨센서스 행렬 누적
- PAC(0.4–0.8)과 엔트로피를 K별로 계산해 곡선 저장 및 플롯
- K* = argmin PAC (동률 시 작은 K) 선택, 해당 K* 컨센서스 히트맵 저장
- K*에 대해 전체 데이터에서 seed=0으로 스펙트럴 실행한 레이블 1세트 저장

산출:
- results/tables/stability_curve.csv
- results/figs/stability_curve.pdf
- results/figs/consensus_heatmap_K*.pdf
- results/runs/final_labels.npy
"""

from __future__ import annotations

import argparse
import csv
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
        print(f"[08] 유틸 파일이 없습니다: {util_path}", file=sys.stderr)
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


def consensus_from_bootstrap_labels(
    N: int, 
    bootstrap_runs: List[Tuple[np.ndarray, np.ndarray]],
) -> np.ndarray:
    """부트스트랩 결과(각각 (indices_b, labels_b))로부터 컨센서스 행렬 계산.

    C_num[i,j]: 동일 클러스터 횟수, C_den[i,j]: 동시 등장 횟수. 최종 C = C_num / C_den (den=0이면 0), diag=1.
    """
    C_num = np.zeros((N, N), dtype=np.float64)
    C_den = np.zeros((N, N), dtype=np.float64)
    for b_idx, lab in bootstrap_runs:
        # pairwise equality within the bootstrap sample only
        eq = (lab[:, None] == lab[None, :]).astype(np.float64)
        # accumulate using advanced indexing
        C_num[np.ix_(b_idx, b_idx)] += eq
        C_den[np.ix_(b_idx, b_idx)] += 1.0
    with np.errstate(invalid="ignore", divide="ignore"):
        C = np.divide(C_num, C_den, out=np.zeros_like(C_num), where=(C_den > 0))
    C = 0.5 * (C + C.T)
    np.fill_diagonal(C, 1.0)
    return C.astype(np.float32, copy=False)


def binary_entropy_mean_upper(C: np.ndarray) -> float:
    """상삼각(i<j)에서 이진 엔트로피 H(p) 평균.
    H(p) = -p log2 p - (1-p) log2(1-p), 경계값은 0으로 처리.
    """
    N = C.shape[0]
    iu = np.triu_indices(N, k=1)
    p = C[iu]
    # Sanitize and clip to avoid log2(0) and log2(1)
    p = np.nan_to_num(p, nan=0.0, posinf=1.0, neginf=0.0)
    p = np.clip(p.astype(np.float64, copy=False), 1e-12, 1 - 1e-12)
    with np.errstate(divide="ignore", invalid="ignore"):
        h = -(p * np.log2(p) + (1 - p) * np.log2(1 - p))
    return float(np.nanmean(h)) if h.size > 0 else float("nan")


def plot_stability_curve(ks: List[int], pac: List[float], ent: List[float], out_path: Path) -> None:
    import matplotlib.pyplot as plt

    x = ks
    fig, ax1 = plt.subplots(figsize=(6.5, 4.2))

    color1 = "tab:blue"
    ax1.set_xlabel("K (clusters)")
    ax1.set_ylabel("PAC (0.4–0.8)", color=color1)
    ax1.plot(x, pac, marker="o", color=color1)
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.grid(True, linestyle=":", alpha=0.4)

    ax2 = ax1.twinx()
    color2 = "tab:green"
    ax2.set_ylabel("Entropy (bits)", color=color2)
    ax2.plot(x, ent, marker="s", color=color2)
    ax2.tick_params(axis='y', labelcolor=color2)

    fig.tight_layout()
    ensure_parent_dir(out_path)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_consensus_heatmap(C: np.ndarray, out_path: Path, title: str) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5.2, 4.8))
    im = ax.imshow(C, cmap="viridis", vmin=0.0, vmax=1.0, interpolation="nearest")
    ax.set_title(title)
    ax.set_xlabel("Samples")
    ax.set_ylabel("Samples")
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Consensus")
    fig.tight_layout()
    ensure_parent_dir(out_path)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=str, default=str(BASE_DIR / "config.yaml"))
    args = ap.parse_args()

    # Config
    cfg = load_config(Path(args.config))
    exp_cfg = cfg.get("exp", {})
    out_cfg = cfg.get("output", {})

    k_range = exp_cfg.get("k_range", [5, 15])
    if not (isinstance(k_range, list) and len(k_range) == 2):
        print("[08] exp.k_range 형식이 잘못되었습니다. 예: [5, 15]", file=sys.stderr)
        sys.exit(1)
    k_min, k_max = int(k_range[0]), int(k_range[1])
    if k_min > k_max:
        k_min, k_max = k_max, k_min
    seeds = int(exp_cfg.get("seeds", 50))

    output_root = Path(out_cfg.get("dir", "results"))
    if not output_root.is_absolute():
        output_root = (BASE_DIR / output_root).resolve()
    runs_dir = output_root / "runs"
    figs_dir = output_root / "figs"
    tables_dir = output_root / "tables"
    runs_dir.mkdir(parents=True, exist_ok=True)
    figs_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    # Inputs
    avg_kernel_path = runs_dir / "avg_kernel.npy"
    concat_feat_path = runs_dir / "concat_features.npy"
    if not avg_kernel_path.exists():
        print(f"[08] 평균 커널이 없습니다: {avg_kernel_path}", file=sys.stderr)
        sys.exit(1)
    K_full = np.load(avg_kernel_path)
    # Sanitize any non-finite values in kernel
    K_full = np.nan_to_num(K_full.astype(np.float32, copy=False), nan=0.0, posinf=0.0, neginf=0.0)
    N = K_full.shape[0]
    print(f"[08] K_full shape={K_full.shape}")

    # Utils
    utils = import_utils_module()

    # Iterate K and seeds, build consensus and stability metrics
    Ks: List[int] = list(range(k_min, k_max + 1))
    pac_list: List[float] = []
    ent_list: List[float] = []
    C_per_K: Dict[int, np.ndarray] = {}

    for K_clusters in Ks:
        print(f"[08] K={K_clusters} 부트스트랩 {seeds}회 ...")
        runs: List[Tuple[np.ndarray, np.ndarray]] = []
        for s in range(seeds):
            b_idx = utils.bootstrap_sample_idx(N, seed=s)
            K_bb = K_full[np.ix_(b_idx, b_idx)]
            labels_b = utils.spectral_labels_from_kernel(K_bb, K_clusters=K_clusters, seed=s)
            runs.append((b_idx, labels_b))
        C = consensus_from_bootstrap_labels(N, runs)
        C_per_K[K_clusters] = C
        pac = utils.pac_score(C, low=0.4, high=0.8)
        ent = binary_entropy_mean_upper(C)
        pac_list.append(float(pac))
        ent_list.append(float(ent))
        print(f"[08] K={K_clusters} PAC={pac:.6f}, Entropy={ent:.6f}")

    # Save stability curve CSV
    curve_csv = tables_dir / "stability_curve.csv"
    with open(curve_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["K", "PAC", "Entropy_bits"])
        for K_clusters, pac, ent in zip(Ks, pac_list, ent_list):
            w.writerow([K_clusters, pac, ent])
    print(f"[08] 저장: {curve_csv}")

    # Plot stability curve
    curve_fig = figs_dir / "stability_curve.pdf"
    plot_stability_curve(Ks, pac_list, ent_list, curve_fig)
    print(f"[08] 저장: {curve_fig}")

    # Select K* by argmin PAC (tie -> smaller K)
    pac_arr = np.asarray(pac_list)
    Ks_arr = np.asarray(Ks)
    # stable lexsort: first by PAC, then by K
    order = np.lexsort((Ks_arr, pac_arr))
    K_star = int(Ks_arr[order[0]])
    print(f"[08] K* (argmin PAC) = {K_star}")

    # Save consensus heatmap for K*
    C_star = C_per_K[K_star]
    heatmap_fig = figs_dir / f"consensus_heatmap_{K_star}.pdf"
    plot_consensus_heatmap(C_star, heatmap_fig, title=f"Consensus Heatmap (K={K_star})")
    print(f"[08] 저장: {heatmap_fig}")

    # Save one deterministic labels array at K* (seed=0, full data)
    labels_full = utils.spectral_labels_from_kernel(K_full, K_clusters=K_star, seed=0)
    labels_path = runs_dir / "final_labels.npy"
    np.save(labels_path, labels_full)
    print(f"[08] 저장: {labels_path} (shape={labels_full.shape})")

    print("[08] 완료.")


if __name__ == "__main__":
    main()


