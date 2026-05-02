#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
07_run_clustering_sweep.py
- 목표: 06단계 특징을 기반으로 다양한 파라미터/공간/알고리즘을 스윕하여 최고의 실루엣 스코어를 찾고 저장.

고정 입출력:
- 입력 루트: data/processed/embeddings/bge_large_en_v1_5/codebook_applied/
  * ids.csv
  * combined_*.npz (06 산출 특징)
- 출력 루트: .../codebook_applied/phaseC_sweep_results/
  * sweep_results.csv (전 조합 성능표)
  * best/embedding_2d_with_clusters.csv, cluster_scatter.png, meta.json

설정(환경변수로 축소/확장 가능):
- PHASEC_FEATURE: tfidf_counts_l2|tfidf_counts_bm25_l2|tfidf_counts_svd100|tfidf_counts_bm25_svd100|quantized|tfidf_onehot_l2|onehot|counts
- PHASEC_CLUSTER_SPACES: 콤마구분, 예: umap4,umap8,svd50,svd100,raw (기본: umap4,svd100,raw)
- PHASEC_K_LIST: KMeans/Agglo K 후보, 예: 2,3,4,5,8,10,12,15 (기본 동일)
- PHASEC_MAX_TRIALS: 최대 평가 조합 수 하드 제한(기본 200)
"""

from __future__ import annotations
import os
from pathlib import Path

import pandas as pd
import warnings
try:
    from matplotlib import MatplotlibDeprecationWarning  # type: ignore
except Exception:  # pragma: no cover
    MatplotlibDeprecationWarning = None  # type: ignore

# 외부 라이브러리 경고 억제(실행 로그 간결화)
warnings.filterwarnings("ignore", category=FutureWarning, module=r"sklearn\..*")
warnings.filterwarnings("ignore", category=UserWarning, module=r"umap\.umap_.*")
warnings.filterwarnings("ignore", category=UserWarning, module=r"umap")
warnings.filterwarnings("ignore", category=UserWarning, message=r".*n_jobs value 1 overridden.*")
warnings.filterwarnings("ignore", category=UserWarning, message=r".*Use no seed for parallelism.*")
warnings.filterwarnings("ignore", category=UserWarning, message=r".*renamed to 'ensure_all_finite'.*")
warnings.filterwarnings("ignore", category=FutureWarning, message=r".*renamed to 'ensure_all_finite'.*")
warnings.filterwarnings("ignore", category=UserWarning, module=r"sklearn\..*")
warnings.filterwarnings("ignore", category=UserWarning, module=r"matplotlib\..*")
warnings.filterwarnings("ignore", category=FutureWarning, module=r"matplotlib\..*")
if MatplotlibDeprecationWarning is not None:
    warnings.filterwarnings("ignore", category=MatplotlibDeprecationWarning)

from phasec.paths import PHASEC_ROOT as ROOT
from phasec.reporting import (
    build_visual_embedding,
    export_best_artifacts,
    export_relation_artifacts,
    normalize_results_df,
    save_best_by_algo_summary,
)
from phasec.runner import run_sweep, seed_everything
from phasec.spaces import (
    apply_metric_learning as _apply_metric_learning,
    load_feature as _load_feature,
)


OUTDIR = Path(os.getenv("PHASEC_OUTDIR", str(ROOT / "phaseC_sweep_results"))).resolve()
REL_OUT = OUTDIR / "relation_graph" if "PHASEC_OUTDIR" in os.environ else ROOT / "relation_graph"


def main():
    import time
    OUTDIR.mkdir(parents=True, exist_ok=True)
    ids_path = ROOT / "ids.csv"
    if not ids_path.exists():
        raise SystemExit("ids.csv가 필요합니다. 04/06 단계를 확인하세요.")
    df_ids = pd.read_csv(ids_path)

    # 재현성 시드
    seed = int(os.getenv('PHASEC_SEED', '42'))
    seed_everything(seed)
    feature_key, feat_path, X = _load_feature()
    print(f"[09] Using features: {feature_key} -> {feat_path} | X={X.shape}")
    t_start = time.time()

    # Metric learning(옵션) 적용
    X_ml, ml_info = _apply_metric_learning(X, df_ids, feature_key)
    if ml_info.get("metric_learning", False):
        X = X_ml
        print(f"[09] Metric learning applied: algo={ml_info.get('algo')} dim={X.shape[1]} label={ml_info.get('label_col')}")
    # 원천(기준) 공간 보존: 이후 raw/projection 비교에 사용
    X_base = X.copy()

    # K 리스트 설정
    # 기본 K 범위: 2~15
    k_env = os.getenv('PHASEC_K_LIST', '2,3,4,5,6,7,8,9,10,11,12,13,14,15')
    k_list = [int(v.strip()) for v in k_env.split(',') if v.strip()]
    # 더 넓게 탐색하도록 기본 trial 상한을 상향
    max_trials = int(os.getenv('PHASEC_MAX_TRIALS', '800'))
    rows, best_global, best_per_algo, space_map, metric_map = run_sweep(
        X=X,
        X_base=X_base,
        feature_key=feature_key,
        k_list=k_list,
        max_trials=max_trials,
    )
    res_df, res_path = normalize_results_df(rows, OUTDIR)

    # ========= 논문 보고용 메트릭 저장 =========
    try:
        for path in save_best_by_algo_summary(best_per_algo, res_df, space_map, metric_map, OUTDIR, X):
            print("[09] Saved:", path)
    except Exception as e:
        print(f"[09][WARN] Failed to save paper metrics: {e}")
    # 러ntime 요약 기록
    try:
        with open(OUTDIR / 'runtime.txt', 'w') as f:
            f.write(f"runtime_sec={time.time()-t_start:.3f}\n")
            f.write(f"seed={seed}\n")
    except Exception:
        pass

    X2, emb_method = build_visual_embedding(X, feature_key)
    labels_best, artifact_paths = export_best_artifacts(
        df_ids=df_ids,
        X2=X2,
        feature_key=feature_key,
        feat_path=feat_path,
        best_global=best_global,
        best_per_algo=best_per_algo,
        res_df=res_df,
        outdir=OUTDIR,
        emb_method=emb_method,
    )

    print("[09] Saved:")
    print(" -", res_path)
    for path in artifact_paths:
        print(" -", path)

    for path in export_relation_artifacts(X, labels_best, best_global, space_map, metric_map, OUTDIR, REL_OUT):
        print(" -", path)


if __name__ == "__main__":
    main()
