#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering
from sklearn.manifold import trustworthiness
from sklearn.metrics import pairwise_distances, silhouette_score
from sklearn.neighbors import NearestNeighbors
import umap


BASE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"
FEATURES_NPZ = ARTIFACTS_DIR / "06_apply_codebook" / "bge_large_en_v1_5" / "combined_tfidf_counts_l2.npz"
SWEEP_RESULTS_CSV = ARTIFACTS_DIR / "06_apply_codebook" / "bge_large_en_v1_5" / "phaseC_sweep_results" / "sweep_results.csv"

EXPECTED = {
    "algorithm": "agglomerative",
    "linkage": "average",
    "k": 15,
    "space": "umap4_nn10_md0.01_sp1.0",
    "silhouette_mean": 0.664,
    "silhouette_std": 0.008,
    "trustworthiness": 0.805,
    "continuity": 0.812,
}


def _knn_indices(X: np.ndarray, k: int, metric: str, full: bool = False) -> np.ndarray:
    n = X.shape[0]
    n_neighbors = max(2, (n - 1) if full else min(n, k + 1))
    nn = NearestNeighbors(
        n_neighbors=n_neighbors,
        metric=(metric if metric in ("euclidean", "cosine", "manhattan") else "euclidean"),
    )
    nn.fit(X)
    _, idx = nn.kneighbors(X)
    return idx[:, 1:]


def _knn_overlap(idx_high: np.ndarray, idx_low: np.ndarray, k: int) -> float:
    n = idx_high.shape[0]
    total = 0.0
    for i in range(n):
        a = set(idx_high[i, :k].tolist())
        b = set(idx_low[i, :k].tolist())
        total += len(a.intersection(b)) / float(k)
    return float(total / max(1, n))


def _continuity(idx_high_full: np.ndarray, idx_low_full: np.ndarray, k: int) -> float:
    n = idx_high_full.shape[0]
    denom = n * k * (2 * n - 3 * k - 1)
    norm = 2.0 / float(denom)
    total = 0.0
    for i in range(n):
        high_k = set(idx_high_full[i, :k].tolist())
        low_k = set(idx_low_full[i, :k].tolist())
        missing = high_k.difference(low_k)
        ranks_low = {int(j): (ri + 1) for ri, j in enumerate(idx_low_full[i].tolist())}
        for j in missing:
            total += max(0, int(ranks_low.get(int(j), n)) - k)
    return float(1.0 - norm * total)


def projection_quality(X_high: np.ndarray, X_low: np.ndarray, k: int) -> Dict[str, float]:
    idx_h_k = _knn_indices(X_high, k=k, metric="cosine", full=False)
    idx_l_k = _knn_indices(X_low, k=k, metric="cosine", full=False)
    idx_h_full = _knn_indices(X_high, k=k, metric="cosine", full=True)
    idx_l_full = _knn_indices(X_low, k=k, metric="cosine", full=True)
    return {
        "trustworthiness": float(trustworthiness(X_high, X_low, n_neighbors=k, metric="cosine")),
        "continuity": _continuity(idx_h_full, idx_l_full, k),
        "knn_overlap": _knn_overlap(idx_h_k, idx_l_k, k),
    }


def fit_exact_agglomerative(X_low: np.ndarray) -> np.ndarray:
    D_cos = pairwise_distances(X_low, metric="cosine").astype(np.float32)
    try:
        model = AgglomerativeClustering(
            n_clusters=EXPECTED["k"],
            linkage=EXPECTED["linkage"],
            metric="precomputed",
        )
    except TypeError:
        model = AgglomerativeClustering(
            n_clusters=EXPECTED["k"],
            linkage=EXPECTED["linkage"],
            affinity="precomputed",
        )
    return model.fit_predict(D_cos)


def evaluate_seed(X_high: np.ndarray, seed: int) -> Dict[str, float]:
    X_low = umap.UMAP(
        n_components=4,
        n_neighbors=10,
        min_dist=0.01,
        spread=1.0,
        random_state=seed,
        metric="cosine",
    ).fit_transform(X_high).astype(np.float32)
    labels = fit_exact_agglomerative(X_low)
    metrics = projection_quality(X_high, X_low, k=10)
    metrics["silhouette"] = float(silhouette_score(X_low, labels, metric="cosine"))
    return metrics


def summarize(values: List[float]) -> Tuple[float, float]:
    arr = np.asarray(values, dtype=np.float32)
    return float(np.nanmean(arr)), float(np.nanstd(arr))


def inspect_sweep_results() -> Dict[str, object]:
    if not SWEEP_RESULTS_CSV.exists():
        return {"found": False, "reason": f"missing file: {SWEEP_RESULTS_CSV}"}

    df = pd.read_csv(SWEEP_RESULTS_CSV)
    if "algorithm" in df.columns:
        df["algo_norm"] = df["algorithm"].fillna(df.get("algo"))
    else:
        df["algo_norm"] = df["algo"]

    mask = (
        df["algo_norm"].astype(str).str.lower().eq(EXPECTED["algorithm"])
        & df["space"].astype(str).eq(EXPECTED["space"])
        & pd.to_numeric(df["k"], errors="coerce").eq(EXPECTED["k"])
    )
    if "linkage" in df.columns:
        mask = mask & df["linkage"].astype(str).str.lower().eq(EXPECTED["linkage"])

    row = df.loc[mask]
    if row.empty:
        return {"found": False, "reason": f"exact row not found in {SWEEP_RESULTS_CSV.name}"}

    rec = row.iloc[0].to_dict()
    return {
        "found": True,
        "row": {
            "space": rec.get("space"),
            "algo": rec.get("algo_norm"),
            "k": int(rec.get("k")),
            "linkage": rec.get("linkage"),
            "silhouette": float(rec.get("silhouette")),
            "trustworthiness_k": float(rec.get("trustworthiness_k")),
            "continuity_k": float(rec.get("continuity_k")),
            "knn_overlap_k": float(rec.get("knn_overlap_k")),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify BioArtlas paper target metrics.")
    parser.add_argument("--seeds", type=int, default=50, help="Number of UMAP seeds to evaluate.")
    args = parser.parse_args()

    if not FEATURES_NPZ.exists():
        raise SystemExit(f"Missing feature matrix: {FEATURES_NPZ}\nRun `bash run.sh` first.")

    npz = np.load(FEATURES_NPZ)
    if "combined" not in npz.files:
        raise SystemExit(f"`combined` key missing in {FEATURES_NPZ}")
    X_high = npz["combined"].astype(np.float32)

    sweep_info = inspect_sweep_results()
    print("## Sweep Check")
    print(json.dumps(sweep_info, indent=2))

    print("\n## Seed Repeat")
    all_metrics = [evaluate_seed(X_high, seed) for seed in range(args.seeds)]
    sil_mean, sil_std = summarize([m["silhouette"] for m in all_metrics])
    tw_mean, tw_std = summarize([m["trustworthiness"] for m in all_metrics])
    ct_mean, ct_std = summarize([m["continuity"] for m in all_metrics])

    result = {
        "expected": EXPECTED,
        "observed": {
            "seeds": int(args.seeds),
            "silhouette_mean": sil_mean,
            "silhouette_std": sil_std,
            "trustworthiness_mean": tw_mean,
            "trustworthiness_std": tw_std,
            "continuity_mean": ct_mean,
            "continuity_std": ct_std,
        },
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
