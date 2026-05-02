from __future__ import annotations

import os
from math import isfinite
from typing import Any, Dict, Optional, Tuple

import numpy as np

from .cluster_common import k_preference_bonus
from .metrics import eval_silhouette


def _density_objective(raw_sil: float, used_k: int, noise_ratio: float, k_min: int, noise_max: float) -> float:
    score = raw_sil if isfinite(raw_sil) else -1e9
    if used_k < k_min:
        score -= 0.05 * (k_min - used_k)
    if noise_ratio > noise_max:
        score -= 0.05 * (noise_ratio - noise_max) * 10
    score += k_preference_bonus(used_k=used_k, k_value=None)
    return score


def dbscan_sweep(X: np.ndarray, base_metric: str) -> Tuple[np.ndarray, Dict[str, Any]]:
    from sklearn.cluster import DBSCAN

    k_min = int(os.getenv("PHASEC_TARGET_K_MIN", "5"))
    noise_max = float(os.getenv("PHASEC_NOISE_MAX", "0.6"))

    def _knee_epsilon(Xin: np.ndarray, k: int = 10, metric: str = "euclidean") -> Optional[float]:
        try:
            from sklearn.neighbors import NearestNeighbors

            nbrs = NearestNeighbors(
                n_neighbors=k,
                metric=metric if metric in ("euclidean", "cosine", "manhattan") else "euclidean",
            ).fit(Xin)
            dist, _ = nbrs.kneighbors(Xin)
            kth = np.sort(dist[:, -1])
            x = np.arange(len(kth))
            p1 = np.array([x[0], kth[0]], dtype=float)
            p2 = np.array([x[-1], kth[-1]], dtype=float)
            v = p2 - p1
            v /= np.linalg.norm(v) + 1e-12
            diffs = np.cross(v, np.vstack([x, kth]).T - p1)
            return float(kth[int(np.argmax(np.abs(diffs)))])
        except Exception:
            return None

    eps0 = _knee_epsilon(X, k=10, metric=base_metric)
    if eps0 is None or not np.isfinite(eps0):
        eps0 = 1.0

    best: Dict[str, Any] = {"score": float("-inf"), "labels": None, "eps": eps0, "min_samples": 10}
    for eps_mult in (0.4, 0.5, 0.6, 0.75, 0.9, 1.0, 1.1, 1.25):
        eps = max(1e-3, eps0 * eps_mult)
        for min_samples in (3, 4, 5, 8, 10, 12, 15):
            labels = DBSCAN(eps=eps, min_samples=min_samples, metric=base_metric).fit_predict(X)
            raw_sil = eval_silhouette(X, labels, metric=base_metric)
            used = int(np.unique(labels[labels >= 0]).size)
            noise_ratio = float((labels < 0).sum()) / len(labels)
            score = _density_objective(raw_sil, used, noise_ratio, k_min, noise_max)
            key = (score, used, -noise_ratio)
            cur = (
                best["score"],
                np.unique(best["labels"][best["labels"] >= 0]).size if isinstance(best["labels"], np.ndarray) else -1,
                float("-inf"),
            )
            if key > cur:
                best = {
                    "score": score,
                    "labels": labels,
                    "eps": eps,
                    "min_samples": min_samples,
                    "raw_sil": raw_sil,
                    "used_k": used,
                    "noise_ratio": noise_ratio,
                }

    labels = best["labels"] if best["labels"] is not None else np.full((X.shape[0],), -1)
    return labels, best


