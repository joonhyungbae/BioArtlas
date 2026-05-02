from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

import numpy as np
import pandas as pd

from .clustering import bootstrap_stability
from .exports import (
    compute_cluster_centroids,
    export_cluster_relation_graph,
    export_dendrogram,
    export_hdbscan_condensed_tree,
)


def to_jsonable(value: Any) -> Any:
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.ndarray):
        return None
    return value


def parse_space_params(space_name: str) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    try:
        if isinstance(space_name, str) and space_name.startswith("umap"):
            parts = space_name.split("_")
            params["umap_dim"] = int(parts[0].replace("umap", ""))
            for part in parts[1:]:
                if part.startswith("nn"):
                    params["umap_nn"] = int(part.replace("nn", ""))
                elif part.startswith("md"):
                    params["umap_min_dist"] = float(part.replace("md", ""))
                elif part.startswith("sp"):
                    params["umap_spread"] = float(part.replace("sp", ""))
    except Exception:
        return {}
    return params


def normalize_results_df(rows: List[Dict[str, Any]], outdir: Path) -> Tuple[pd.DataFrame, Path]:
    res_df = pd.DataFrame(rows)
    if "noise_ratio" in res_df.columns:
        res_df["outlier_present"] = pd.to_numeric(res_df["noise_ratio"], errors="coerce").fillna(0.0) > 0.0
    else:
        res_df["outlier_present"] = False

    if not res_df.empty:
        res_df = res_df.sort_values(
            by=["outlier_present", "silhouette", "space", "algo"],
            ascending=[True, False, True, True],
        )

    res_path = outdir / "sweep_results.csv"
    res_df.to_csv(res_path, index=False)
    return res_df, res_path


def _raw_sil_from_meta(meta: Mapping[str, Any]) -> float:
    for key in ("raw_sil", "silhouette", "score"):
        value = meta.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return float("nan")


def _record_mask(res_df: pd.DataFrame, record: Mapping[str, Any]) -> pd.Series:
    mask = (res_df["space"] == record.get("space")) & (res_df["algo"] == record.get("algo"))
    meta = record.get("meta") or {}
    numeric_keys = ("k", "eps", "min_samples", "min_cluster_size", "xi", "bandwidth")
    string_keys = ("linkage", "cluster_selection_method")

    for key in numeric_keys:
        value = meta.get(key)
        if value is None or key not in res_df.columns:
            continue
        series = pd.to_numeric(res_df[key], errors="coerce")
        try:
            target = float(value)
        except Exception:
            continue
        mask = mask & np.isclose(series.fillna(np.nan), target, equal_nan=False)

    for key in string_keys:
        value = meta.get(key)
        if value is None or key not in res_df.columns:
            continue
        mask = mask & (res_df[key].astype(str) == str(value))

    return mask


def best_metrics_from_results(res_df: pd.DataFrame, record: Mapping[str, Any]) -> Dict[str, Any]:
    if res_df.empty:
        return {}
    try:
        best_rows = res_df.loc[_record_mask(res_df, record)]
        if best_rows.empty:
            return {}
        return {
            str(key): to_jsonable(value)
            for key, value in best_rows.iloc[0].to_dict().items()
            if key not in {"labels", "meta"}
        }
    except Exception:
        return {}


