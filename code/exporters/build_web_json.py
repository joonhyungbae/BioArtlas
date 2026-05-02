#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
build_web_json.py
- 07 단계의 글로벌 best 결과(embedding_2d_with_clusters.csv)를
  BioArtlas_web의 웹 시각화용 JSON으로 변환하여 저장

입력 우선순위:
 1) artifacts/06_apply_codebook/bge_large_en_v1_5/phaseC_sweep_results/best/embedding_2d_with_clusters.csv (글로벌 베스트)
 2) artifacts/06_apply_codebook/bge_large_en_v1_5/phaseC_sweep_results/best_by_algo/agglomerative/embedding_2d_with_clusters.csv (폴백)

출력:
 - ../BioArtlas_web/public/bioart_clustering_2d.json
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import re
import json
import numpy as np
import pandas as pd
import colorsys
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parent
CODE_DIR = BASE_DIR.parent
REPO_ROOT = CODE_DIR.parent
ROOT = CODE_DIR / "artifacts" / "06_apply_codebook" / "bge_large_en_v1_5" / "phaseC_sweep_results"
PREF_AGGLO = ROOT / "best_by_algo/agglomerative/embedding_2d_with_clusters.csv"
PREF_AGGLO_META = ROOT / "best_by_algo/agglomerative/meta.json"
FALLBACK_BEST = ROOT / "best/embedding_2d_with_clusters.csv"
FALLBACK_BEST_META = ROOT / "best/meta.json"
OUT_JSON = REPO_ROOT / "BioArtlas_web" / "public" / "bioart_clustering_2d.json"
AXIS_CSV = REPO_ROOT / "data" / "processed" / "bioartlas_axes_bilingual.csv"
ARTIST_LABEL_CSV = REPO_ROOT / "data" / "metadata" / "artist_labels.csv"

# 13 English axis columns (canonical names)
AXIS_EN_COLUMNS = [
    "Materiality",
    "Methodology",
    "Actor Relationships & Configuration",
    "Ethical Approach",
    "Aesthetic Strategy",
    "Epistemic Function",
    "Philosophical Stance",
    "Social Context",
    "Audience Engagement",
    "Temporal Scale",
    "Spatio Scale",
    "Power and Capital Critique",
    "Documentation & Representation",
]


