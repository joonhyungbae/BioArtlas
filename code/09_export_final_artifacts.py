#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
09_export_final_artifacts.py
- 07 단계의 글로벌 best 결과를 표준화된 최종 산출물로 정리/저장

입력:
  - artifacts/06_apply_codebook/bge_large_en_v1_5/phaseC_sweep_results/best/
    * embedding_2d_with_clusters.csv
    * meta.json
    * cluster_scatter.png (선택)
    * cluster_dendrogram.png (선택)
    * hdbscan_condensed_tree.png (선택)
  - relation_graph/graph.gexf (선택)

출력(정리된 최종 결과):
  - artifacts/final/
    * final_data_with_clusters.csv (Artist, Artwork, Year, x, y, cluster, ...)
    * final_data_with_clusters.xlsx
    * cluster_summary.csv (클러스터별 개요)
    * meta.json (07 best 메타 + 요약 통계)
    * cluster_scatter.png, cluster_dendrogram.png, hdbscan_condensed_tree.png (가능 시 복사)
    * relation_graph.gexf (가능 시 복사)

비고:
  - web/analysis helper가 재사용할 수 있도록 data/processed/final_cluster_assignments.csv(.xlsx)도 함께 저장
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import json
import shutil
from datetime import datetime

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
DATA_DIR = REPO_ROOT / "data"
DATA_PROCESSED_DIR = DATA_DIR / "processed"
ARTIFACTS_DIR = BASE_DIR / "artifacts"
ROOT = ARTIFACTS_DIR / "06_apply_codebook" / "bge_large_en_v1_5" / "phaseC_sweep_results"
BEST_DIR = ROOT / "best"
REL_DIR = ARTIFACTS_DIR / "06_apply_codebook" / "bge_large_en_v1_5" / "relation_graph"

OUT_FINAL_DIR = ARTIFACTS_DIR / "final"
OUT_FINAL_DIR.mkdir(parents=True, exist_ok=True)


def _safe_int_year(y) -> int | None:
    try:
        # 문자열에서 4자리만 추출 시도 후 숫자 변환
        if isinstance(y, str):
            import re
            m = re.search(r"(\d{4})", y)
            if m:
                y = m.group(1)
        v = pd.to_numeric(y, errors="coerce")
        return int(v) if pd.notna(v) else None
    except Exception:
        return None


def build_cluster_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    uniq = sorted(df["cluster"].astype(int).unique().tolist())
    for cid in uniq:
        sub = df[df["cluster"].astype(int) == int(cid)]
        if sub.empty:
            continue
        # 중심
        cx = float(sub["x"].astype(float).mean())
        cy = float(sub["y"].astype(float).mean())
        # 연도 범위 (숫자 파싱 기반)
        years = sub["Year"].apply(_safe_int_year).dropna().astype(int)
        if len(years) > 0:
            y0, y1 = int(years.min()), int(years.max())
            year_range = f"{y0}-{y1}" if y0 != y1 else str(y0)
        else:
            year_range = ""
        # 작가 top-N
        top_artists = sub["Artist"].astype(str).value_counts().head(3).index.tolist()
        rows.append({
            "cluster": int(cid),
            "count": int(len(sub)),
            "center_x": cx,
            "center_y": cy,
            "year_range": year_range,
            "top_artists": ", ".join(map(str, top_artists)),
        })
    return pd.DataFrame(rows).sort_values(by=["cluster"]).reset_index(drop=True)


