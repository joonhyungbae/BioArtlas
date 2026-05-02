#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
06_apply_word_codebook.py
- 05에서 학습된 단어 코드북(클러스터)을 이용해 04의 토큰들을 클러스터 ID로 치환
- 산출물:
  - 행×축별 클러스터 ID 목록(JSONL)
  - 축별 원핫/카운트 행렬(.npz) 및 결합 행렬(.npz)
  - 클러스터 센터를 평균한 양자화 축 임베딩(.npz)
  - 메타/식별자 저장

고정 경로(인자 없음):
  - 04 산출물 디렉토리: artifacts/04_embedding/bge_large_en_v1_5/
    * axis_row_tokens.jsonl, ids.csv, meta.json
  - 05 산출물 디렉토리: artifacts/05_word_codebook/bge_large_en_v1_5/
    * word_to_cluster.csv, codebook_centers.npy, meta.json
  - 출력 디렉토리: artifacts/06_apply_codebook/bge_large_en_v1_5/
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Tuple
import os

import numpy as np
import pandas as pd
try:
    from sklearn.decomposition import TruncatedSVD
except Exception:
    TruncatedSVD = None  # optional


BASE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"
DIR_04 = ARTIFACTS_DIR / "04_embedding" / "bge_large_en_v1_5"
DIR_05 = ARTIFACTS_DIR / "05_word_codebook" / "bge_large_en_v1_5"
DIR_OUT = ARTIFACTS_DIR / "06_apply_codebook" / "bge_large_en_v1_5"

AXIS_EN_COLUMNS: List[str] = [
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

ACTIVE_AXES: List[str] = AXIS_EN_COLUMNS
ID_COLS: List[str] = ["Artist", "Artwork", "Year", "Gen"]


def slugify(name: str) -> str:
    import re
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def read_axis_row_tokens(jsonl_path: Path, expected_rows: int | None) -> List[Dict[str, List[str]]]:
    records: List[Dict[str, List[str]]] = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            records.append({k: list(v) for k, v in obj.items()})
    if expected_rows is not None and len(records) != expected_rows:
        print(f"[06][WARN] axis_row_tokens rows({len(records)}) != expected_rows({expected_rows})")
    return records


def build_cluster_matrices(
    axis_to_row_tokens: Dict[str, List[List[str]]],
    word_to_cluster: Dict[str, int],
    cluster_centers: np.ndarray,
    token_to_index: Dict[str, int] | None = None,
    token_embs_norm: np.ndarray | None = None,
    soft_topk: int = 1,
    soft_tau: float = 0.0,
) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray], Dict[str, np.ndarray]]:
    """축별 카운트/원핫 행렬과 양자화 임베딩을 생성.

    Returns:
      - axis_counts: {axis: (n_rows, n_clusters) float32}
      - axis_onehots: {axis: (n_rows, n_clusters) float32}
      - axis_quantized: {axis: (n_rows, dim) float32}  # 클러스터 센터 평균
    """
    axes = list(axis_to_row_tokens.keys())
    n_rows = len(next(iter(axis_to_row_tokens.values()))) if axes else 0
    n_clusters = int(cluster_centers.shape[0])
    dim = int(cluster_centers.shape[1])

    axis_counts: Dict[str, np.ndarray] = {}
    axis_onehots: Dict[str, np.ndarray] = {}
    axis_quantized: Dict[str, np.ndarray] = {}

    # 소프트 할당 사용 여부
    use_soft = soft_topk > 1 and token_to_index is not None and token_embs_norm is not None
    centers_norm = None
    if use_soft:
        eps = 1e-12
        norms = np.linalg.norm(cluster_centers, axis=1, keepdims=True) + eps
        centers_norm = (cluster_centers / norms).astype(np.float32)
        # 토큰별 top-k 캐시
        soft_cache: Dict[int, Tuple[np.ndarray, np.ndarray]] = {}

    for axis in ACTIVE_AXES:
        rows_tokens = axis_to_row_tokens.get(axis, [[] for _ in range(n_rows)])
        counts = np.zeros((n_rows, n_clusters), dtype=np.float32)
        for i, tokens in enumerate(rows_tokens):
            if not tokens:
                continue
            if not use_soft:
                for w in tokens:
                    cid = word_to_cluster.get(w)
                    if cid is None:
                        continue
                    counts[i, cid] += 1.0
            else:
                # 토큰을 클러스터로 soft top-k 분배 (코사인 유사도 기반)
                for w in tokens:
                    idx = token_to_index.get(w, -1) if isinstance(token_to_index, dict) else -1
                    if idx < 0:
                        # 임베딩 없으면 하드 매핑으로 보완
                        cid = word_to_cluster.get(w)
                        if cid is not None:
                            counts[i, cid] += 1.0
                        continue
                    if idx not in soft_cache:
                        v = token_embs_norm[idx]
                        sims = centers_norm @ v  # (K,)
                        # 음수는 0으로 클리핑(가중치 음수 방지)
                        sims = np.maximum(sims, 0.0)
                        if soft_topk >= n_clusters:
                            top_idx = np.arange(n_clusters, dtype=np.int32)
                            top_val = sims
                        else:
                            top_idx = np.argpartition(-sims, soft_topk-1)[:soft_topk]
                            top_val = sims[top_idx]
                        if soft_tau > 0:
                            wts = np.exp(top_val / float(soft_tau))
                        else:
                            wts = top_val
                        s = float(wts.sum())
                        if s <= 0:
                            # 전체 0이면 하드 최고값으로 1 할당
                            j = int(top_idx[np.argmax(top_val)])
                            soft_cache[idx] = (np.array([j], dtype=np.int32), np.array([1.0], dtype=np.float32))
                        else:
                            wts = (wts / s).astype(np.float32)
                            soft_cache[idx] = (top_idx.astype(np.int32), wts)
                    top_idx, wts = soft_cache[idx]
                    counts[i, top_idx] += wts
        axis_counts[axis] = counts
        onehot = (counts > 0).astype(np.float32)
        axis_onehots[axis] = onehot

        # 양자화 임베딩: 행별로 클러스터 센터를 카운트 가중 평균
        quant = np.zeros((n_rows, dim), dtype=np.float32)
        for i in range(n_rows):
            row_counts = counts[i]
            total = float(row_counts.sum())
            if total <= 0:
                continue
            weights = (row_counts / total).astype(np.float32)
            # weighted average of centers
            quant[i] = weights @ cluster_centers
        axis_quantized[axis] = quant

    return axis_counts, axis_onehots, axis_quantized