def _generate_colors(n_colors: int) -> List[str]:
    colors: List[str] = []
    if n_colors <= 0:
        return colors
    for i in range(n_colors):
        hue = float(i) / float(max(1, n_colors))
        r, g, b = colorsys.hsv_to_rgb(hue, 0.8, 0.9)
        colors.append("#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255)))
    return colors


def _load_inputs() -> tuple[pd.DataFrame, Path, Dict[str, Any]]:
    # 우선: 글로벌 best → 없으면 agglomerative 베스트
    if FALLBACK_BEST.exists():
        csv_path = FALLBACK_BEST
        meta_path = FALLBACK_BEST_META if FALLBACK_BEST_META.exists() else None
    elif PREF_AGGLO.exists():
        csv_path = PREF_AGGLO
        meta_path = PREF_AGGLO_META if PREF_AGGLO_META.exists() else None
    else:
        raise SystemExit("best 또는 agglomerative 결과 CSV를 찾지 못했습니다. 07 단계를 확인하세요.")

    df = pd.read_csv(csv_path)
    meta: Dict[str, Any] = {}
    if meta_path is not None:
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {}
    return df, csv_path, meta


def _load_artist_labels() -> Dict[str, str]:
    if not ARTIST_LABEL_CSV.exists():
        return {}
    try:
        df = pd.read_csv(ARTIST_LABEL_CSV, dtype=str, keep_default_na=False)
    except Exception:
        return {}
    if "Artist" not in df.columns or "Artist_ko" not in df.columns:
        return {}
    labels: Dict[str, str] = {}
    for _, row in df.iterrows():
        artist = str(row.get("Artist", "")).strip()
        artist_ko = str(row.get("Artist_ko", "")).strip()
        if artist and artist_ko:
            labels[artist] = artist_ko
    return labels


def main():
    df, src_csv, meta = _load_inputs()
    artist_labels = _load_artist_labels()

    # 필수 컬럼 확인/정규화
    # 예상 컬럼: Artist, Artwork, Year, (선택)Gen, x, y, cluster
    required = {"Artist", "Artwork", "Year", "x", "y", "cluster"}
    miss = [c for c in required if c not in df.columns]
    if miss:
        raise SystemExit(f"필수 컬럼 누락: {miss} in {src_csv}")

    # 숫자화/클린업 (연도 행 제거 없이 숫자만 별도 파싱하여 사용)
    # Year_num: Year 문자열에서 첫 4자리 숫자만 추출해 숫자 연도로 사용, 없으면 NaN
    try:
        # 올바른 4자리 연도 추출 (raw string에서 역슬래시 이스케이프 제거)
        year_extracted = df["Year"].astype(str).str.extract(r"(\d{4})")[0]
        df["Year_num"] = pd.to_numeric(year_extracted, errors="coerce")
    except Exception:
        df["Year_num"] = pd.to_numeric(df.get("Year", None), errors="coerce")

    df["cluster"] = pd.to_numeric(df["cluster"], errors="coerce").fillna(-1).astype(int)
    df["x"] = pd.to_numeric(df["x"], errors="coerce").astype(float)
    df["y"] = pd.to_numeric(df["y"], errors="coerce").astype(float)

    # 클러스터 ID 목록(정렬)
    uniq_clusters = sorted(df["cluster"].unique().tolist())
    # outlier(-1) 분리
    non_out = [c for c in uniq_clusters if c >= 0]
    outliers_present = (-1 in uniq_clusters)

    # 색상 매핑: 정상 클러스터 → 팔레트, outlier → 골드
    palette = _generate_colors(len(non_out))
    color_map: Dict[int, str] = {cid: palette[i] for i, cid in enumerate(non_out)}
    if outliers_present:
        color_map[-1] = "#FFD700"

    # 포인트 리스트
    points: List[Dict[str, Any]] = []
    for i, row in df.reset_index(drop=True).iterrows():
        pid = int(i)
        artist = str(row.get("Artist", ""))
        artist_ko = artist_labels.get(artist, "")
        title = str(row.get("Artwork", ""))
        # Year는 행 제거 없이, 숫자로 파싱 가능한 경우에만 int로 설정
        yn = row.get("Year_num")
        year = int(yn) if pd.notna(yn) else None
        cid = int(row.get("cluster"))
        px = float(row.get("x"))
        py = float(row.get("y"))
        point: Dict[str, Any] = {
            "id": pid,
            "artist": artist,
            "artist_ko": artist_ko,
            "title": title,
            # 숫자 시작 연도 (가능한 경우)
            "year": year if year is not None else None,
            # 원본 연도 문자열 보존
            "yearOriginal": str(row.get("Year", "")),
            "cluster": cid,
            "umapX": px,
            "umapY": py,
            # 선택 필드(프론트에서 사용 가능하지만 필수는 아님)
            "type": "outlier" if cid == -1 else "normal",
            "size": 1.0,
            "description": f"{artist} ({year})" if year is not None else f"{artist}",
            "tooltip": f"{title}\n{artist}, {year}" if year is not None else f"{title}\n{artist}",
        }
        points.append(point)

    # ==== (선택) 축 정보 병합: data/processed/bioartlas_axes_bilingual.csv 에서 per-row 축 라벨을 포인트에 주입 ====
    axes_present: List[str] = []
    try:
        if AXIS_CSV.exists():
            df_axes = pd.read_csv(AXIS_CSV, dtype=str, keep_default_na=False)
            # 사용 가능한 축 열 감지(영문 축 13개 중 존재하는 것만)
            axes_present = [a for a in AXIS_EN_COLUMNS if a in df_axes.columns]
            # KO 열(존재 시)
            axes_present_ko = [f"{a}_ko" for a in AXIS_EN_COLUMNS if f"{a}_ko" in df_axes.columns]
            # 조인 키 구성
            key_cols = [c for c in ["Artist", "Artwork", "Year"] if c in df_axes.columns and c in df.columns]
            if key_cols:
                # 키 문자열 생성
                def _k(df_in: pd.DataFrame) -> pd.Series:
                    return (
                        df_in[key_cols[0]].astype(str)
                        + "\u241F" + df_in[key_cols[1]].astype(str)
                        + "\u241F" + df_in[key_cols[2]].astype(str)
                    )
                left = df.copy()
                right = df_axes.copy()
                left["__k__"] = _k(left)
                right["__k__"] = _k(right)
                axes_map_en: Dict[str, Dict[str, str]] = {}
                axes_map_ko: Dict[str, Dict[str, str]] = {}
                for _, r in right.iterrows():
                    k = str(r["__k__"])
                    en_obj = {a: str(r.get(a, "")) for a in axes_present}
                    ko_obj = {a: str(r.get(f"{a}_ko", "")) for a in AXIS_EN_COLUMNS if f"{a}_ko" in right.columns}
                    axes_map_en[k] = en_obj
                    axes_map_ko[k] = ko_obj
                # 포인트에 주입
                for pt in points:
                    # 원본 df의 동일한 인덱스 i 가 pt['id']임을 가정
                    # 보다 견고하게는 키로 찾는다
                    try:
                        k = str(left.loc[pt["id"], "__k__"]) if "__k__" in left.columns else None
                    except Exception:
                        k = None
                    if k and k in axes_map_en:
                        pt["axes_en"] = axes_map_en[k]
                        if axes_map_ko.get(k):
                            pt["axes_ko"] = axes_map_ko[k]
            else:
                # 키가 없으면 행 순서로 주입(길이 일치 시)
                if len(df_axes) >= len(points):
                    for i, pt in enumerate(points):
                        r = df_axes.iloc[i]
                        en_obj = {a: str(r.get(a, "")) for a in axes_present}
                        ko_obj = {a: str(r.get(f"{a}_ko", "")) for a in AXIS_EN_COLUMNS if f"{a}_ko" in df_axes.columns}
                        pt["axes_en"] = en_obj
                        if ko_obj:
                            pt["axes_ko"] = ko_obj
    except Exception:
        # 축 병합 실패 시 조용히 건너뜀(기존 스키마 유지)
        axes_present = []

    # 클러스터 요약
    clusters_info: Dict[str, Dict[str, Any]] = {}
    for cid in uniq_clusters:
        mask = (df["cluster"] == cid)
        sub = df[mask]
        count = int(mask.sum())
        if count == 0:
            continue
        center_x = float(np.mean(sub["x"]))
        center_y = float(np.mean(sub["y"]))
        # 연도 범위
        try:
            # 클러스터 연도 범위도 숫자로 파싱된 Year_num 기반
            y_min = int(pd.to_numeric(sub["Year_num"], errors="coerce").min())
            y_max = int(pd.to_numeric(sub["Year_num"], errors="coerce").max())
            year_range = f"{y_min}-{y_max}" if y_min != y_max else str(y_min)
        except Exception:
            year_range = ""
        # 대표작(최대 3개)
        reps: List[Dict[str, Any]] = []
        for _, r in sub.head(3).iterrows():
            rep_artist = str(r.get("Artist", ""))
            reps.append({
                "artist": rep_artist,
                "artist_ko": artist_labels.get(rep_artist, ""),
                "title": str(r.get("Artwork", "")),
                # 대표작 연도도 숫자 시작 연도 사용
                "year": int(r.get("Year_num")) if pd.notna(r.get("Year_num")) else None,
                # 원본 연도 문자열 보존
                "year_original": str(r.get("Year", "")),
            })
        # 메인 아티스트 top-3
        top_artists = [str(a) for a in sub["Artist"].value_counts().head(3).index.tolist()]
        top_artists_ko = [artist_labels.get(artist, "") for artist in top_artists]
        clusters_info[str(cid)] = {
            "id": int(cid),
            "name": f"Cluster {cid}" if cid >= 0 else "Outliers",
            "color": color_map.get(int(cid), "#999999"),
            "count": count,
            "year_range": year_range,
            "center": {"x": center_x, "y": center_y},
            "type": "cluster" if cid >= 0 else "outlier",
            "representative_works": reps,
            "main_artists": top_artists,
            "main_artists_ko": top_artists_ko,
            # 호환 필드(현재 프론트에선 사용 안 함)
            "main_genre": "",
            "main_medium": "",
        }

    # 통계/메타
    total_artworks = int(len(df))
    uniq_nonneg = sorted([int(c) for c in uniq_clusters if c >= 0])
    n_clusters = int(len(uniq_nonneg))
    n_outliers = int((df["cluster"] < 0).sum())
    try:
        # 전체 연도 범위도 Year_num 기반으로 계산 (NaN 무시)
        y_series = pd.to_numeric(df["Year_num"], errors="coerce")
        if y_series.notna().any():
            y0 = int(y_series.min())
            y1 = int(y_series.max())
            year_range_all = f"{y0}-{y1}" if y0 != y1 else str(y0)
        else:
            year_range_all = ""
    except Exception:
        year_range_all = ""
    total_artists = int(df["Artist"].nunique())

    # 점수(meta에서 접근)
    try:
        sil = float((meta.get("best") or {}).get("score"))
    except Exception:
        sil = None

    # 클러스터링/시각화 메타 구성
    feature_key = str(((meta.get("feature") or {}).get("key")) or "")
    best_info = (meta.get("best") or {})
    best_algo = str(best_info.get("algo") or "")
    best_space = str(best_info.get("space") or "")
    best_meta = (best_info.get("meta") or {})
    try:
        best_k = int(best_meta.get("k")) if "k" in best_meta and str(best_meta.get("k")).strip() != "" else None
    except Exception:
        best_k = None
    # 07단계와 동일한 규칙으로 시각화 UMAP 메트릭 추정
    viz_metric_default = 'cosine' if feature_key in ('tfidf_counts_l2', 'tfidf_onehot_l2', 'tfidf_counts_bm25_l2') else 'euclidean'
    # 07단계 메타에서 시각화 임베딩 방식 파악 (예: 'UMAP[cosine]' 또는 't-SNE')
    emb_str = str(((meta.get("viz") or {}).get("embedding")) or "")
    if emb_str.lower().startswith("umap"):
        viz_method = "UMAP"
        m = re.search(r"\[(.*?)\]", emb_str)
        viz_metric_from_meta = (m.group(1) if m else viz_metric_default)
    elif emb_str.lower().startswith("t-sne") or emb_str.lower().startswith("tsne"):
        viz_method = "t-SNE"
        viz_metric_from_meta = None
    else:
        viz_method = "UMAP"
        viz_metric_from_meta = viz_metric_default

    # 시각화 메타: 방법별로 필요한 필드만 노출(UMAP 전용 파라미터가 t-SNE일 때 보이지 않도록)
    viz_meta: Dict[str, Any]
    if viz_method == "UMAP":
        viz_meta = {
            "method": "UMAP",
            "metric": viz_metric_from_meta,
            "n_neighbors": 15,
            "min_dist": 0.1,
            "spread": 1.0,
        }
    elif viz_method == "t-SNE":
        viz_meta = {
            "method": "t-SNE",
            # 07 단계의 기본 설정을 반영
            "perplexity": 15,
            "init": "random",
        }
    else:
        viz_meta = {"method": viz_method or "unknown"}

    metadata: Dict[str, Any] = {
        "title": "BioArtlas - 2D Visualization (best)",
        "description": "Phase C best clustering on codebook-applied features",
        "version": "2.0",
        "created": datetime.now().isoformat(),
        # 하위호환 필드(이전 프론트 코드 지원)
        "algorithm": best_algo or "KMeans",
        "parameters": {
            "feature_key": feature_key,
            "space": best_space,
            "k": best_k,
        },
        "statistics": {
            "total_artworks": total_artworks,
            "n_clusters": n_clusters,
            "n_outliers": n_outliers,
            "silhouette_score": sil if sil is not None else None,
            "noise_ratio": float(n_outliers) / float(max(1, total_artworks)),
            "year_range": year_range_all,
            "total_artists": total_artists,
        },
        # 상세 메타(신규)
        "clustering": {
            "algorithm": best_algo or "KMeans",
            "k": best_k if best_k is not None else n_clusters,
            "space": best_space or None,
            "feature_key": feature_key or None,
            "silhouette": sil if sil is not None else None,
        },
        "viz": viz_meta,
        # 프론트 확장을 위한 축 목록(존재하는 경우)
        "axes": axes_present or AXIS_EN_COLUMNS,
    }

    # 경계
    bounds = {
        "x": {"min": float(np.nanmin(df["x"].values)), "max": float(np.nanmax(df["x"].values))},
        "y": {"min": float(np.nanmin(df["y"].values)), "max": float(np.nanmax(df["y"].values))},
    }

    out_obj = {
        "metadata": metadata,
        "points": points,
        "clusters": clusters_info,
        # artists 섹션은 현재 프론트에서 직접 사용하지 않으므로 생략 가능
        "bounds": bounds,
        "viewport": {"default_scale": 1.0, "default_padding": 0.1},
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out_obj, f, ensure_ascii=False, indent=2)

    print("[08] Saved:")
    print(" -", OUT_JSON)
    print("[08] Source:", src_csv)


if __name__ == "__main__":
    main()