def hdbscan_try(X: np.ndarray, metric: str) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
    try:
        import hdbscan  # type: ignore
    except Exception:
        return None, {"used": False}

    k_min = int(os.getenv("PHASEC_TARGET_K_MIN", "5"))
    noise_max = float(os.getenv("PHASEC_NOISE_MAX", "0.6"))
    best: Dict[str, Any] = {"score": float("-inf"), "labels": None, "min_cluster_size": None}

    for min_cluster_size in (5, 6, 8, 10, 12, 15, 20):
        for min_samples in (None, 1, 5):
            for selection in ("eom", "leaf"):
                try:
                    kwargs = {
                        "min_cluster_size": min_cluster_size,
                        "metric": metric,
                        "cluster_selection_method": selection,
                    }
                    if min_samples is not None:
                        kwargs["min_samples"] = min_samples
                    labels = hdbscan.HDBSCAN(**kwargs).fit_predict(X)
                    raw_sil = eval_silhouette(X, labels, metric)
                    used = int(np.unique(labels[labels >= 0]).size)
                    noise_ratio = float((labels < 0).sum()) / len(labels)
                    score = _density_objective(raw_sil, used, noise_ratio, k_min, noise_max)
                    if score > best["score"]:
                        best = {
                            "score": score,
                            "labels": labels,
                            "min_cluster_size": min_cluster_size,
                            "min_samples": (min_samples if min_samples is not None else -1),
                            "selection": selection,
                            "raw_sil": raw_sil,
                            "used_k": used,
                            "noise_ratio": noise_ratio,
                        }
                except Exception:
                    continue

    if best["labels"] is None:
        return None, {"used": False}
    info = {"used": True}
    info.update(best)
    return best["labels"], info


def optics_try(X: np.ndarray, metric: str) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
    try:
        from sklearn.cluster import OPTICS
    except Exception:
        return None, {"used": False}

    best: Dict[str, Any] = {"score": float("-inf"), "labels": None}
    k_min = int(os.getenv("PHASEC_TARGET_K_MIN", "5"))
    noise_max = float(os.getenv("PHASEC_NOISE_MAX", "0.6"))

    for min_samples in (3, 5, 8, 10, 12):
        for xi in (0.03, 0.05, 0.1):
            try:
                model = OPTICS(min_samples=min_samples, xi=xi, metric=metric)
                model.fit(X)
                labels = model.labels_
                raw_sil = eval_silhouette(X, labels, metric)
                used = int(np.unique(labels[labels >= 0]).size)
                noise_ratio = float((labels < 0).sum()) / len(labels)
                score = _density_objective(raw_sil, used, noise_ratio, k_min, noise_max)
                if isfinite(score) and score > best["score"]:
                    best = {
                        "score": score,
                        "labels": labels,
                        "min_samples": min_samples,
                        "xi": xi,
                        "raw_sil": raw_sil,
                        "used_k": used,
                        "noise_ratio": noise_ratio,
                    }
            except Exception:
                continue

    if best["labels"] is None:
        return None, {"used": False}
    info = {"used": True}
    info.update({key: value for key, value in best.items() if key != "labels"})
    return best["labels"], info


def meanshift_try(X: np.ndarray, metric: str) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
    if metric != "euclidean":
        return None, {"used": False}
    try:
        from sklearn.cluster import MeanShift, estimate_bandwidth
    except Exception:
        return None, {"used": False}

    try:
        bw0 = estimate_bandwidth(X, quantile=0.2, n_samples=min(500, X.shape[0]))
        bandwidths = [bw0 * ratio for ratio in (0.5, 0.75, 1.0, 1.25, 1.5) if bw0 and bw0 * ratio > 1e-6] or [1.0]
    except Exception:
        bandwidths = [1.0]

    best: Dict[str, Any] = {"score": float("-inf"), "labels": None}
    for bandwidth in bandwidths:
        try:
            model = MeanShift(bandwidth=bandwidth, bin_seeding=True)
            labels = model.fit_predict(X)
            score = eval_silhouette(X, labels, metric)
            if isfinite(score) and score > best["score"]:
                best = {"score": score, "labels": labels, "bandwidth": bandwidth}
        except Exception:
            continue

    if best["labels"] is None:
        return None, {"used": False}
    info = {"used": True}
    info.update({key: value for key, value in best.items() if key != "labels"})
    return best["labels"], info
