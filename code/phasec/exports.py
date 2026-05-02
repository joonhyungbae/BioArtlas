from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np


def compute_cluster_centroids(X: np.ndarray, labels: np.ndarray) -> Tuple[np.ndarray, List[int]]:
    valid = labels >= 0
    if not np.any(valid):
        return np.zeros((0, X.shape[1]), dtype=np.float32), []
    X_valid = X[valid]
    labels_valid = labels[valid]
    cluster_ids = sorted(list(set(labels_valid.tolist())))
    centers = []
    for cluster_id in cluster_ids:
        idx = labels_valid == cluster_id
        if np.any(idx):
            centers.append(X_valid[idx].mean(axis=0))
    if centers:
        return np.vstack(centers).astype(np.float32), cluster_ids
    return np.zeros((0, X.shape[1]), dtype=np.float32), []


def export_dendrogram(centroids: np.ndarray, out_png: Path, out_linkage_npy: Path, method: str = "ward") -> bool:
    if centroids.size == 0 or centroids.shape[0] < 2:
        return False
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from scipy.cluster.hierarchy import dendrogram, linkage

        Z = linkage(centroids, method=method, metric="euclidean")
        out_png.parent.mkdir(parents=True, exist_ok=True)
        plt.figure(figsize=(8, 4))
        dendrogram(Z, no_labels=True, color_threshold=None)
        plt.tight_layout()
        plt.savefig(out_png, dpi=180)
        plt.close()
        np.save(out_linkage_npy, Z.astype(np.float32))
        return True
    except Exception:
        return False


def export_hdbscan_condensed_tree(X: np.ndarray, min_cluster_size: int, metric: str, out_png: Path) -> bool:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import hdbscan  # type: ignore

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            metric=metric if metric in ("euclidean", "manhattan", "cosine") else "euclidean",
        )
        clusterer.fit(X)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        try:
            ax = hdbscan.plots.condensed_tree(clusterer)
            fig = ax.get_figure()
            fig.tight_layout()
            fig.savefig(out_png, dpi=180)
            plt.close(fig)
            return True
        except Exception:
            plt.figure(figsize=(6, 4))
            labels = clusterer.labels_
            valid = labels >= 0
            plt.scatter(np.arange(labels.shape[0])[valid], labels[valid], s=2)
            plt.tight_layout()
            plt.savefig(out_png, dpi=180)
            plt.close()
            return True
    except Exception:
        return False


def export_cluster_relation_graph(
    centroids: np.ndarray,
    cluster_ids: List[int],
    metric: str,
    k: int,
    out_gexf: Path,
    leiden: bool = True,
    louvain: bool = True,
) -> Dict[str, Any]:
    info = {"nodes": int(centroids.shape[0]), "edges": 0, "used_leiden": False, "used_louvain": False}
    if centroids.size == 0 or centroids.shape[0] < 2:
        return info
    try:
        import networkx as nx  # type: ignore

        C = centroids.astype(np.float32)
        if metric == "cosine":
            nrm = np.linalg.norm(C, axis=1, keepdims=True) + 1e-12
            Cn = (C / nrm).astype(np.float32)
            W = np.clip(Cn @ Cn.T, -1.0, 1.0)
        else:
            from sklearn.metrics import pairwise_distances

            D = pairwise_distances(C, metric="euclidean")
            sigma = np.median(D[D > 0]) if np.any(D > 0) else 1.0
            W = np.exp(-(D ** 2) / (2 * (sigma ** 2) + 1e-12)).astype(np.float32)

        n = C.shape[0]
        G = nx.Graph()
        for cid, node_id in zip(cluster_ids, range(n)):
            G.add_node(int(node_id), cluster=int(cid))

        for i in range(n):
            scores = W[i].copy()
            scores[i] = -np.inf
            nn_idx = np.argpartition(-scores, kth=min(k, n - 1) - 1)[: min(k, n - 1)]
            for j in nn_idx:
                weight = float(W[i, j])
                if weight <= 0:
                    continue
                if G.has_edge(i, j):
                    if G[i][j].get("weight", 0.0) < weight:
                        G[i][j]["weight"] = weight
                else:
                    G.add_edge(int(i), int(j), weight=weight)

        info["edges"] = int(G.number_of_edges())

        part = None
        if leiden:
            try:
                import igraph as ig  # type: ignore
                import leidenalg as la  # type: ignore

                mapping = {node: i for i, node in enumerate(G.nodes())}
                inv_map = {i: node for node, i in mapping.items()}
                edges = [(mapping[u], mapping[v]) for u, v in G.edges()]
                weights = [G[u][v].get("weight", 1.0) for u, v in G.edges()]
                g = ig.Graph()
                g.add_vertices(len(mapping))
                if edges:
                    g.add_edges(edges)
                    g.es["weight"] = weights
                part_obj = la.find_partition(g, la.RBConfigurationVertexPartition, weights="weight")
                part = {inv_map[i]: int(cluster) for i, cluster in enumerate(part_obj.membership)}
                info["used_leiden"] = True
            except Exception:
                part = None
        if part is None and louvain:
            try:
                import community as community_louvain  # type: ignore

                part = community_louvain.best_partition(G, weight="weight")
                info["used_louvain"] = True
            except Exception:
                part = None
        if part is not None:
            for node in G.nodes():
                G.nodes[node]["community"] = int(part.get(node, -1))

        out_gexf.parent.mkdir(parents=True, exist_ok=True)
        nx.write_gexf(G, out_gexf)
    except Exception:
        return info
    return info

