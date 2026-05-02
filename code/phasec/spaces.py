from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .paths import PHASEC_ROOT


def load_feature(root: Path = PHASEC_ROOT) -> Tuple[str, Path, np.ndarray]:
    feature_map = {
        "tfidf_counts_l2": root / "combined_tfidf_counts_l2.npz",
        "tfidf_counts_bm25_l2": root / "combined_tfidf_counts_bm25_l2.npz",
        "tfidf_counts_bm25": root / "combined_tfidf_counts_bm25.npz",
        "tfidf_counts_svd100": root / "combined_tfidf_counts_svd100.npz",
        "tfidf_counts_bm25_svd100": root / "combined_tfidf_counts_bm25_svd100.npz",
        "quantized": root / "combined_quantized_embeddings.npz",
        "tfidf_onehot_l2": root / "combined_tfidf_onehot_l2.npz",
        "onehot": root / "combined_cluster_onehot.npz",
        "counts": root / "combined_cluster_counts.npz",
    }
    pref = os.getenv("PHASEC_FEATURE", "").strip()
    key: Optional[str] = None
    if pref and pref in feature_map and feature_map[pref].exists():
        key = pref
    else:
        for candidate in [
            "tfidf_counts_bm25_l2",
            "tfidf_counts_l2",
            "tfidf_counts_bm25_svd100",
            "tfidf_counts_svd100",
            "quantized",
            "tfidf_onehot_l2",
            "onehot",
            "counts",
        ]:
            if feature_map[candidate].exists():
                key = candidate
                break
    if key is None:
        raise SystemExit("Could not find a usable 06 feature NPZ artifact.")
    feature_path = feature_map[key]
    npz = np.load(feature_path)
    if "combined" not in npz.files:
        raise SystemExit(f"Missing 'combined' key in NPZ: {feature_path}")
    X = npz["combined"].astype(np.float32)
    return key, feature_path, X


def build_cluster_space_candidates(X: np.ndarray, feature_key: str) -> List[Tuple[str, np.ndarray, str]]:
    """Build candidate clustering spaces as (name, matrix, metric)."""
    wanted = os.getenv("PHASEC_CLUSTER_SPACES", "umap4,umap8,umap16,svd,raw").strip()
    spaces = [token.strip().lower() for token in wanted.split(",") if token.strip()]
    out: List[Tuple[str, np.ndarray, str]] = []

    def _parse_int_list(env_key: str, default_val: str) -> List[int]:
        raw = os.getenv(env_key, default_val)
        values: List[int] = []
        for token in [value.strip() for value in raw.split(",") if value.strip()]:
            try:
                values.append(int(token))
            except Exception:
                continue
        return values

    def _parse_float_list(env_key: str, default_val: str) -> List[float]:
        raw = os.getenv(env_key, default_val)
        values: List[float] = []
        for token in [value.strip() for value in raw.split(",") if value.strip()]:
            try:
                values.append(float(token))
            except Exception:
                continue
        return values

    def _umap_spaces(dim: int) -> List[Tuple[str, np.ndarray, str]]:
        try:
            import umap

            metric = (
                "cosine"
                if feature_key in ("tfidf_counts_l2", "tfidf_onehot_l2", "tfidf_counts_bm25_l2")
                else "euclidean"
            )
            nn_list = _parse_int_list("PHASEC_UMAP_NN_LIST", os.getenv("PHASEC_UMAP_NN", "10,15,30")) or [10, 15, 30]
            md_list = _parse_float_list(
                "PHASEC_UMAP_MIN_DIST_LIST",
                os.getenv("PHASEC_UMAP_MIN_DIST", "0.0,0.01,0.1,0.5"),
            ) or [0.0, 0.01, 0.1, 0.5]
            sp_list = _parse_float_list(
                "PHASEC_UMAP_SPREAD_LIST",
                os.getenv("PHASEC_UMAP_SPREAD", "1.0"),
            ) or [1.0]
            outputs: List[Tuple[str, np.ndarray, str]] = []
            for nn in nn_list:
                for md in md_list:
                    for spread in sp_list:
                        Xs = umap.UMAP(
                            n_components=dim,
                            n_neighbors=int(nn),
                            min_dist=float(md),
                            spread=float(spread),
                            random_state=42,
                            metric=metric,
                        ).fit_transform(X).astype(np.float32)
                        outputs.append((f"umap{dim}_nn{nn}_md{md}_sp{spread}", Xs, metric))
            return outputs
        except Exception:
            return []

    for space_name in spaces:
        if space_name == "raw":
            out.append(("raw", X, "euclidean"))
        elif space_name.startswith("umap"):
            try:
                dim = int(space_name.replace("umap", ""))
            except Exception:
                dim = 4
            out.extend(_umap_spaces(dim))
        elif space_name.startswith("svd"):
            try:
                dim = int(space_name.replace("svd", ""))
            except Exception:
                dim = 100
            try:
                from sklearn.decomposition import TruncatedSVD

                svd = TruncatedSVD(n_components=min(dim, max(2, X.shape[1] - 1)), random_state=42)
                Xs = svd.fit_transform(X).astype(np.float32)
                out.append((f"svd{dim}", Xs, "euclidean"))
            except Exception:
                pass
        elif space_name == "svd":
            for dim in _parse_int_list("PHASEC_SVD_D_LIST", "50,100,150"):
                try:
                    from sklearn.decomposition import TruncatedSVD

                    svd = TruncatedSVD(n_components=min(dim, max(2, X.shape[1] - 1)), random_state=42)
                    Xs = svd.fit_transform(X).astype(np.float32)
                    out.append((f"svd{dim}", Xs, "euclidean"))
                except Exception:
                    continue
    return out