def main():
    import time
    t_start = time.time()
    DIR_OUT.mkdir(parents=True, exist_ok=True)

    # 04 산출물 로드
    jsonl_tokens = DIR_04 / "axis_row_tokens.jsonl"
    ids_csv = DIR_04 / "ids.csv"
    meta04 = DIR_04 / "meta.json"
    if not jsonl_tokens.exists():
        raise SystemExit("axis_row_tokens.jsonl 이 필요합니다. 04 단계를 먼저 실행하세요.")

    # 05 산출물 로드
    word_to_cluster_csv = DIR_05 / "word_to_cluster.csv"
    centers_npy = DIR_05 / "codebook_centers.npy"
    meta05 = DIR_05 / "meta.json"
    if not word_to_cluster_csv.exists() or not centers_npy.exists():
        raise SystemExit("word_codebook 산출물( word_to_cluster.csv / codebook_centers.npy )이 필요합니다. 05를 실행하세요.")

    # 메타 로깅
    try:
        with open(meta04, "r", encoding="utf-8") as f:
            meta_04_obj = json.load(f)
    except Exception:
        meta_04_obj = {}
    try:
        with open(meta05, "r", encoding="utf-8") as f:
            meta_05_obj = json.load(f)
    except Exception:
        meta_05_obj = {}

    # 행 수 및 ID 확보
    if ids_csv.exists():
        df_ids = pd.read_csv(ids_csv)
        n_rows = len(df_ids)
    else:
        df_ids = pd.DataFrame()
        n_rows = None  # unknown yet

    # 토큰 로드
    records = read_axis_row_tokens(jsonl_tokens, expected_rows=n_rows)
    if n_rows is None:
        n_rows = len(records)
    print(f"[06] Rows: {n_rows}")

    # axis -> row -> tokens 구조로 변환
    axis_to_row_tokens: Dict[str, List[List[str]]] = {axis: [[] for _ in range(n_rows)] for axis in ACTIVE_AXES}
    for i, obj in enumerate(records):
        for axis in ACTIVE_AXES:
            axis_to_row_tokens[axis][i] = list(obj.get(axis, []))

    # 코드북 로드
    df_map = pd.read_csv(word_to_cluster_csv)
    if "word" not in df_map.columns or "cluster" not in df_map.columns:
        raise SystemExit("word_to_cluster.csv에는 'word'와 'cluster' 컬럼이 필요합니다.")
    word_to_cluster: Dict[str, int] = {str(w): int(c) for w, c in zip(df_map["word"].astype(str), df_map["cluster"].astype(int))}
    centers = np.load(centers_npy).astype(np.float32)
    n_clusters = centers.shape[0]
    dim = centers.shape[1]
    print(f"[06] Codebook loaded: K={n_clusters}, dim={dim}")

    # 소프트 할당을 위한 토큰 임베딩 준비
    soft_topk = int(os.getenv("PHASEC_SOFT_TOPK", "1"))
    soft_tau = float(os.getenv("PHASEC_SOFT_TAU", "0.0"))
    token_to_index: Dict[str, int] | None = None
    token_embs_norm: np.ndarray | None = None
    if soft_topk > 1:
        tokens_vocab_csv = DIR_04 / "tokens_vocab.csv"
        # 토큰 임베딩 소스 자동 선택(05와 동일 정책 + 차원 일치 우선)
        order_env = os.getenv("PHASEC_TOKEN_EMB_ORDER", "combined_concat,combined_avg,secondary,primary")
        order = [o.strip().lower() for o in order_env.split(",") if o.strip()]
        cand_map = {
            "combined_concat": DIR_04 / "tokens_embeddings__combined_concat.npy",
            "combined_avg": DIR_04 / "tokens_embeddings__combined_avg.npy",
            "primary": DIR_04 / "tokens_embeddings.npy",
        }
        secondary_paths = [p for p in sorted(DIR_04.glob("tokens_embeddings__*.npy")) if "__combined_" not in p.name]
        candidates: List[Path] = []
        for key in order:
            if key in ("combined_concat", "combined_avg", "primary"):
                candidates.append(cand_map[key])
            elif key == "secondary":
                candidates.extend(secondary_paths)

        chosen_path: Path | None = None
        chosen_reason = ""
        # 1) 차원 일치 우선 선택
        for p in candidates:
            if not p.exists():
                continue
            try:
                tmp = np.load(p, mmap_mode='r')
                if tmp.ndim == 2 and tmp.shape[1] == dim:
                    chosen_path = p
                    chosen_reason = "match_dim"
                    break
            except Exception:
                continue
        # 2) 차원 불일치여도 첫 가용 경로 선택
        if chosen_path is None:
            for p in candidates:
                if p.exists():
                    chosen_path = p
                    chosen_reason = "fallback_first_available"
                    break

        if tokens_vocab_csv.exists() and chosen_path is not None and chosen_path.exists():
            print(f"[06] token embeddings source: {chosen_reason} -> {chosen_path}")
            df_vocab = pd.read_csv(tokens_vocab_csv)
            vocab_words = df_vocab["word"].astype(str).tolist() if "word" in df_vocab.columns else []
            token_to_index = {w: i for i, w in enumerate(vocab_words)}
            embs = np.load(chosen_path).astype(np.float32)
            # 차원 불일치 또는 강제 시, 여러 PCA 설정을 스윕해 코드북 센터와의 정렬도가 가장 높은 구성을 선택
            if embs.ndim == 2:
                need_pca = (embs.shape[1] != dim) or (os.getenv("PHASEC_TOKEN_PCA_FORCE", "false").lower() == "true")
                enable_auto_pca = os.getenv("PHASEC_TOKEN_PCA_ENABLE", "true").lower() == "true"
                if need_pca and enable_auto_pca:
                    try:
                        from sklearn.decomposition import PCA as _PCA
                    except Exception:
                        _PCA = None
                    def _alignment_score(embs_proj: np.ndarray) -> float:
                        # 토큰-클러스터 평균 임베딩과 코드북 센터의 평균 코사인 유사도
                        try:
                            # cid -> indices
                            idx_by_cid: Dict[int, List[int]] = {}
                            samples_per_cid = int(os.getenv("PHASEC_TOKEN_PCA_MAX_SAMPLES_PER_CLUSTER", "100"))
                            for w, cid in word_to_cluster.items():
                                idx = token_to_index.get(w, -1) if isinstance(token_to_index, dict) else -1
                                if idx < 0:
                                    continue
                                lst = idx_by_cid.get(int(cid))
                                if lst is None:
                                    idx_by_cid[int(cid)] = [idx]
                                else:
                                    if len(lst) < samples_per_cid:
                                        lst.append(idx)
                            valid_cids = sorted([c for c, lst in idx_by_cid.items() if len(lst) > 0])
                            if not valid_cids:
                                return float('-inf')
                            means: List[np.ndarray] = []
                            centers_sel: List[np.ndarray] = []
                            for c in valid_cids:
                                ii = idx_by_cid[c]
                                means.append(np.mean(embs_proj[ii, :], axis=0))
                                centers_sel.append(centers[c, :])
                            M = np.vstack(means).astype(np.float32)
                            C = np.vstack(centers_sel).astype(np.float32)
                            # cosine similarity row-wise
                            Mn = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-12)
                            Cn = C / (np.linalg.norm(C, axis=1, keepdims=True) + 1e-12)
                            sims = np.sum(Mn * Cn, axis=1)
                            return float(np.mean(sims))
                        except Exception:
                            return float('-inf')
                    best_score = float('-inf')
                    best_embs = None
                    best_cfg = None
                    # 후보 설정
                    solvers = [s.strip() for s in os.getenv("PHASEC_TOKEN_PCA_SOLVERS", "randomized,full").split(',') if s.strip()]
                    whitens = [w.strip().lower() == 'true' for w in os.getenv("PHASEC_TOKEN_PCA_WHITEN", "false,true").split(',') if w.strip()]
                    rs = int(os.getenv("PHASEC_TOKEN_PCA_RANDOM_STATE", "42") or 42)
                    fit_max = int(os.getenv("PHASEC_TOKEN_PCA_MAX_TOKENS", "200000") or 200000)
                    # 피팅 샘플 서브샘플링(속도)
                    rng = np.random.default_rng(rs)
                    X_fit = embs
                    if X_fit.shape[0] > fit_max:
                        idx = rng.choice(X_fit.shape[0], size=fit_max, replace=False)
                        X_fit = X_fit[idx]
                    if _PCA is None:
                        print("[06][WARN] sklearn PCA not available; skipping PCA alignment.")
                    else:
                        for solver in solvers:
                            for whiten in whitens:
                                try:
                                    pca = _PCA(n_components=dim, svd_solver=solver, whiten=whiten, random_state=rs)
                                    pca.fit(X_fit)
                                    embs_p = pca.transform(embs)
                                    score = _alignment_score(embs_p)
                                    if np.isfinite(score) and score > best_score:
                                        best_score = score
                                        best_embs = embs_p
                                        best_cfg = {"solver": solver, "whiten": bool(whiten)}
                                except Exception:
                                    continue
                    if best_embs is not None and best_embs.ndim == 2 and best_embs.shape[1] == dim:
                        print(f"[06] Token PCA selected: solver={best_cfg.get('solver')} whiten={best_cfg.get('whiten')} | align_cos={best_score:.4f}")
                        embs = best_embs.astype(np.float32)
                    else:
                        if embs.shape[1] != dim:
                            print(f"[06][WARN] PCA alignment failed; token emb dim {embs.shape[1]} != center dim {dim}. Disabling soft assignment.")
                            soft_topk = 1
                            soft_tau = 0.0
                            token_to_index = None
                            token_embs_norm = None
            # 최종 차원 점검
            if embs.ndim != 2 or embs.shape[1] != dim:
                print(f"[06][WARN] token embedding dim ({embs.shape[1] if embs.ndim==2 else 'NA'}) != codebook center dim ({dim}); disabling soft assignment.")
                soft_topk = 1
                soft_tau = 0.0
                token_to_index = None
                token_embs_norm = None
            else:
                # L2 정규화
                norm = np.linalg.norm(embs, axis=1, keepdims=True) + 1e-12
                token_embs_norm = (embs / norm).astype(np.float32)
                print(f"[06] Soft assignment enabled: topk={soft_topk}, tau={soft_tau} (token_embs={token_embs_norm.shape})")
        else:
            print("[06][WARN] Soft assignment requested but tokens vocab/embeddings missing; falling back to hard counts.")
            soft_topk = 1
            soft_tau = 0.0

    # 축별 행렬 및 양자화 임베딩 생성
    print("[06] Building per-axis count/onehot and quantized embeddings ...")
    axis_counts, axis_onehots, axis_quantized = build_cluster_matrices(
        axis_to_row_tokens,
        word_to_cluster,
        centers,
        token_to_index=token_to_index,
        token_embs_norm=token_embs_norm,
        soft_topk=soft_topk,
        soft_tau=soft_tau,
    )

    # 행×축별 클러스터 ID 목록(JSONL) 저장
    print("[06] Writing axis_row_cluster_ids.jsonl ...")
    out_jsonl = DIR_OUT / "axis_row_cluster_ids.jsonl"
    with open(out_jsonl, "w", encoding="utf-8") as f:
        for i in range(n_rows):
            obj: Dict[str, List[int]] = {}
            for axis in ACTIVE_AXES:
                tokens = axis_to_row_tokens[axis][i]
                cids: List[int] = []
                for w in tokens:
                    cid = word_to_cluster.get(w)
                    if cid is not None:
                        cids.append(int(cid))
                obj[axis] = cids
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    # 행×축별 클러스터 ID 목록(CSV) 저장: 각 축 컬럼에 "cid1|cid2|..." 형태로 기록
    print("[06] Writing axis_row_cluster_ids.csv ...")
    cid_rows: List[Dict[str, str]] = []
    for i in range(n_rows):
        row_dict: Dict[str, str] = {}
        for axis in ACTIVE_AXES:
            tokens = axis_to_row_tokens[axis][i]
            cids = [word_to_cluster[w] for w in tokens if w in word_to_cluster]
            # 중복 제거 후 정렬
            uniq = sorted(set(int(c) for c in cids))
            row_dict[axis] = "|".join(map(str, uniq))
        cid_rows.append(row_dict)
    df_cids = pd.DataFrame(cid_rows)
    if not df_ids.empty:
        df_cids = pd.concat([df_ids.reset_index(drop=True), df_cids], axis=1)
    df_cids.to_csv(DIR_OUT / "axis_row_cluster_ids.csv", index=False)

    # 축별 .npz 저장
    np.savez_compressed(DIR_OUT / "axis_cluster_counts.npz", **{slugify(a): m for a, m in axis_counts.items()})
    np.savez_compressed(DIR_OUT / "axis_cluster_onehot.npz", **{slugify(a): m for a, m in axis_onehots.items()})
    np.savez_compressed(DIR_OUT / "axis_quantized_embeddings.npz", **{slugify(a): m for a, m in axis_quantized.items()})

    # 결합 전 축 블록 L2 정규화 옵션
    do_axis_block_l2 = os.getenv("PHASEC_AXIS_BLOCK_L2", "false").lower() == "true"
    do_axis_block_l2_quant = os.getenv("PHASEC_AXIS_BLOCK_L2_QUANT", "false").lower() == "true"
    def _l2_norm_rows(M: np.ndarray) -> np.ndarray:
        nrm = np.linalg.norm(M, axis=1, keepdims=True) + 1e-12
        return (M / nrm).astype(np.float32)

    # 결합 행렬/임베딩 저장
    blocks_counts = []
    blocks_onehot = []
    blocks_quant = []
    for a in ACTIVE_AXES:
        mc = axis_counts[a]
        mo = axis_onehots[a]
        mq = axis_quantized[a]
        if do_axis_block_l2:
            if mc.size:
                mc = _l2_norm_rows(mc)
            if mo.size:
                mo = _l2_norm_rows(mo)
        if do_axis_block_l2_quant and mq.size:
            mq = _l2_norm_rows(mq)
        blocks_counts.append(mc)
        blocks_onehot.append(mo)
        blocks_quant.append(mq)

    counts_mat = np.concatenate(blocks_counts, axis=1)
    onehot_mat = np.concatenate(blocks_onehot, axis=1)
    quant_mat = np.concatenate(blocks_quant, axis=1)
    np.savez_compressed(DIR_OUT / "combined_cluster_counts.npz", combined=counts_mat)
    np.savez_compressed(DIR_OUT / "combined_cluster_onehot.npz", combined=onehot_mat)
    np.savez_compressed(DIR_OUT / "combined_quantized_embeddings.npz", combined=quant_mat)

    # 식별자 저장(그대로 전달)
    if not df_ids.empty:
        df_ids.to_csv(DIR_OUT / "ids.csv", index=False)

    # 메타 저장
    meta = {
        "source_04": {
            "axis_row_tokens": str(jsonl_tokens),
            "meta": str(meta04),
        },
        "source_05": {
            "word_to_cluster": str(word_to_cluster_csv),
            "cluster_centers": str(centers_npy),
            "meta": str(meta05),
        },
        "axes": ACTIVE_AXES,
        "rows": int(n_rows),
        "n_clusters": int(n_clusters),
        "center_dim": int(dim),
        "outputs": {
            "axis_row_cluster_ids": str(out_jsonl),
            "axis_cluster_counts": str(DIR_OUT / "axis_cluster_counts.npz"),
            "axis_cluster_onehot": str(DIR_OUT / "axis_cluster_onehot.npz"),
            "axis_quantized_embeddings": str(DIR_OUT / "axis_quantized_embeddings.npz"),
            "combined_cluster_counts": str(DIR_OUT / "combined_cluster_counts.npz"),
            "combined_cluster_onehot": str(DIR_OUT / "combined_cluster_onehot.npz"),
            "combined_quantized_embeddings": str(DIR_OUT / "combined_quantized_embeddings.npz"),
        },
    }
    with open(DIR_OUT / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # CSV 내보내기 (결합 행렬 + 축별 개별 CSV)
    print("[06] Writing CSV exports ...")
    # 결합 컬럼 이름 구성
    def _combined_columns(is_counts: bool, is_onehot: bool, is_quant: bool) -> List[str]:
        cols: List[str] = []
        if is_counts or is_onehot:
            # cluster columns per axis
            for axis in ACTIVE_AXES:
                slug = slugify(axis)
                for cid in range(n_clusters):
                    cols.append(f"{slug}__c{cid}")
        elif is_quant:
            # feature dims per axis
            for axis in ACTIVE_AXES:
                slug = slugify(axis)
                for j in range(dim):
                    cols.append(f"{slug}__f{j}")
        return cols

    # IDs 프리픽스
    id_df_out = df_ids.copy() if not df_ids.empty else pd.DataFrame({"row": np.arange(counts_mat.shape[0])})

    # combined counts
    try:
        cols_counts = _combined_columns(is_counts=True, is_onehot=False, is_quant=False)
        df_counts = pd.concat([id_df_out.reset_index(drop=True), pd.DataFrame(counts_mat, columns=cols_counts)], axis=1)
        df_counts.to_csv(DIR_OUT / "combined_cluster_counts.csv", index=False)
    except Exception as e:
        print(f"[06][WARN] Failed to write combined_cluster_counts.csv: {e}")

    # combined onehot
    try:
        cols_onehot = _combined_columns(is_counts=False, is_onehot=True, is_quant=False)
        df_onehot = pd.concat([id_df_out.reset_index(drop=True), pd.DataFrame(onehot_mat, columns=cols_onehot)], axis=1)
        df_onehot.to_csv(DIR_OUT / "combined_cluster_onehot.csv", index=False)
    except Exception as e:
        print(f"[06][WARN] Failed to write combined_cluster_onehot.csv: {e}")

    # combined quantized embeddings
    try:
        cols_quant = _combined_columns(is_counts=False, is_onehot=False, is_quant=True)
        df_quant = pd.concat([id_df_out.reset_index(drop=True), pd.DataFrame(quant_mat, columns=cols_quant)], axis=1)
        df_quant.to_csv(DIR_OUT / "combined_quantized_embeddings.csv", index=False)
    except Exception as e:
        print(f"[06][WARN] Failed to write combined_quantized_embeddings.csv: {e}")

    # ============ TF-IDF/BM25 파생 특징 생성 ============
    N = counts_mat.shape[0]
    # per-axis block별로 동일한 K를 가정
    K = n_clusters
    # 문서빈도 df: 각 컬럼에서 >0 인 행 수
    df_vec = (counts_mat > 0).sum(axis=0).astype(np.int64)
    # IDF: log((N+1)/(df+1)) + 1 (smoothed)
    idf_vec = np.log((N + 1) / (df_vec + 1)) + 1.0
    # TF-IDF (counts)
    tfidf_counts = counts_mat * idf_vec
    # TF-IDF (onehot)
    tfidf_onehot = onehot_mat * idf_vec
    # 행 L2 정규화
    def _l2_normalize(X: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(X, axis=1, keepdims=True) + 1e-12
        return (X / norm).astype(np.float32)
    tfidf_counts_l2 = _l2_normalize(tfidf_counts)
    tfidf_onehot_l2 = _l2_normalize(tfidf_onehot)

    # BM25 옵션: 포화 TF 가중
    use_bm25 = os.getenv("PHASEC_USE_BM25", "false").lower() == "true"
    k1 = float(os.getenv("PHASEC_BM25_K1", "1.2"))
    b = float(os.getenv("PHASEC_BM25_B", "0.75"))
    tfidf_counts_bm25 = None
    tfidf_counts_bm25_l2 = None
    if use_bm25:
        # 문서 길이 정규화
        doc_len = counts_mat.sum(axis=1, keepdims=True)
        avgdl = float(np.maximum(doc_len.mean(), 1e-12))
        # BM25 TF
        tf_bm25 = ((counts_mat * (k1 + 1.0)) /
                   (counts_mat + k1 * (1.0 - b + b * (doc_len / (avgdl + 1e-12)))))
        tfidf_counts_bm25 = (tf_bm25 * idf_vec).astype(np.float32)
        # L2 정규화
        tfidf_counts_bm25_l2 = _l2_normalize(tfidf_counts_bm25)

    # 저장: TF-IDF 원본 + L2 (+BM25)
    np.savez_compressed(DIR_OUT / "combined_tfidf_counts.npz", combined=tfidf_counts.astype(np.float32))
    np.savez_compressed(DIR_OUT / "combined_tfidf_onehot.npz", combined=tfidf_onehot.astype(np.float32))
    np.savez_compressed(DIR_OUT / "combined_tfidf_counts_l2.npz", combined=tfidf_counts_l2)
    np.savez_compressed(DIR_OUT / "combined_tfidf_onehot_l2.npz", combined=tfidf_onehot_l2)
    if use_bm25 and tfidf_counts_bm25 is not None:
        np.savez_compressed(DIR_OUT / "combined_tfidf_counts_bm25.npz", combined=tfidf_counts_bm25)
        np.savez_compressed(DIR_OUT / "combined_tfidf_counts_bm25_l2.npz", combined=tfidf_counts_bm25_l2)

    # CSV도 저장 (L2 버전 기준)
    try:
        df_tfidf_c = pd.concat([id_df_out.reset_index(drop=True), pd.DataFrame(tfidf_counts_l2, columns=cols_counts)], axis=1)
        df_tfidf_c.to_csv(DIR_OUT / "combined_tfidf_counts_l2.csv", index=False)
        df_tfidf_o = pd.concat([id_df_out.reset_index(drop=True), pd.DataFrame(tfidf_onehot_l2, columns=cols_onehot)], axis=1)
        df_tfidf_o.to_csv(DIR_OUT / "combined_tfidf_onehot_l2.csv", index=False)
        if use_bm25 and tfidf_counts_bm25_l2 is not None:
            df_tfidf_bm25 = pd.concat([id_df_out.reset_index(drop=True), pd.DataFrame(tfidf_counts_bm25_l2, columns=cols_counts)], axis=1)
            df_tfidf_bm25.to_csv(DIR_OUT / "combined_tfidf_counts_bm25_l2.csv", index=False)
    except Exception as e:
        print(f"[06][WARN] Failed to write TF-IDF CSVs: {e}")

    # SVD 축소(optional)
    if TruncatedSVD is not None:
        try:
            # 안전한 컴포넌트 수 산정: n_components <= min(n_samples-1, n_features-1, 100)
            n_samples, n_features = tfidf_counts_l2.shape
            max_comp = max(2, min(100, n_samples - 1, n_features - 1)) if n_features > 1 and n_samples > 1 else 1
            n_components = int(max_comp)
            svd = TruncatedSVD(n_components=n_components, random_state=42)
            X_svd_counts = svd.fit_transform(tfidf_counts_l2).astype(np.float32)
            np.savez_compressed(DIR_OUT / "combined_tfidf_counts_svd100.npz", combined=X_svd_counts)
            # onehot도 동일 파이프라인으로 축소
            svd2 = TruncatedSVD(n_components=n_components, random_state=42)
            X_svd_onehot = svd2.fit_transform(tfidf_onehot_l2).astype(np.float32)
            np.savez_compressed(DIR_OUT / "combined_tfidf_onehot_svd100.npz", combined=X_svd_onehot)
            # BM25 버전도 축소 저장(옵션)
            if use_bm25 and tfidf_counts_bm25_l2 is not None:
                svd3 = TruncatedSVD(n_components=n_components, random_state=42)
                X_svd_bm25 = svd3.fit_transform(tfidf_counts_bm25_l2).astype(np.float32)
                np.savez_compressed(DIR_OUT / "combined_tfidf_counts_bm25_svd100.npz", combined=X_svd_bm25)
            # CSV 저장(실제 산출 차원에 맞춰 컬럼 생성)
            cols_counts = [f"svd{i}" for i in range(int(X_svd_counts.shape[1]))]
            pd.concat([id_df_out.reset_index(drop=True), pd.DataFrame(X_svd_counts, columns=cols_counts)], axis=1).to_csv(
                DIR_OUT / "combined_tfidf_counts_svd100.csv", index=False
            )
            cols_onehot = [f"svd{i}" for i in range(int(X_svd_onehot.shape[1]))]
            pd.concat([id_df_out.reset_index(drop=True), pd.DataFrame(X_svd_onehot, columns=cols_onehot)], axis=1).to_csv(
                DIR_OUT / "combined_tfidf_onehot_svd100.csv", index=False
            )
            if use_bm25 and tfidf_counts_bm25_l2 is not None:
                cols_bm25 = [f"svd{i}" for i in range(int(X_svd_bm25.shape[1]))]
                pd.concat([id_df_out.reset_index(drop=True), pd.DataFrame(X_svd_bm25, columns=cols_bm25)], axis=1).to_csv(
                    DIR_OUT / "combined_tfidf_counts_bm25_svd100.csv", index=False
                )
            print(f"[06] Saved SVD features (n_components={n_components})")
        except Exception as e:
            print(f"[06][WARN] TruncatedSVD failed: {e}")
    else:
        print("[06][INFO] sklearn TruncatedSVD not available; skipping SVD features")

    # per-axis CSVs
    try:
        for axis in ACTIVE_AXES:
            slug = slugify(axis)
            # counts
            df_ax_c = pd.concat([id_df_out.reset_index(drop=True), pd.DataFrame(axis_counts[axis], columns=[f"c{cid}" for cid in range(n_clusters)])], axis=1)
            df_ax_c.to_csv(DIR_OUT / f"axis_counts__{slug}.csv", index=False)
            # onehot
            df_ax_o = pd.concat([id_df_out.reset_index(drop=True), pd.DataFrame(axis_onehots[axis], columns=[f"c{cid}" for cid in range(n_clusters)])], axis=1)
            df_ax_o.to_csv(DIR_OUT / f"axis_onehot__{slug}.csv", index=False)
            # quantized embeddings
            df_ax_q = pd.concat([id_df_out.reset_index(drop=True), pd.DataFrame(axis_quantized[axis], columns=[f"f{j}" for j in range(dim)])], axis=1)
            df_ax_q.to_csv(DIR_OUT / f"axis_quantized__{slug}.csv", index=False)
    except Exception as e:
        print(f"[06][WARN] Failed to write per-axis CSVs: {e}")

    print("[06] Saved:")
    print(" -", out_jsonl)
    print(" -", DIR_OUT / "axis_cluster_counts.npz")
    print(" -", DIR_OUT / "axis_cluster_onehot.npz")
    print(" -", DIR_OUT / "axis_quantized_embeddings.npz")
    print(" -", DIR_OUT / "combined_cluster_counts.npz")
    print(" -", DIR_OUT / "combined_cluster_onehot.npz")
    print(" -", DIR_OUT / "combined_quantized_embeddings.npz")
    print(" -", DIR_OUT / "axis_row_cluster_ids.csv")
    print(" -", DIR_OUT / "combined_cluster_counts.csv")
    print(" -", DIR_OUT / "combined_cluster_onehot.csv")
    print(" -", DIR_OUT / "combined_quantized_embeddings.csv")
    print(" -", DIR_OUT / "combined_tfidf_counts.npz")
    print(" -", DIR_OUT / "combined_tfidf_onehot.npz")
    print(" -", DIR_OUT / "combined_tfidf_counts_l2.npz")
    print(" -", DIR_OUT / "combined_tfidf_onehot_l2.npz")
    if os.getenv("PHASEC_USE_BM25", "false").lower() == "true":
        print(" -", DIR_OUT / "combined_tfidf_counts_bm25.npz")
        print(" -", DIR_OUT / "combined_tfidf_counts_bm25_l2.npz")
    print(" -", DIR_OUT / "combined_tfidf_counts_l2.csv")
    print(" -", DIR_OUT / "combined_tfidf_onehot_l2.csv")
    if TruncatedSVD is not None:
        print(" -", DIR_OUT / "combined_tfidf_counts_svd100.npz")
        print(" -", DIR_OUT / "combined_tfidf_onehot_svd100.npz")
        print(" -", DIR_OUT / "combined_tfidf_counts_svd100.csv")
        print(" -", DIR_OUT / "combined_tfidf_onehot_svd100.csv")
        if os.getenv("PHASEC_USE_BM25", "false").lower() == "true":
            print(" -", DIR_OUT / "combined_tfidf_counts_bm25_svd100.npz")
            print(" -", DIR_OUT / "combined_tfidf_counts_bm25_svd100.csv")
    if not df_ids.empty:
        print(" -", DIR_OUT / "ids.csv")
    print(" -", DIR_OUT / "meta.json")

    # ========= 논문 보고용 메트릭 저장 =========
    try:
        def _density(X: np.ndarray) -> float:
            if X.size == 0:
                return 0.0
            return float((X != 0).sum() / X.size)
        def _row_nnz(X: np.ndarray) -> float:
            if X.size == 0:
                return 0.0
            return float((X != 0).sum(axis=1).mean())
        def _row_l2_mean(X: np.ndarray) -> float:
            if X.size == 0:
                return 0.0
            nrm = np.linalg.norm(X, axis=1)
            return float(nrm.mean())

        metrics = {
            "rows": int(n_rows),
            "n_clusters": int(n_clusters),
            "center_dim": int(dim),
            "axis_block_l2": bool(do_axis_block_l2),
            "axis_block_l2_quant": bool(do_axis_block_l2_quant),
            "features": {
                "counts": {
                    "shape": list(map(int, list(counts_mat.shape))),
                    "density": _density(counts_mat),
                    "row_nnz_mean": _row_nnz(counts_mat),
                    "row_l2_mean": _row_l2_mean(counts_mat),
                },
                "onehot": {
                    "shape": list(map(int, list(onehot_mat.shape))),
                    "density": _density(onehot_mat),
                    "row_nnz_mean": _row_nnz(onehot_mat),
                    "row_l2_mean": _row_l2_mean(onehot_mat),
                },
                "quantized": {
                    "shape": list(map(int, list(quant_mat.shape))),
                    "row_l2_mean": _row_l2_mean(quant_mat),
                },
            },
            "tfidf": {
                "counts_l2": {
                    "exists": bool((DIR_OUT / "combined_tfidf_counts_l2.npz").exists()),
                },
                "onehot_l2": {
                    "exists": bool((DIR_OUT / "combined_tfidf_onehot_l2.npz").exists()),
                },
                "bm25": bool(os.getenv("PHASEC_USE_BM25", "false").lower() == "true"),
            },
            "runtime_sec": float(time.time() - t_start),
            "env": {
                "PHASEC_USE_BM25": os.getenv("PHASEC_USE_BM25", ""),
                "PHASEC_BM25_K1": os.getenv("PHASEC_BM25_K1", ""),
                "PHASEC_BM25_B": os.getenv("PHASEC_BM25_B", ""),
                "PHASEC_AXIS_BLOCK_L2": os.getenv("PHASEC_AXIS_BLOCK_L2", ""),
                "PHASEC_AXIS_BLOCK_L2_QUANT": os.getenv("PHASEC_AXIS_BLOCK_L2_QUANT", ""),
            },
        }
        with open(DIR_OUT / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)
        # summary CSV(테이블용)
        pd.DataFrame([{
            "rows": metrics["rows"],
            "n_clusters": metrics["n_clusters"],
            "center_dim": metrics["center_dim"],
            "counts_density": metrics["features"]["counts"]["density"],
            "onehot_density": metrics["features"]["onehot"]["density"],
            "quant_row_l2": metrics["features"]["quantized"]["row_l2_mean"],
            "bm25": metrics["tfidf"]["bm25"],
            "runtime_sec": metrics["runtime_sec"],
        }]).to_csv(DIR_OUT / "metrics_summary.csv", index=False)
        print("[06] Saved:", DIR_OUT / "metrics.json")
        print("[06] Saved:", DIR_OUT / "metrics_summary.csv")
    except Exception as e:
        print(f"[06][WARN] Failed to save paper metrics: {e}")



if __name__ == "__main__":
    main()
