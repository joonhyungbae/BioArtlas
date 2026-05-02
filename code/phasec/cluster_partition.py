from __future__ import annotations

import os
from math import isfinite
from typing import Any, Dict, List, Tuple

import numpy as np

from .cluster_common import k_preference_bonus
from .metrics import eval_silhouette


def kmeans_grid(X: np.ndarray, metric: str, k_list: List[int]) -> Tuple[np.ndarray, Dict[str, Any]]:
    from sklearn.cluster import KMeans

    k_min = int(os.getenv("PHASEC_TARGET_K_MIN", "5"))
    n_init = int(os.getenv("PHASEC_KMEANS_N_INIT", "100") or 100)
    max_iter = int(os.getenv("PHASEC_KMEANS_MAX_ITER", "500") or 500)
    tol = float(os.getenv("PHASEC_KMEANS_TOL", "1e-4") or 1e-4)
    init_method_env = os.getenv("PHASEC_KMEANS_INIT", "").strip()
    init_methods = [init_method_env] if init_method_env else ["k-means++", "random"]
    algo = os.getenv("PHASEC_KMEANS_ALGO", "lloyd").strip() or "lloyd"
    use_minibatch = os.getenv("PHASEC_KMEANS_MINIBATCH", "false").strip().lower() == "true"
    batch_size = int(os.getenv("PHASEC_KMEANS_BATCH_SIZE", "1024") or 1024)
    spherical_default = "true" if metric == "cosine" else "false"
    env_spherical = os.getenv("PHASEC_KMEANS_SPHERICAL", "").strip().lower()
    env_standard = os.getenv("PHASEC_KMEANS_STANDARDIZE", "").strip().lower()
    spherical_choices = [env_spherical == "true"] if env_spherical in ("true", "false") else [spherical_default == "true", False]
    standardize_choices = [env_standard == "true"] if env_standard in ("true", "false") else [False, True]

    def _prep_for_kmeans(Xin: np.ndarray, standardize: bool, spherical: bool) -> np.ndarray:
        Xk = Xin
        if standardize:
            try:
                from sklearn.preprocessing import StandardScaler

                Xk = StandardScaler(with_mean=True, with_std=True).fit_transform(Xk).astype(np.float32)
            except Exception:
                pass
        if spherical:
            nrm = np.linalg.norm(Xk, axis=1, keepdims=True) + 1e-12
            Xk = (Xk / nrm).astype(np.float32)
        return Xk

    best: Dict[str, Any] = {"score": float("-inf"), "labels": None, "k": None}

    MBK = None
    if use_minibatch:
        try:
            from sklearn.cluster import MiniBatchKMeans  # type: ignore

            MBK = MiniBatchKMeans
        except Exception:
            MBK = None

    for k in k_list:
        try:
            for standardize in standardize_choices:
                for spherical in spherical_choices:
                    for init_method in init_methods:
                        if use_minibatch and MBK is not None:
                            try:
                                model = MBK(
                                    n_clusters=k,
                                    random_state=42,
                                    init=init_method,
                                    max_iter=max_iter,
                                    batch_size=batch_size,
                                    n_init=n_init,
                                    tol=tol,
                                )
                            except TypeError:
                                model = MBK(
                                    n_clusters=k,
                                    random_state=42,
                                    init=init_method,
                                    max_iter=max_iter,
                                    batch_size=batch_size,
                                )
                        else:
                            try:
                                model = KMeans(
                                    n_clusters=k,
                                    random_state=42,
                                    init=init_method,
                                    n_init=n_init,
                                    max_iter=max_iter,
                                    tol=tol,
                                    algorithm=algo,
                                )
                            except TypeError:
                                try:
                                    model = KMeans(
                                        n_clusters=k,
                                        random_state=42,
                                        init=init_method,
                                        n_init=n_init,
                                        max_iter=max_iter,
                                    )
                                except TypeError:
                                    model = KMeans(n_clusters=k, random_state=42, n_init=10)

                        X_eval = _prep_for_kmeans(X, standardize=standardize, spherical=spherical)
                        labels = model.fit_predict(X_eval)
                        sil_eval = eval_silhouette(X_eval, labels, "euclidean")
                        sil_adj = sil_eval + k_preference_bonus(used_k=k, k_value=k)
                        if isfinite(sil_adj) and sil_adj > best["score"]:
                            best = {
                                "score": sil_adj,
                                "labels": labels,
                                "k": k,
                                "raw_sil": sil_eval,
                                "n_init": int(n_init),
                                "max_iter": int(max_iter),
                                "tol": float(tol),
                                "init": init_method,
                                "algorithm": algo,
                                "minibatch": bool(use_minibatch and MBK is not None),
                                "batch_size": int(batch_size),
                                "standardize": bool(standardize),
                                "spherical": bool(spherical),
                            }
        except Exception:
            continue

    labels = best["labels"] if best["labels"] is not None else np.full((X.shape[0],), -1)
    return labels, best


