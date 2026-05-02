from __future__ import annotations

from dataclasses import dataclass
import os
import random
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from .clustering import (
    agglom_grid,
    bootstrap_stability,
    dbscan_sweep,
    hdbscan_try,
    kmeans_grid,
    meanshift_try,
    optics_try,
)
from .metrics import (
    baseline_metric_for_feature,
    ch_db_on,
    eval_silhouette,
    projection_quality,
    silhouette_on,
)
from .spaces import build_cluster_space_candidates


@dataclass
class SweepOutcome:
    labels: np.ndarray
    row_info: Dict[str, Any]
    best_meta: Dict[str, Any]
    silhouette: float
    best_score: float
    eval_metric: str
    trial_cost: int
    row_extras: Dict[str, Any]


@dataclass(frozen=True)
class AlgoSpec:
    name: str
    evaluate: Callable[[np.ndarray, str], Optional[SweepOutcome]]


def seed_everything(seed: int) -> None:
    try:
        random.seed(seed)
    except Exception:
        pass
    try:
        np.random.seed(seed)
    except Exception:
        pass


def _build_row_common(
    X_base: np.ndarray,
    X_space: np.ndarray,
    labels: np.ndarray,
    eval_metric: str,
    baseline_metric: str,
    proj_quality: Dict[str, float],
) -> Dict[str, float]:
    sil_proj = silhouette_on(X_space, labels, eval_metric)
    sil_raw = silhouette_on(X_base, labels, baseline_metric)
    ch_proj, db_proj = ch_db_on(X_space, labels)
    ch_raw, db_raw = ch_db_on(X_base, labels)
    return {
        "silhouette_proj": float(sil_proj),
        "silhouette_raw": float(sil_raw),
        "calinski_harabasz_proj": float(ch_proj),
        "calinski_harabasz_raw": float(ch_raw),
        "davies_bouldin_proj": float(db_proj),
        "davies_bouldin_raw": float(db_raw),
        "trustworthiness_k": float(proj_quality.get("trustworthiness_k", float("nan"))),
        "continuity_k": float(proj_quality.get("continuity_k", float("nan"))),
        "knn_overlap_k": float(proj_quality.get("knn_overlap_k", float("nan"))),
    }


def _attach_bootstrap(
    row_common: Dict[str, Any],
    X_space: np.ndarray,
    labels: np.ndarray,
    algo: str,
    meta: Dict[str, Any],
    metric: str,
    reps: int,
) -> Dict[str, Any]:
    row = dict(row_common)
    if reps <= 0:
        return row
    stab = bootstrap_stability(X_space, labels, algo, meta, metric=metric, reps=reps)
    row.update(
        {
            "ari_boot_mean": stab.get("ari_mean"),
            "ari_boot_std": stab.get("ari_std"),
            "nmi_boot_mean": stab.get("nmi_mean"),
            "nmi_boot_std": stab.get("nmi_std"),
            "bootstrap_reps": int(stab.get("reps", reps)),
        }
    )
    return row


def _cluster_count(labels: np.ndarray) -> int:
    return int(np.unique(labels[labels >= 0]).size)


def _strip_used_flag(info: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in info.items() if key != "used"}


