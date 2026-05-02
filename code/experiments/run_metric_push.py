#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd


CODE_DIR = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = CODE_DIR / "artifacts"
PHASEC_ROOT = ARTIFACTS_DIR / "06_apply_codebook" / "bge_large_en_v1_5"

PROFILES: Dict[str, Dict[str, str]] = {
    "silhouette_push": {
        "PHASEC_FEATURE": "tfidf_counts_l2",
        "PHASEC_CLUSTER_SPACES": "umap4,umap8,umap16,svd,raw",
        "PHASEC_UMAP_NN_LIST": "5,10,15,20,30",
        "PHASEC_UMAP_MIN_DIST_LIST": "0.0,0.01,0.05,0.1,0.25,0.5",
        "PHASEC_K_LIST": "4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20",
        "PHASEC_AGGLO_LINKAGES": "average,complete,ward",
        "PHASEC_MAX_TRIALS": "2500",
    },
    "onehot_push": {
        "PHASEC_FEATURE": "tfidf_onehot_l2",
        "PHASEC_CLUSTER_SPACES": "umap4,umap8,svd,raw",
        "PHASEC_UMAP_NN_LIST": "10,15,20,30",
        "PHASEC_UMAP_MIN_DIST_LIST": "0.0,0.01,0.05,0.1",
        "PHASEC_K_LIST": "5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20",
        "PHASEC_AGGLO_LINKAGES": "average,complete,ward",
        "PHASEC_MAX_TRIALS": "1800",
    },
    "quantized_push": {
        "PHASEC_FEATURE": "quantized",
        "PHASEC_CLUSTER_SPACES": "umap4,umap8,svd,raw",
        "PHASEC_UMAP_NN_LIST": "10,15,20,30",
        "PHASEC_UMAP_MIN_DIST_LIST": "0.0,0.01,0.05,0.1",
        "PHASEC_K_LIST": "5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20",
        "PHASEC_AGGLO_LINKAGES": "average,complete,ward",
        "PHASEC_MAX_TRIALS": "1800",
    },
    "peak_silhouette_push": {
        "PHASEC_FEATURE": "tfidf_onehot_l2",
        "PHASEC_CLUSTER_SPACES": "umap4,umap8,umap16,svd,raw",
        "PHASEC_UMAP_NN_LIST": "5,10,15,20,30",
        "PHASEC_UMAP_MIN_DIST_LIST": "0.0,0.001,0.01,0.05,0.1",
        "PHASEC_K_LIST": "2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20",
        "PHASEC_TARGET_K_MIN": "2",
        "PHASEC_NOISE_MAX": "0.95",
        "PHASEC_SIL_TOL": "0.05",
        "PHASEC_AGGLO_LINKAGES": "average,complete,ward",
        "PHASEC_MAX_TRIALS": "2200",
    },
    "clean_silhouette_push": {
        "PHASEC_FEATURE": "tfidf_counts_l2",
        "PHASEC_CLUSTER_SPACES": "umap4,umap8,umap16,svd,raw",
        "PHASEC_UMAP_NN_LIST": "5,10,15,20,30",
        "PHASEC_UMAP_MIN_DIST_LIST": "0.0,0.005,0.01,0.05,0.1",
        "PHASEC_K_LIST": "8,9,10,11,12,13,14,15,16,17,18,19,20,22,24,26,28,30",
        "PHASEC_TARGET_K_MIN": "8",
        "PHASEC_NOISE_MAX": "0.0",
        "PHASEC_K_REWARD": "0.01",
        "PHASEC_PEN_SINGLETON_AGGLO": "0.15",
        "PHASEC_PEN_SMALL_AGGLO": "0.08",
        "PHASEC_MIN_CLUSTER_SIZE_AGGLO": "3",
        "PHASEC_AGGLO_CONNECTIVITY_K": "6",
        "PHASEC_AGGLO_CONNECTIVITY_MUTUAL": "true",
        "PHASEC_KMEANS_N_INIT": "200",
        "PHASEC_KMEANS_MAX_ITER": "1000",
        "PHASEC_MAX_TRIALS": "2200",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run phase-C metric push experiments.")
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES.keys()) + ["all"],
        default="silhouette_push",
        help="Experiment profile to run.",
    )
    return parser.parse_args()


def build_summary(df: pd.DataFrame) -> Dict[str, object]:
    algo_col = "algorithm" if "algorithm" in df.columns else "algo"
    if "algorithm" in df.columns and "algo" in df.columns:
        df = df.copy()
        df["algorithm"] = df["algorithm"].fillna(df["algo"])
        algo_col = "algorithm"

    if "noise_ratio" in df.columns:
        df = df.copy()
        df["outlier_present"] = pd.to_numeric(df["noise_ratio"], errors="coerce").fillna(0.0) > 0.0

    overall = df.sort_values("silhouette", ascending=False).iloc[0].to_dict()
    no_outlier_df = df[df["outlier_present"] == False] if "outlier_present" in df.columns else df
    no_outlier = no_outlier_df.sort_values("silhouette", ascending=False).iloc[0].to_dict()
    return {
        "overall_best": {
            "space": overall.get("space"),
            "algo": overall.get(algo_col),
            "k": overall.get("k"),
            "linkage": overall.get("linkage"),
            "silhouette": overall.get("silhouette"),
            "noise_ratio": overall.get("noise_ratio"),
        },
        "no_outlier_best": {
            "space": no_outlier.get("space"),
            "algo": no_outlier.get(algo_col),
            "k": no_outlier.get("k"),
            "linkage": no_outlier.get("linkage"),
            "silhouette": no_outlier.get("silhouette"),
            "noise_ratio": no_outlier.get("noise_ratio"),
        },
    }


def run_profile(name: str, env_overrides: Dict[str, str]) -> Dict[str, object]:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    outdir = ARTIFACTS_DIR / "experiments" / "phasec" / f"{stamp}_{name}"
    outdir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.update(env_overrides)
    env["PHASEC_OUTDIR"] = str(outdir)

    subprocess.run(
        ["python", "07_run_clustering_sweep.py"],
        cwd=CODE_DIR,
        env=env,
        check=True,
    )

    sweep_csv = outdir / "sweep_results.csv"
    df = pd.read_csv(sweep_csv)
    summary = build_summary(df)
    summary_path = outdir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "profile": name,
                "env": env_overrides,
                "summary": summary,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    return {
        "profile": name,
        "outdir": str(outdir),
        **summary,
    }


def main() -> None:
    args = parse_args()
    profiles: List[str]
    if args.profile == "all":
        profiles = list(PROFILES.keys())
    else:
        profiles = [args.profile]

    results = [run_profile(name, PROFILES[name]) for name in profiles]
    leaderboard = pd.DataFrame(results)
    leaderboard_path = ARTIFACTS_DIR / "experiments" / "phasec" / "leaderboard.json"
    leaderboard_path.parent.mkdir(parents=True, exist_ok=True)
    with open(leaderboard_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