def save_best_by_algo_summary(
    best_per_algo: Mapping[str, Dict[str, Any]],
    res_df: pd.DataFrame,
    space_map: Mapping[str, np.ndarray],
    metric_map: Mapping[str, str],
    outdir: Path,
    fallback_space: np.ndarray,
) -> List[Path]:
    best_rows: List[Dict[str, Any]] = []
    for algo in sorted(best_per_algo.keys()):
        rec = best_per_algo[algo]
        labels = rec.get("labels")
        if labels is None:
            continue
        labels = np.asarray(labels)
        used_k = int(np.unique(labels[labels >= 0]).size)
        noise_ratio = float((labels < 0).sum()) / len(labels)
        meta = rec.get("meta") or {}
        row = {
            "algo": algo,
            "space": rec.get("space"),
            "score_adj": float(rec.get("score", float("nan"))),
            "raw_sil": _raw_sil_from_meta(meta),
            "used_k": used_k,
            "noise_ratio": noise_ratio,
            "linkage": meta.get("linkage"),
            "k": meta.get("k"),
            "eps": meta.get("eps"),
            "min_samples": meta.get("min_samples"),
            "xi": meta.get("xi"),
            "connectivity_k": os.getenv("PHASEC_AGGLO_CONNECTIVITY_K", ""),
            "connectivity_mutual": os.getenv("PHASEC_AGGLO_CONNECTIVITY_MUTUAL", ""),
        }
        row.update(parse_space_params(str(rec.get("space") or "")))

        space_name = str(rec.get("space") or "")
        X_eval = space_map.get(space_name, fallback_space)
        metric = metric_map.get(space_name, "euclidean")
        stab = bootstrap_stability(
            X_eval,
            labels,
            algo,
            meta,
            metric=metric,
            reps=int(os.getenv("PHASEC_STAB_REPS", "5")),
        )
        row.update(
            {
                "ari_mean": stab.get("ari_mean"),
                "ari_std": stab.get("ari_std"),
                "nmi_mean": stab.get("nmi_mean"),
                "nmi_std": stab.get("nmi_std"),
            }
        )
        best_rows.append(row)

    paper_df = pd.DataFrame(best_rows)
    if not paper_df.empty:
        paper_df = paper_df.sort_values(by=["score_adj", "algo"], ascending=[False, True])

    summary_path = outdir / "best_by_algo_summary.csv"
    topn_path = outdir / "sweep_topN.csv"
    paper_df.to_csv(summary_path, index=False)
    res_df.head(int(os.getenv("PHASEC_PAPER_TOPN", "10"))).to_csv(topn_path, index=False)
    return [summary_path, topn_path]


def build_visual_embedding(X: np.ndarray, feature_key: str) -> Tuple[np.ndarray, str]:
    try:
        import umap

        viz_metric = "cosine" if feature_key in ("tfidf_counts_l2", "tfidf_onehot_l2") else "euclidean"
        X2 = umap.UMAP(
            n_components=2,
            n_neighbors=15,
            min_dist=0.1,
            random_state=42,
            metric=viz_metric,
        ).fit_transform(X).astype(np.float32)
        return X2, f"UMAP[{viz_metric}]"
    except Exception:
        from sklearn.manifold import TSNE

        X2 = TSNE(n_components=2, random_state=42, perplexity=15, init="random").fit_transform(X).astype(np.float32)
        return X2, "t-SNE"


def _scatter_colors(labels: np.ndarray) -> List[str]:
    from matplotlib import cm, colors as mcolors

    unique_labels = sorted(int(label) for label in np.unique(labels))
    tab20 = cm.get_cmap("tab20", 20)
    tab10 = cm.get_cmap("tab10", 10)

    def color_for_index(index: int) -> str:
        cmap = tab20 if index % 2 == 0 else tab10
        return mcolors.to_hex(cmap(index % cmap.N))

    color_map: Dict[int, str] = {}
    cluster_index = 0
    for label in unique_labels:
        if label == -1:
            color_map[label] = "#FFD700"
        else:
            color_map[label] = color_for_index(cluster_index)
            cluster_index += 1
    return [color_map[int(label)] for label in labels]


def _save_scatter_plot(X2: np.ndarray, labels: np.ndarray, title: str, out_path: Path) -> bool:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        plt.figure(figsize=(8, 6))
        plt.scatter(X2[:, 0], X2[:, 1], c=_scatter_colors(labels), s=22, alpha=0.95, linewidths=0)
        plt.title(title)
        plt.tight_layout()
        plt.savefig(out_path, dpi=200)
        plt.close()
        return True
    except Exception:
        return False


def _build_meta(
    feature_key: str,
    feat_path: Path,
    record: Mapping[str, Any],
    res_df: pd.DataFrame,
    emb_method: str,
) -> Dict[str, Any]:
    meta_clean = {
        key: to_jsonable(value)
        for key, value in (record.get("meta") or {}).items()
        if key != "labels"
    }
    return {
        "feature": {"key": feature_key, "path": str(feat_path)},
        "best": {
            "space": record.get("space"),
            "algo": record.get("algo"),
            "score": float(record.get("score", float("nan"))),
            "meta": meta_clean,
            "space_params": parse_space_params(str(record.get("space") or "")),
            "metrics": best_metrics_from_results(res_df, record),
        },
        "viz": {"embedding": emb_method},
    }


