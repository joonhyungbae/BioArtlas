from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np

from .metrics import compute_ari_nmi


def refit_and_predict(Xc: np.ndarray, algo: str, meta: Dict[str, Any], metric: str) -> np.ndarray:
    try:
        if algo == "kmeans":
            from sklearn.cluster import KMeans

            k = int(meta.get("k") or meta.get("n_clusters") or 2)
            return KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(Xc)

        if algo == "agglomerative":
            from sklearn.cluster import AgglomerativeClustering

            linkage = str(meta.get("linkage") or "ward")
            k = int(meta.get("k") or 2)
            try:
                model = AgglomerativeClustering(n_clusters=k, linkage=linkage, metric="euclidean")
            except TypeError:
                model = AgglomerativeClustering(n_clusters=k, linkage=linkage, affinity="euclidean")
            return model.fit_predict(Xc)

        if algo == "dbscan":
            from sklearn.cluster import DBSCAN

            eps = float(meta.get("eps") or 1.0)
            min_samples = int(meta.get("min_samples") or 5)
            return DBSCAN(eps=eps, min_samples=min_samples, metric=metric).fit_predict(Xc)

        if algo == "optics":
            from sklearn.cluster import OPTICS

            xi = float(meta.get("xi") or 0.05)
            min_samples = int(meta.get("min_samples") or 5)
            model = OPTICS(min_samples=min_samples, xi=xi, metric=metric)
            model.fit(Xc)
            return model.labels_

        if algo == "hdbscan":
            try:
                import hdbscan  # type: ignore
            except Exception:
                return np.full((Xc.shape[0],), -1)

            min_cluster_size = int(meta.get("min_cluster_size") or 5)
            min_samples = meta.get("min_samples")
            selection = str(meta.get("selection") or "eom")
            kwargs: Dict[str, Any] = {
                "min_cluster_size": min_cluster_size,
                "metric": metric,
                "cluster_selection_method": selection,
            }
            if isinstance(min_samples, (int, float)) and int(min_samples) >= 0:
                kwargs["min_samples"] = int(min_samples)
            return hdbscan.HDBSCAN(**kwargs).fit_predict(Xc)
    except Exception:
        pass

    return np.full((Xc.shape[0],), -1)


def bootstrap_stability(
    Xc: np.ndarray,
    y_base: np.ndarray,
    algo: str,
    meta: Dict[str, Any],
    metric: str,
    reps: int = 5,
) -> Dict[str, float]:
    rng = np.random.default_rng(42)
    aris: List[float] = []
    nmis: List[float] = []
    n = Xc.shape[0]

    for _ in range(max(1, reps)):
        idx = rng.integers(low=0, high=n, size=n)
        y_fit = refit_and_predict(Xc[idx], algo, meta, metric)
        ari, nmi = compute_ari_nmi(y_base[idx], y_fit)
        aris.append(ari)
        nmis.append(nmi)

    def _mean_std(values: List[float]) -> Tuple[float, float]:
        arr = np.array(values, dtype=np.float32)
        return float(np.nanmean(arr)), float(np.nanstd(arr))

    ari_mean, ari_std = _mean_std(aris)
    nmi_mean, nmi_std = _mean_std(nmis)
    return {
        "reps": int(reps),
        "ari_mean": ari_mean,
        "ari_std": ari_std,
        "nmi_mean": nmi_mean,
        "nmi_std": nmi_std,
    }