def _update_best(
    best_global: Dict[str, Any],
    best_per_algo: Dict[str, Dict[str, Any]],
    algo: str,
    score: float,
    labels: np.ndarray,
    space_name: str,
    meta: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    if np.isfinite(score):
        current = best_per_algo.get(algo, {"score": float("-inf")})
        if score > current.get("score", float("-inf")):
            best_per_algo[algo] = {
                "score": float(score),
                "space": space_name,
                "labels": labels,
                "meta": meta,
            }
        if score > best_global["score"] and (labels >= 0).all():
            best_global = {
                "score": float(score),
                "space": space_name,
                "algo": algo,
                "labels": labels,
                "meta": meta,
            }
    return best_global, best_per_algo


def _evaluate_kmeans(X_space: np.ndarray, metric: str, k_list: List[int]) -> SweepOutcome:
    labels, info = kmeans_grid(X_space, metric, k_list)
    try:
        silhouette = float(info.get("raw_sil", float("nan")))
    except Exception:
        silhouette = float("nan")
    if not np.isfinite(silhouette):
        silhouette = eval_silhouette(X_space, labels, "euclidean")
    return SweepOutcome(
        labels=labels,
        row_info=info,
        best_meta=info,
        silhouette=silhouette,
        best_score=silhouette,
        eval_metric=metric,
        trial_cost=len(k_list),
        row_extras={},
    )


def _evaluate_dbscan(X_space: np.ndarray, metric: str, _k_list: List[int]) -> SweepOutcome:
    labels, info = dbscan_sweep(X_space, metric)
    silhouette = eval_silhouette(X_space, labels, metric)
    return SweepOutcome(
        labels=labels,
        row_info=info,
        best_meta=info,
        silhouette=silhouette,
        best_score=silhouette,
        eval_metric=metric,
        trial_cost=1,
        row_extras={"k": _cluster_count(labels)},
    )


def _evaluate_hdbscan(X_space: np.ndarray, metric: str, _k_list: List[int]) -> Optional[SweepOutcome]:
    labels, info = hdbscan_try(X_space, metric)
    if not info.get("used", False) or labels is None:
        return None
    silhouette = eval_silhouette(X_space, labels, metric)
    return SweepOutcome(
        labels=labels,
        row_info=info,
        best_meta=info,
        silhouette=silhouette,
        best_score=silhouette,
        eval_metric=metric,
        trial_cost=1,
        row_extras={"k": _cluster_count(labels)},
    )


def _evaluate_agglomerative(X_space: np.ndarray, metric: str, k_list: List[int]) -> SweepOutcome:
    labels, info = agglom_grid(X_space, metric, k_list)
    eval_metric = "euclidean" if str(info.get("linkage") or "").lower() == "ward" else metric
    silhouette = eval_silhouette(X_space, labels, eval_metric)
    return SweepOutcome(
        labels=labels,
        row_info=info,
        best_meta=info,
        silhouette=silhouette,
        best_score=silhouette,
        eval_metric=eval_metric,
        trial_cost=len(k_list) * 2,
        row_extras={},
    )


def _evaluate_optics(X_space: np.ndarray, metric: str, _k_list: List[int]) -> Optional[SweepOutcome]:
    labels, info = optics_try(X_space, metric)
    if not info.get("used", False) or labels is None:
        return None
    meta = _strip_used_flag(info)
    score = float(meta["score"])
    return SweepOutcome(
        labels=labels,
        row_info=meta,
        best_meta=meta,
        silhouette=score,
        best_score=score,
        eval_metric=metric,
        trial_cost=1,
        row_extras={"k": _cluster_count(labels)},
    )


def _evaluate_meanshift(X_space: np.ndarray, metric: str, _k_list: List[int]) -> Optional[SweepOutcome]:
    labels, info = meanshift_try(X_space, metric)
    if not info.get("used", False) or labels is None:
        return None
    meta = _strip_used_flag(info)
    score = float(meta["score"])
    return SweepOutcome(
        labels=labels,
        row_info=meta,
        best_meta=meta,
        silhouette=score,
        best_score=score,
        eval_metric=metric,
        trial_cost=1,
        row_extras={"k": _cluster_count(labels)},
    )


def _build_algo_registry(k_list: List[int]) -> List[AlgoSpec]:
    return [
        AlgoSpec(name="kmeans", evaluate=lambda X_space, metric: _evaluate_kmeans(X_space, metric, k_list)),
        AlgoSpec(name="dbscan", evaluate=lambda X_space, metric: _evaluate_dbscan(X_space, metric, k_list)),
        AlgoSpec(name="hdbscan", evaluate=lambda X_space, metric: _evaluate_hdbscan(X_space, metric, k_list)),
        AlgoSpec(name="agglomerative", evaluate=lambda X_space, metric: _evaluate_agglomerative(X_space, metric, k_list)),
        AlgoSpec(name="optics", evaluate=lambda X_space, metric: _evaluate_optics(X_space, metric, k_list)),
        AlgoSpec(name="meanshift", evaluate=lambda X_space, metric: _evaluate_meanshift(X_space, metric, k_list)),
    ]


def run_sweep(
    X: np.ndarray,
    X_base: np.ndarray,
    feature_key: str,
    k_list: List[int],
    max_trials: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Dict[str, Any]], Dict[str, np.ndarray], Dict[str, str]]:
    spaces = build_cluster_space_candidates(X, feature_key)
    if not spaces:
        spaces = [("raw", X, "euclidean")]

    space_map = {name: arr for name, arr, _metric in spaces}
    metric_map = {name: metric for name, _arr, metric in spaces}
    baseline_metric = baseline_metric_for_feature(feature_key)
    neighbor_k = int(os.getenv("PHASEC_NEIGHBOR_K", "10"))
    bootstrap_reps = int(os.getenv("PHASEC_BOOTSTRAP_REPS", "0") or 0)

    projq_by_space: Dict[str, Dict[str, float]] = {}
    for space_name, X_space, metric in spaces:
        try:
            projq_by_space[space_name] = projection_quality(X_base, X_space, neighbor_k, baseline_metric, metric)
        except Exception:
            projq_by_space[space_name] = {
                "trustworthiness_k": float("nan"),
                "continuity_k": float("nan"),
                "knn_overlap_k": float("nan"),
            }

    rows: List[Dict[str, Any]] = []
    best_global: Dict[str, Any] = {
        "score": float("-inf"),
        "space": None,
        "algo": None,
        "labels": None,
        "meta": {},
    }
    best_per_algo: Dict[str, Dict[str, Any]] = {}
    trials = 0
    algo_registry = _build_algo_registry(k_list)

    for space_name, X_space, metric in spaces:
        print(f"[09] Space: {space_name} metric={metric} shape={X_space.shape}")
        proj_quality = projq_by_space.get(space_name, {})
        for spec in algo_registry:
            outcome = spec.evaluate(X_space, metric)
            if outcome is None:
                continue

            row_common = _build_row_common(
                X_base,
                X_space,
                outcome.labels,
                outcome.eval_metric,
                baseline_metric,
                proj_quality,
            )
            row_common = _attach_bootstrap(
                row_common,
                X_space,
                outcome.labels,
                spec.name,
                outcome.best_meta,
                metric,
                bootstrap_reps,
            )
            rows.append(
                {
                    "space": space_name,
                    "algo": spec.name,
                    "metric": metric,
                    **outcome.row_info,
                    **row_common,
                    "silhouette": outcome.silhouette,
                    **outcome.row_extras,
                }
            )
            trials += outcome.trial_cost
            best_global, best_per_algo = _update_best(
                best_global,
                best_per_algo,
                spec.name,
                outcome.best_score,
                outcome.labels,
                space_name,
                outcome.best_meta,
            )
            if trials >= max_trials:
                break
        if trials >= max_trials:
            break

    return rows, best_global, best_per_algo, space_map, metric_map