def export_cluster_bundle(
    df_ids: pd.DataFrame,
    X2: np.ndarray,
    labels: np.ndarray,
    feature_key: str,
    feat_path: Path,
    record: Mapping[str, Any],
    res_df: pd.DataFrame,
    outdir: Path,
    emb_method: str,
    title: str,
) -> List[Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    df2 = pd.DataFrame({"x": X2[:, 0], "y": X2[:, 1], "cluster": labels})
    df_full = pd.concat([df_ids.reset_index(drop=True), df2.reset_index(drop=True)], axis=1)

    csv_path = outdir / "embedding_2d_with_clusters.csv"
    meta_path = outdir / "meta.json"
    scatter_path = outdir / "cluster_scatter.png"
    df_full.to_csv(csv_path, index=False)
    with open(meta_path, "w", encoding="utf-8") as handle:
        json.dump(_build_meta(feature_key, feat_path, record, res_df, emb_method), handle, ensure_ascii=False, indent=2)

    saved_paths = [csv_path, meta_path]
    if _save_scatter_plot(X2, labels, title, scatter_path):
        saved_paths.append(scatter_path)
    return saved_paths


def export_best_artifacts(
    df_ids: pd.DataFrame,
    X2: np.ndarray,
    feature_key: str,
    feat_path: Path,
    best_global: Mapping[str, Any],
    best_per_algo: Mapping[str, Dict[str, Any]],
    res_df: pd.DataFrame,
    outdir: Path,
    emb_method: str,
) -> Tuple[np.ndarray, List[Path]]:
    labels_best = best_global.get("labels")
    if labels_best is None:
        labels_best = np.full((X2.shape[0],), -1, dtype=int)
    labels_best = np.asarray(labels_best)

    saved_paths = export_cluster_bundle(
        df_ids=df_ids,
        X2=X2,
        labels=labels_best,
        feature_key=feature_key,
        feat_path=feat_path,
        record=best_global,
        res_df=res_df,
        outdir=outdir / "best",
        emb_method=emb_method,
        title=f"Best: {best_global.get('algo')} on {best_global.get('space')} (sil={float(best_global.get('score', float('nan'))):.3f})",
    )

    best_algos_dir = outdir / "best_by_algo"
    best_algos_dir.mkdir(parents=True, exist_ok=True)
    for algo, rec in best_per_algo.items():
        labels = rec.get("labels")
        if labels is None:
            continue
        record = {
            "space": rec.get("space"),
            "algo": algo,
            "score": rec.get("score"),
            "meta": rec.get("meta") or {},
        }
        saved_paths.extend(
            export_cluster_bundle(
                df_ids=df_ids,
                X2=X2,
                labels=np.asarray(labels),
                feature_key=feature_key,
                feat_path=feat_path,
                record=record,
                res_df=res_df,
                outdir=best_algos_dir / algo,
                emb_method=emb_method,
                title=f"Best by algo: {algo} on {rec.get('space')} (sil={float(rec.get('score', float('nan'))):.3f})",
            )
        )

    return labels_best, saved_paths


def export_relation_artifacts(
    X_default: np.ndarray,
    labels_best: np.ndarray,
    best_global: Mapping[str, Any],
    space_map: Mapping[str, np.ndarray],
    metric_map: Mapping[str, str],
    outdir: Path,
    rel_out: Path,
) -> List[Path]:
    space_name = str(best_global.get("space") or "")
    X_best = space_map.get(space_name, X_default)
    metric_best = metric_map.get(space_name, "euclidean")
    saved_paths: List[Path] = []

    centroids, cluster_ids = compute_cluster_centroids(X_best, labels_best)
    den_png = outdir / "best" / "cluster_dendrogram.png"
    den_link = outdir / "best" / "cluster_dendrogram_linkage.npy"
    if export_dendrogram(centroids, den_png, den_link, method="ward"):
        saved_paths.extend([den_png, den_link])

    if str(best_global.get("algo")) == "hdbscan":
        mcs = int((best_global.get("meta") or {}).get("min_cluster_size", 10))
        tree_png = outdir / "best" / "hdbscan_condensed_tree.png"
        if export_hdbscan_condensed_tree(X_best, mcs, metric_best, tree_png):
            saved_paths.append(tree_png)

    k_rel = int(os.getenv("PHASEC_REL_GRAPH_K", "5"))
    rel_metric = os.getenv("PHASEC_REL_GRAPH_METRIC", "cosine").strip().lower()
    rel_out.mkdir(parents=True, exist_ok=True)
    gexf_path = rel_out / "graph.gexf"
    info_rel = export_cluster_relation_graph(centroids, cluster_ids, rel_metric, k_rel, gexf_path)
    if info_rel.get("nodes", 0) > 0:
        saved_paths.append(gexf_path)

    return saved_paths