def apply_metric_learning(
    X: np.ndarray,
    df_ids: pd.DataFrame,
    feature_key: str,
    env_prefix: str = "PHASEC_",
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Optionally re-project the feature space with metric learning."""
    algo = os.getenv(f"{env_prefix}METRIC_LEARN", "none").strip().lower()
    label_col = os.getenv(f"{env_prefix}LABEL_COL", "").strip()
    out_dim = int(os.getenv(f"{env_prefix}ML_DIM", "64").strip() or 64)
    info: Dict[str, Any] = {"metric_learning": False}
    if algo in ("none", ""):
        return X, info
    if label_col == "" or label_col not in df_ids.columns:
        print(f"[09][INFO] Metric learning requested ({algo}) but label column missing: '{label_col}'. Skipping.")
        return X, info

    y = df_ids[label_col].astype(str).fillna("")
    uniq = sorted(y.unique().tolist())
    if len(uniq) < 2:
        print(f"[09][INFO] Metric learning skipped: label '{label_col}' has <2 classes.")
        return X, info

    try:
        if algo == "nca":
            try:
                from metric_learn import NCA  # type: ignore
            except Exception:
                print("[09][INFO] 'metric-learn' not installed. Install via: pip install metric-learn")
                return X, info
            print(f"[09] Metric learning: NCA on feature '{feature_key}', dim={out_dim}, labels='{label_col}' ...")
            model = NCA(n_components=out_dim, init="auto", max_iter=1000)
            X_tr = model.fit_transform(X, y)
            return X_tr.astype(np.float32), {
                "metric_learning": True,
                "algo": "nca",
                "label_col": label_col,
                "out_dim": int(X_tr.shape[1]),
            }
        if algo == "lmnn":
            try:
                from metric_learn import LMNN  # type: ignore
            except Exception:
                print("[09][INFO] 'metric-learn' not installed. Install via: pip install metric-learn")
                return X, info
            print(f"[09] Metric learning: LMNN on feature '{feature_key}', dim={out_dim}, labels='{label_col}' ...")
            model = LMNN(k=3, learn_rate=1e-6, max_iter=200, n_components=out_dim)
            X_tr = model.fit_transform(X, y)
            return X_tr.astype(np.float32), {
                "metric_learning": True,
                "algo": "lmnn",
                "label_col": label_col,
                "out_dim": int(X_tr.shape[1]),
            }
        print(f"[09][INFO] Unknown metric learning algo '{algo}'. Skipping.")
        return X, info
    except Exception as exc:
        print(f"[09][WARN] Metric learning failed: {exc}. Skipping.")
        return X, {"metric_learning": False}

