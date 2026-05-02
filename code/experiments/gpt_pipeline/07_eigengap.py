#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
07_eigengap.py

역할:
- results/runs/avg_kernel.npy를 로드
- 정규화 라플라시안 L = I - D^{-1/2} K D^{-1/2}의 하위 30개 고유값 계산
- 최대 eigengap을 이용해 k_hat 선택
- 플롯 저장: results/figs/eigengap_avgkernel.pdf
- k_hat CSV 저장: results/tables/eigengap_candidates.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path
import csv
import sys

import numpy as np


BASE_DIR = Path(__file__).resolve().parent


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def compute_normalized_laplacian(K: np.ndarray) -> np.ndarray:
    if K.ndim != 2 or K.shape[0] != K.shape[1]:
        raise ValueError("K must be a square matrix")
    # Symmetrize for numerical stability
    K = 0.5 * (K + K.T)
    # Degree matrix from row sums
    d = K.sum(axis=1)
    # Protect against zeros
    with np.errstate(divide="ignore"):
        inv_sqrt_d = 1.0 / np.sqrt(np.maximum(d, 1e-12))
    inv_sqrt_d[~np.isfinite(inv_sqrt_d)] = 0.0
    Dm12 = np.diag(inv_sqrt_d)
    S = Dm12 @ K @ Dm12
    # Symmetrize again
    S = 0.5 * (S + S.T)
    I = np.eye(K.shape[0], dtype=S.dtype)
    L = I - S
    return L


def smallest_k_eigenvalues(L: np.ndarray, k: int) -> np.ndarray:
    n = L.shape[0]
    k = max(1, min(k, n))
    # Try sparse eigensolver first
    try:
        from scipy.sparse.linalg import eigsh  # type: ignore

        vals = eigsh(L, k=k, which="SA", return_eigenvectors=False)
        vals = np.sort(vals)  # ascending
        return vals
    except Exception:
        vals = np.linalg.eigh(L)[0]
        return np.sort(vals)[:k]


def choose_k_by_eigengap(evals_asc: np.ndarray) -> int:
    # Largest gap among the first k values gives k_hat at gap index+1
    if evals_asc.size < 2:
        return 1
    gaps = evals_asc[1:] - evals_asc[:-1]
    k_hat = int(np.argmax(gaps)) + 1
    return max(1, k_hat)


def plot_eigvals(evals_asc: np.ndarray, k_hat: int, out_path: Path) -> None:
    import matplotlib.pyplot as plt

    x = np.arange(1, len(evals_asc) + 1)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(x, evals_asc, marker="o", linewidth=1)
    ax.set_xlabel("Index (smallest eigenvalues)")
    ax.set_ylabel("Eigenvalue")
    ax.set_title("Normalized Laplacian Eigenvalues (avg kernel)")
    # Highlight k_hat position
    ax.axvline(k_hat, color="red", linestyle="--", linewidth=1)
    ax.text(k_hat + 0.1, float(evals_asc[min(k_hat - 1, len(evals_asc) - 1)]), f"k_hat={k_hat}", color="red")
    ax.grid(True, linestyle=":", alpha=0.5)

    ensure_parent_dir(out_path)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top_k", type=int, default=30, help="Number of smallest eigenvalues to compute")
    args = ap.parse_args()

    avg_kernel_path = (BASE_DIR / "results" / "runs" / "avg_kernel.npy").resolve()
    if not avg_kernel_path.exists():
        print(f"[07] 평균 커널 파일이 없습니다: {avg_kernel_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[07] 로드: {avg_kernel_path}")
    K = np.load(avg_kernel_path)
    print(f"[07] K shape={K.shape}, min/max/mean={K.min():.6f}/{K.max():.6f}/{K.mean():.6f}")

    L = compute_normalized_laplacian(K)
    k = min(args.top_k, L.shape[0])
    evals_asc = smallest_k_eigenvalues(L, k)
    k_hat = choose_k_by_eigengap(evals_asc)

    print(f"[07] Eigenvalues (first {k}, asc): {np.array2string(evals_asc, precision=6, separator=', ')}")
    print(f"[07] k_hat (eigengap): {k_hat}")

    # Save figure
    fig_path = (BASE_DIR / "results" / "figs" / "eigengap_avgkernel.pdf").resolve()
    plot_eigvals(evals_asc, k_hat, fig_path)
    print(f"[07] 플롯 저장: {fig_path}")

    # Save CSV (single column k_hat)
    csv_path = (BASE_DIR / "results" / "tables" / "eigengap_candidates.csv").resolve()
    ensure_parent_dir(csv_path)
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["k_hat"])  # header
        w.writerow([k_hat])
    print(f"[07] CSV 저장: {csv_path}")

    print("[07] 완료.")


if __name__ == "__main__":
    main()