def agglom_grid(X: np.ndarray, metric: str, k_list: List[int]) -> Tuple[np.ndarray, Dict[str, Any]]:
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.metrics import pairwise_distances
    import numpy as _np

    k_min = int(os.getenv("PHASEC_TARGET_K_MIN", "5"))
    k_reward = float(os.getenv("PHASEC_K_REWARD", "0.02"))
    min_cluster_size = int(os.getenv("PHASEC_MIN_CLUSTER_SIZE_AGGLO", "2"))
    pen_singleton = float(os.getenv("PHASEC_PEN_SINGLETON_AGGLO", "0.10"))
    pen_small = float(os.getenv("PHASEC_PEN_SMALL_AGGLO", "0.05"))
    links_env = os.getenv("PHASEC_AGGLO_LINKAGES", "ward,average,complete,single").strip()
    linkages = [token.strip().lower() for token in links_env.split(",") if token.strip()]
    use_cos = os.getenv("PHASEC_AGGLO_USE_COSINE", "true").lower() == "true"
    conn_k = int(os.getenv("PHASEC_AGGLO_CONNECTIVITY_K", "0"))
    conn_mutual = os.getenv("PHASEC_AGGLO_CONNECTIVITY_MUTUAL", "true").lower() == "true"

    best: Dict[str, Any] = {"score": float("-inf"), "labels": None, "k": None, "linkage": None}

    D_cos = None
    if use_cos and metric == "cosine" and X.shape[0] <= int(os.getenv("PHASEC_AGGLO_MAX_N_FOR_COS", "500")):
        try:
            D_cos = pairwise_distances(X, metric="cosine").astype(_np.float32)
        except Exception:
            D_cos = None

    connectivity = None
    if conn_k and conn_k > 0:
        try:
            from sklearn.neighbors import NearestNeighbors

            nbrs = NearestNeighbors(
                n_neighbors=min(conn_k, X.shape[0] - 1),
                metric=(metric if metric in ("euclidean", "cosine", "manhattan") else "euclidean"),
            )
            nbrs.fit(X)
            adjacency = nbrs.kneighbors_graph(X, mode="connectivity")
            if conn_mutual:
                adjacency = adjacency.minimum(adjacency.T)
            connectivity = adjacency
        except Exception:
            connectivity = None

    for linkage in linkages:
        for k in k_list:
            try:
                if linkage == "ward":
                    try:
                        model = AgglomerativeClustering(n_clusters=k, linkage="ward", connectivity=connectivity)
                    except TypeError:
                        model = AgglomerativeClustering(n_clusters=k, linkage="ward")
                    labels = model.fit_predict(X)
                else:
                    if D_cos is not None:
                        try:
                            model = AgglomerativeClustering(
                                n_clusters=k,
                                linkage=linkage,
                                metric="precomputed",
                                connectivity=connectivity,
                            )
                            labels = model.fit_predict(D_cos)
                        except TypeError:
                            model = AgglomerativeClustering(
                                n_clusters=k,
                                linkage=linkage,
                                affinity="precomputed",
                                connectivity=connectivity,
                            )
                            labels = model.fit_predict(D_cos)
                    else:
                        try:
                            model = AgglomerativeClustering(
                                n_clusters=k,
                                linkage=linkage,
                                metric="euclidean",
                                connectivity=connectivity,
                            )
                        except TypeError:
                            model = AgglomerativeClustering(
                                n_clusters=k,
                                linkage=linkage,
                                affinity="euclidean",
                                connectivity=connectivity,
                            )
                        labels = model.fit_predict(X)

                sil = eval_silhouette(X, labels, metric)
                vals, counts = _np.unique(labels[labels >= 0], return_counts=True)
                used = int(vals.size)
                singleton_ratio = float((counts == 1).sum()) / max(1, used)
                small_ratio = float((counts < max(1, min_cluster_size)).sum()) / max(1, used)
                sil_adj = sil + k_reward * max(0, k - k_min) - pen_singleton * singleton_ratio - pen_small * small_ratio
                if isfinite(sil_adj) and sil_adj > best["score"]:
                    best = {
                        "score": sil_adj,
                        "labels": labels,
                        "k": k,
                        "linkage": linkage,
                        "raw_sil": sil,
                        "singleton_ratio": float(singleton_ratio),
                        "small_ratio": float(small_ratio),
                    }
            except Exception:
                continue

    labels = best["labels"] if best["labels"] is not None else np.full((X.shape[0],), -1)
    return labels, best
