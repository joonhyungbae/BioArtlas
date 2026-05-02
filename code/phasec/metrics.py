from __future__ import annotations

from typing import Dict, Tuple

import numpy as np


def eval_silhouette(X: np.ndarray, labels: np.ndarray, metric: str) -> float:
    try:
        from sklearn.metrics import silhouette_score

        valid = labels >= 0
        labs = np.unique(labels[valid])
        if labs.size < 2:
            return float("nan")
        return float(silhouette_score(X[valid], labels[valid], metric=metric))
    except Exception:
        return float("nan")


def baseline_metric_for_feature(feature_key: str) -> str:
    try:
        key = (feature_key or "").strip().lower()
        if key in ("tfidf_counts_l2", "tfidf_counts_bm25_l2", "tfidf_onehot_l2"):
            return "cosine"
    except Exception:
        pass
    return "euclidean"


def valid_cluster_mask(labels: np.ndarray) -> np.ndarray:
    try:
        valid = labels >= 0
        if not np.any(valid):
            return np.zeros_like(labels, dtype=bool)
        labs = np.unique(labels[valid])
        if labs.size < 2:
            return np.zeros_like(labels, dtype=bool)
        return valid
    except Exception:
        return np.zeros_like(labels, dtype=bool)


def silhouette_on(X: np.ndarray, labels: np.ndarray, metric: str) -> float:
    try:
        valid = valid_cluster_mask(labels)
        if not np.any(valid):
            return float("nan")
        from sklearn.metrics import silhouette_score

        return float(silhouette_score(X[valid], labels[valid], metric=metric))
    except Exception:
        return float("nan")


def ch_db_on(X: np.ndarray, labels: np.ndarray) -> Tuple[float, float]:
    try:
        from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score

        valid = valid_cluster_mask(labels)
        if not np.any(valid):
            return float("nan"), float("nan")
        return (
            float(calinski_harabasz_score(X[valid], labels[valid])),
            float(davies_bouldin_score(X[valid], labels[valid])),
        )
    except Exception:
        return float("nan"), float("nan")


def knn_indices(X: np.ndarray, k: int, metric: str, full: bool = False) -> np.ndarray:
    n = X.shape[0]
    if n == 0:
        return np.zeros((0, 0), dtype=int)
    if k <= 0:
        k = 1
    try:
        from sklearn.neighbors import NearestNeighbors

        n_neighbors = max(2, (n - 1) if full else min(n, k + 1))
        nn = NearestNeighbors(
            n_neighbors=n_neighbors,
            metric=(metric if metric in ("euclidean", "cosine", "manhattan") else "euclidean"),
        )
        nn.fit(X)
        _, idx = nn.kneighbors(X)
        return idx[:, 1:]
    except Exception:
        try:
            from sklearn.metrics import pairwise_distances

            D = pairwise_distances(X, metric="euclidean")
            np.fill_diagonal(D, np.inf)
            idx = np.argsort(D, axis=1)
            return idx[:, : (n - 1) if full else min(n - 1, k)]
        except Exception:
            return np.zeros((n, 0), dtype=int)


def knn_overlap(idx_high: np.ndarray, idx_low: np.ndarray, k: int) -> float:
    try:
        if k <= 0:
            return float("nan")
        n = idx_high.shape[0]
        k_h = min(k, idx_high.shape[1])
        k_l = min(k, idx_low.shape[1])
        if k_h == 0 or k_l == 0:
            return float("nan")
        total = 0.0
        for i in range(n):
            total += len(set(idx_high[i, :k_h].tolist()).intersection(idx_low[i, :k_l].tolist())) / float(k)
        return float(total / max(1, n))
    except Exception:
        return float("nan")


def continuity(idx_high_full: np.ndarray, idx_low_full: np.ndarray, k: int) -> float:
    try:
        n = idx_high_full.shape[0]
        if n == 0 or k <= 0 or idx_low_full.shape[0] != n:
            return float("nan")
        denom = n * k * (2 * n - 3 * k - 1)
        if denom <= 0:
            return float("nan")
        norm = 2.0 / float(denom)
        total = 0.0
        for i in range(n):
            high_k = set(idx_high_full[i, : min(k, idx_high_full.shape[1])].tolist())
            low_k = set(idx_low_full[i, : min(k, idx_low_full.shape[1])].tolist())
            missing = high_k.difference(low_k)
            if not missing:
                continue
            ranks_low = {int(j): (ri + 1) for ri, j in enumerate(idx_low_full[i].tolist())}
            for j in missing:
                total += max(0, int(ranks_low.get(int(j), n)) - k)
        return float(1.0 - norm * total)
    except Exception:
        return float("nan")


def projection_quality(
    X_high: np.ndarray,
    X_low: np.ndarray,
    k: int,
    metric_high: str,
    metric_low: str,
) -> Dict[str, float]:
    out = {
        "trustworthiness_k": float("nan"),
        "continuity_k": float("nan"),
        "knn_overlap_k": float("nan"),
    }
    try:
        try:
            from sklearn.manifold import trustworthiness  # type: ignore

            out["trustworthiness_k"] = float(
                trustworthiness(
                    X_high,
                    X_low,
                    n_neighbors=int(k),
                    metric=(metric_high if metric_high in ("euclidean", "cosine", "manhattan") else "euclidean"),
                )
            )
        except Exception:
            out["trustworthiness_k"] = float("nan")
        idx_h_k = knn_indices(X_high, k=int(k), metric=metric_high, full=False)
        idx_l_k = knn_indices(X_low, k=int(k), metric=metric_low, full=False)
        out["knn_overlap_k"] = knn_overlap(idx_h_k, idx_l_k, int(k))
        idx_h_full = knn_indices(X_high, k=int(k), metric=metric_high, full=True)
        idx_l_full = knn_indices(X_low, k=int(k), metric=metric_low, full=True)
        out["continuity_k"] = continuity(idx_h_full, idx_l_full, int(k))
    except Exception:
        pass
    return out


def compute_ari_nmi(y_true: np.ndarray, y_pred: np.ndarray) -> Tuple[float, float]:
    try:
        from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

        mask = (y_true >= 0) & (y_pred >= 0)
        if mask.sum() < 2:
            return float("nan"), float("nan")
        return (
            float(adjusted_rand_score(y_true[mask], y_pred[mask])),
            float(normalized_mutual_info_score(y_true[mask], y_pred[mask])),
        )
    except Exception:
        return float("nan"), float("nan")