def main():
    # 필수 입력 확인
    csv_path = BEST_DIR / "embedding_2d_with_clusters.csv"
    meta_path = BEST_DIR / "meta.json"
    if not csv_path.exists() or not meta_path.exists():
        raise SystemExit("07 단계 best 산출물이 없습니다. 07_run_clustering_sweep.py 실행을 확인하세요.")

    df = pd.read_csv(csv_path)
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    # 컬럼 정규화: 기대 컬럼 이름 맞추기
    req_cols = ["Artist", "Artwork", "Year", "x", "y", "cluster"]
    miss = [c for c in req_cols if c not in df.columns]
    if miss:
        raise SystemExit(f"best CSV에 필요한 컬럼이 없습니다: {miss}")

    # 정리된 최종 파일 저장
    out_csv = OUT_FINAL_DIR / "final_data_with_clusters.csv"
    out_xlsx = OUT_FINAL_DIR / "final_data_with_clusters.xlsx"
    df.to_csv(out_csv, index=False)
    try:
        df.to_excel(out_xlsx, index=False)
    except Exception:
        pass

    # 과거 호환 파일명(알고리즘 무관 동일 내용)도 저장
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    legacy_csv = DATA_PROCESSED_DIR / "final_cluster_assignments.csv"
    legacy_xlsx = DATA_PROCESSED_DIR / "final_cluster_assignments.xlsx"
    try:
        df.to_csv(legacy_csv, index=False)
    except Exception:
        pass
    try:
        df.to_excel(legacy_xlsx, index=False)
    except Exception:
        pass

    # 클러스터 요약 저장
    summary_df = build_cluster_summary(df)
    summary_csv = OUT_FINAL_DIR / "cluster_summary.csv"
    summary_df.to_csv(summary_csv, index=False)

    # 2D 좌표 기반 작품 간 거리 행렬 저장 (NxN, 유클리드)
    try:
        X2 = df[["x", "y"]].astype(float).to_numpy()
        D = np.sqrt(((X2[:, None, :] - X2[None, :, :]) ** 2).sum(axis=2)).astype(np.float32)
        dist_npy = OUT_FINAL_DIR / "artwork_distance_2d.npy"
        dist_csv = OUT_FINAL_DIR / "artwork_distance_2d.csv"
        idx_csv = OUT_FINAL_DIR / "artwork_distance_index.csv"
        np.save(dist_npy, D)
        pd.DataFrame(D).to_csv(dist_csv, index=False)
        # 인덱스 매핑(행/열 0..N-1 → 작품 식별자)
        pd.DataFrame({
            "id": np.arange(len(df), dtype=int),
            "Artist": df["Artist"].astype(str),
            "Artwork": df["Artwork"].astype(str),
            "Year": df["Year"],
            "cluster": df["cluster"].astype(int),
        }).to_csv(idx_csv, index=False)
    except Exception:
        dist_npy = dist_csv = idx_csv = None

    # 메타 병합 및 저장(요약 통계 추가)
    cluster_ids = sorted([int(c) for c in df["cluster"].astype(int).unique().tolist() if int(c) >= 0])
    stats: Dict[str, Any] = {
        "saved_at": datetime.now().isoformat(),
        "total_artworks": int(len(df)),
        "n_clusters": int(len(cluster_ids)),
        "n_outliers": int((df["cluster"].astype(int) < 0).sum()),
        "clusters": summary_df.to_dict(orient="records"),
    }
    meta_out = {
        "source_meta": meta,
        "summary": stats,
    }
    with open(OUT_FINAL_DIR / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta_out, f, ensure_ascii=False, indent=2)

    # 이미지/그래프 산출물 복사(가능한 경우)
    def _copy_if_exists(src: Path, dst: Path):
        try:
            if src.exists():
                shutil.copy2(src, dst)
        except Exception:
            pass

    _copy_if_exists(BEST_DIR / "cluster_scatter.png", OUT_FINAL_DIR / "cluster_scatter.png")
    _copy_if_exists(BEST_DIR / "cluster_dendrogram.png", OUT_FINAL_DIR / "cluster_dendrogram.png")
    _copy_if_exists(BEST_DIR / "hdbscan_condensed_tree.png", OUT_FINAL_DIR / "hdbscan_condensed_tree.png")
    _copy_if_exists(REL_DIR / "graph.gexf", OUT_FINAL_DIR / "relation_graph.gexf")

    print("[09] Saved:")
    print(" -", out_csv)
    if out_xlsx.exists():
        print(" -", out_xlsx)
    print(" -", summary_csv)
    print(" -", OUT_FINAL_DIR / "meta.json")
    if (OUT_FINAL_DIR / "cluster_scatter.png").exists():
        print(" -", OUT_FINAL_DIR / "cluster_scatter.png")
    if (OUT_FINAL_DIR / "cluster_dendrogram.png").exists():
        print(" -", OUT_FINAL_DIR / "cluster_dendrogram.png")
    if (OUT_FINAL_DIR / "hdbscan_condensed_tree.png").exists():
        print(" -", OUT_FINAL_DIR / "hdbscan_condensed_tree.png")
    if (OUT_FINAL_DIR / "relation_graph.gexf").exists():
        print(" -", OUT_FINAL_DIR / "relation_graph.gexf")
    if dist_npy and Path(dist_npy).exists():
        print(" -", dist_npy)
    if dist_csv and Path(dist_csv).exists():
        print(" -", dist_csv)
    if idx_csv and Path(idx_csv).exists():
        print(" -", idx_csv)


if __name__ == "__main__":
    main()
