"""
Utilities for SRMVA-like workflows: embeddings I/O, feature building,
kernel construction/combination, spectral/k-means clustering, metrics,
bootstrapping, consensus matrix, and PAC score.

Note on saving: helper functions ensure that directories exist when
writing figures/tables to disk.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import os
import numpy as np

EPS = 1e-12


def _ensure_parent_dir(path: str) -> None:
    """Create parent directory of a file path if not present."""
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def save_figure(fig, out_path: str, dpi: int = 150, bbox_inches: str | None = "tight") -> None:
    """Save a matplotlib figure ensuring its directory exists."""
    _ensure_parent_dir(out_path)
    fig.savefig(out_path, dpi=dpi, bbox_inches=bbox_inches)


def save_dataframe_csv(df, out_path: str, index: bool = False) -> None:
    """Save a pandas DataFrame to CSV ensuring its directory exists."""
    _ensure_parent_dir(out_path)
    df.to_csv(out_path, index=index)


def load_embeddings(npz_path: str) -> Dict[str, np.ndarray]:
    """Load axis-wise embeddings from an .npz file.

    Requirements:
    - Each axis array must be 2D with shape (N, 1024)
    - All axes must share the same N

    Returns a dict mapping axis name -> float32 array (N, 1024).
    """
    if not os.path.exists(npz_path):
        raise FileNotFoundError(f"Embeddings file not found: {npz_path}")

    with np.load(npz_path, allow_pickle=False) as data:
        if len(data.files) == 0:
            raise ValueError("No arrays found in the provided .npz file")

        axes: Dict[str, np.ndarray] = {}
        expected_n: int | None = None
        for key in data.files:
            arr = np.asarray(data[key])
            if arr.ndim != 2:
                raise ValueError(f"Embedding '{key}' must be 2D, got shape {arr.shape}")
            n, d = arr.shape
            if d != 1024:
                raise ValueError(
                    f"Embedding '{key}' must have 1024 dims, got {d}"
                )
            if expected_n is None:
                expected_n = n
            elif n != expected_n:
                raise ValueError(
                    f"All axes must share same N; axis '{key}' has N={n}, expected {expected_n}"
                )
            axes[key] = arr.astype(np.float32, copy=False)

    return axes


def l2_normalize_rows(X: np.ndarray) -> np.ndarray:
    """Row-wise L2 normalize a 2D array. Zero rows remain zero.

    Returns a float32 array with the same shape.
    """
    if X.ndim != 2:
        raise ValueError(f"X must be 2D, got shape {X.shape}")
    X = X.astype(np.float32, copy=False)
    # Sanitize non-finite values to prevent NaNs from propagating
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    # Avoid division by zero; keep zero rows as zeros
    scale = 1.0 / np.maximum(norms, EPS)
    X_norm = X * scale
    # Re-zero rows that were effectively zero to begin with
    zero_mask = np.logical_or(~np.isfinite(norms.squeeze(1)), norms.squeeze(1) < EPS)
    if np.any(zero_mask):
        X_norm[zero_mask] = 0.0
    return X_norm


def build_concat_features(axes_embeddings: Dict[str, np.ndarray]) -> np.ndarray:
    """Concatenate 13 axis embeddings along feature dimension and L2-normalize rows.

    Expects values with shape (N, 1024). Concatenation yields (N, 13*1024).
    Axis order is deterministic via lexicographic sort of axis names.
    """
    if not axes_embeddings:
        raise ValueError("axes_embeddings is empty")

    # Deterministic axis order
    axis_names = sorted(axes_embeddings.keys())
    arrays: List[np.ndarray] = [axes_embeddings[name] for name in axis_names]

    # Validate shapes and consistent N
    n_list = [arr.shape[0] for arr in arrays]
    d_list = [arr.shape[1] for arr in arrays]
    if len(set(n_list)) != 1:
        raise ValueError(f"All axes must share same N; got Ns={set(n_list)}")
    if not all(d == 1024 for d in d_list):
        raise ValueError(f"All axes must be 1024D; got dims={set(d_list)}")

    X_concat = np.concatenate([arr.astype(np.float32, copy=False) for arr in arrays], axis=1)
    X_concat = l2_normalize_rows(X_concat)
    return X_concat


def build_axis_kernels(
    axes_embeddings: Dict[str, np.ndarray],
    trace_normalize: bool = True,
) -> Dict[str, np.ndarray]:
    """Build per-axis linear kernels K = E @ E.T.

    If trace_normalize is True, each kernel is divided by its trace
    (with epsilon protection) so traces are comparable across axes.
    """
    if not axes_embeddings:
        raise ValueError("axes_embeddings is empty")

    kernels: Dict[str, np.ndarray] = {}
    for axis_name, E in axes_embeddings.items():
        if E.ndim != 2 or E.shape[1] != 1024:
            raise ValueError(
                f"Axis '{axis_name}' must be (N, 1024); got {E.shape}"
            )
        E = E.astype(np.float32, copy=False)
        K = E @ E.T  # (N, N)
        # Symmetrize to counter tiny numerical asymmetries
        K = 0.5 * (K + K.T)
        # Sanitize any potential non-finite values
        K = np.nan_to_num(K, nan=0.0, posinf=0.0, neginf=0.0)
        if trace_normalize:
            tr = float(np.trace(K))
            K = K / max(tr, EPS)
        kernels[axis_name] = K.astype(np.float32, copy=False)

    return kernels


def combine_kernels_average(K_dict: Dict[str, np.ndarray]) -> np.ndarray:
    """Average-combine multiple kernels of identical shape."""
    if not K_dict:
        raise ValueError("K_dict is empty")
    kernels = list(K_dict.values())
    shapes = {K.shape for K in kernels}
    if len(shapes) != 1:
        raise ValueError(f"All kernels must have the same shape; got {shapes}")
    K_sum = np.zeros_like(kernels[0], dtype=np.float64)
    for K in kernels:
        K_sum += K.astype(np.float64, copy=False)
    K_avg = (K_sum / len(kernels)).astype(np.float32, copy=False)
    # Symmetrize
    K_avg = 0.5 * (K_avg + K_avg.T)
    # Ensure finiteness
    K_avg = np.nan_to_num(K_avg, nan=0.0, posinf=0.0, neginf=0.0)
    return K_avg.astype(np.float32, copy=False)


def _topk_eigvals(K: np.ndarray, k: int) -> np.ndarray:
    """Compute top-k eigenvalues (desc) of a symmetric matrix using eigh/eigsh."""
    n = K.shape[0]
    k = max(1, min(k, n))
    try:
        # Prefer sparse solver for efficiency if available
        from scipy.sparse.linalg import eigsh  # type: ignore

        vals = eigsh(K, k=k, which="LA", return_eigenvectors=False)
        vals = np.sort(vals)[::-1]
        return vals
    except Exception:
        vals = np.linalg.eigh(K)[0]
        vals = vals[::-1]
        return vals[:k]


def eigengap_from_kernel(K: np.ndarray, top_k: int = 30) -> Tuple[np.ndarray, int]:
    """Compute sorted eigenvalues and estimate k via largest eigengap among top_k.

    Returns (evals_sorted_desc_full, k_hat).
    """
    if K.ndim != 2 or K.shape[0] != K.shape[1]:
        raise ValueError("K must be a square matrix")
    # Symmetrize
    K = 0.5 * (K + K.T)
    n = K.shape[0]
    # Full spectrum for return; use eigh for symmetric matrices
    evals = np.linalg.eigh(K)[0][::-1]  # descending

    k_cap = max(2, min(top_k, n))
    leading = evals[:k_cap]
    if leading.size < 2:
        return evals, 1
    gaps = leading[:-1] - leading[1:]
    k_hat = int(np.argmax(gaps)) + 1
    return evals, k_hat


def _topk_eigvecs(K: np.ndarray, k: int) -> np.ndarray:
    """Top-k eigenvectors (columns) corresponding to largest eigenvalues.

    Returns array of shape (N, k).
    """
    n = K.shape[0]
    k = max(1, min(k, n))
    # Symmetrize for stability and sanitize
    K = 0.5 * (K + K.T)
    K = np.nan_to_num(K, nan=0.0, posinf=0.0, neginf=0.0)
    try:
        from scipy.sparse.linalg import eigsh  # type: ignore

        vals, vecs = eigsh(K, k=k, which="LA")
        # eigsh returns eigenvalues in ascending order; sort descending
        idx = np.argsort(vals)[::-1]
        vecs = vecs[:, idx]
        return vecs.astype(np.float32, copy=False)
    except Exception:
        vals, vecs = np.linalg.eigh(K)
        vecs = vecs[:, ::-1]  # match descending order
        return vecs[:, :k].astype(np.float32, copy=False)


def spectral_labels_from_kernel(K: np.ndarray, K_clusters: int, seed: int) -> np.ndarray:
    """Spectral clustering on a precomputed kernel (affinity) matrix.

    Uses top-K eigenvectors of the kernel, row-normalizes them, and applies k-means.
    """
    if K.ndim != 2 or K.shape[0] != K.shape[1]:
        raise ValueError("K must be a square matrix")
    if K_clusters < 1:
        raise ValueError("K_clusters must be >= 1")
    n = K.shape[0]
    if K_clusters > n:
        raise ValueError("K_clusters cannot exceed number of samples")

    eigvecs = _topk_eigvecs(K, K_clusters)
    Y = l2_normalize_rows(eigvecs)
    # Add tiny jitter to avoid exact duplicates/degeneracy in k-means space
    rng = np.random.RandomState(seed)
    Y = Y + rng.normal(loc=0.0, scale=1e-8, size=Y.shape).astype(np.float32)

    # KMeans on spectral embedding
    try:
        from sklearn.cluster import KMeans  # type: ignore

        km = KMeans(n_clusters=K_clusters, random_state=seed, n_init=20)
        labels = km.fit_predict(Y)
    except Exception as exc:  # pragma: no cover - sklearn may be unavailable
        raise ImportError(
            "spectral_labels_from_kernel requires scikit-learn. Install with 'pip install scikit-learn'."
        ) from exc

    return labels.astype(np.int64, copy=False)


def kmeans_labels_from_features(
    X: np.ndarray, K_clusters: int, seed: int, n_init: int
) -> np.ndarray:
    """Cluster features with k-means and return labels."""
    if X.ndim != 2:
        raise ValueError(f"X must be 2D, got shape {X.shape}")
    if K_clusters < 1:
        raise ValueError("K_clusters must be >= 1")
    if K_clusters > X.shape[0]:
        raise ValueError("K_clusters cannot exceed number of samples")
    # Sanitize and optionally jitter to improve numerical stability
    X_sanitized = np.nan_to_num(X.astype(np.float32, copy=False), nan=0.0, posinf=0.0, neginf=0.0)
    rng = np.random.RandomState(seed)
    jitter_scales = [0.0, 1e-8, 1e-6]
    last_exc: Exception | None = None
    try:
        from sklearn.cluster import KMeans  # type: ignore

        for scale in jitter_scales:
            X_work = X_sanitized
            if scale > 0.0:
                X_work = X_work + rng.normal(loc=0.0, scale=scale, size=X_work.shape).astype(np.float32)
            try:
                km = KMeans(n_clusters=K_clusters, random_state=seed, n_init=int(n_init))
                labels = km.fit_predict(X_work)
                # Validate finiteness of centers and label count
                if not np.all(np.isfinite(km.cluster_centers_)):
                    last_exc = RuntimeError("Non-finite cluster centers encountered")
                    continue
                if np.unique(labels).size < K_clusters:
                    # rare degeneracy; retry with higher jitter
                    last_exc = RuntimeError("Fewer unique labels than clusters")
                    continue
                return labels.astype(np.int64, copy=False)
            except Exception as exc_inner:
                last_exc = exc_inner
                continue
        # If all attempts failed, raise the last exception
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("KMeans failed without exception but no labels were produced")
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "kmeans_labels_from_features requires scikit-learn. Install with 'pip install scikit-learn'."
        ) from exc


def internal_metrics(X_for_metrics: np.ndarray, labels: np.ndarray) -> Dict[str, float]:
    """Compute internal clustering metrics.

    - silhouette (cosine distance)
    - Calinski-Harabasz index
    - Davies-Bouldin index
    Returns dict with NaN where a metric is undefined.
    """
    if X_for_metrics.ndim != 2:
        raise ValueError("X_for_metrics must be 2D")
    if labels.ndim != 1 or labels.shape[0] != X_for_metrics.shape[0]:
        raise ValueError("labels must be 1D and match number of samples")

    try:
        from sklearn.metrics import (
            silhouette_score,
            calinski_harabasz_score,
            davies_bouldin_score,
        )  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "internal_metrics requires scikit-learn. Install with 'pip install scikit-learn'."
        ) from exc

    unique = np.unique(labels)
    num_clusters = unique.size
    metrics: Dict[str, float] = {
        "silhouette_cosine": float("nan"),
        "calinski_harabasz": float("nan"),
        "davies_bouldin": float("nan"),
    }

    if 1 < num_clusters < X_for_metrics.shape[0]:
        # Sanitize features for metric computations
        X_sanitized = np.nan_to_num(
            X_for_metrics.astype(np.float32, copy=False),
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )
        try:
            metrics["silhouette_cosine"] = float(
                silhouette_score(X_sanitized, labels, metric="cosine")
            )
        except Exception:
            metrics["silhouette_cosine"] = float("nan")

        try:
            metrics["calinski_harabasz"] = float(
                calinski_harabasz_score(X_sanitized, labels)
            )
        except Exception:
            metrics["calinski_harabasz"] = float("nan")

        try:
            metrics["davies_bouldin"] = float(
                davies_bouldin_score(X_sanitized, labels)
            )
        except Exception:
            metrics["davies_bouldin"] = float("nan")

    return metrics


def bootstrap_sample_idx(N: int, seed: int) -> np.ndarray:
    """Return bootstrap sample indices (size N with replacement)."""
    if N <= 0:
        raise ValueError("N must be positive")
    rng = np.random.RandomState(seed)
    idx = rng.randint(0, N, size=N, dtype=np.int64)
    return idx


def consensus_matrix(list_of_label_arrays: List[np.ndarray]) -> np.ndarray:
    """Compute consensus (co-association) matrix from multiple labelings.

    Returns an (N, N) matrix with values in [0, 1], diagonal = 1.
    """
    if not list_of_label_arrays:
        raise ValueError("list_of_label_arrays is empty")
    Ns = {len(arr) for arr in list_of_label_arrays}
    if len(Ns) != 1:
        raise ValueError(f"All label arrays must share same length; got {Ns}")
    N = list(Ns)[0]
    C = np.zeros((N, N), dtype=np.float64)
    for labels in list_of_label_arrays:
        labels = np.asarray(labels)
        if labels.ndim != 1 or labels.shape[0] != N:
            raise ValueError("Each labels array must be 1D of length N")
        # Co-clustering indicator matrix
        eq = (labels[:, None] == labels[None, :])
        C += eq.astype(np.float64, copy=False)
    C /= len(list_of_label_arrays)
    # Enforce symmetry and ones on diagonal
    C = 0.5 * (C + C.T)
    np.fill_diagonal(C, 1.0)
    return C.astype(np.float32, copy=False)


def pac_score(consensus_mat: np.ndarray, low: float = 0.4, high: float = 0.8) -> float:
    """Compute PAC score: proportion of (i<j) pairs with consensus in (low, high).

    Lower PAC indicates more unambiguous consensus clustering.
    """
    if consensus_mat.ndim != 2 or consensus_mat.shape[0] != consensus_mat.shape[1]:
        raise ValueError("consensus_mat must be a square matrix")
    if not (0.0 <= low < high <= 1.0):
        raise ValueError("Require 0 <= low < high <= 1")

    N = consensus_mat.shape[0]
    iu = np.triu_indices(N, k=1)
    vals = consensus_mat[iu]
    ambiguous = np.logical_and(vals > low, vals < high)
    pac = float(np.sum(ambiguous)) / float(vals.size) if vals.size > 0 else float("nan")
    return pac


__all__ = [
    "load_embeddings",
    "l2_normalize_rows",
    "build_concat_features",
    "build_axis_kernels",
    "combine_kernels_average",
    "eigengap_from_kernel",
    "spectral_labels_from_kernel",
    "kmeans_labels_from_features",
    "internal_metrics",
    "bootstrap_sample_idx",
    "consensus_matrix",
    "pac_score",
    # helpers
    "save_figure",
    "save_dataframe_csv",
]


