#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
05_build_word_codebook.py
- 공개된 data/dataset/BioArtlas.csv에서 축별 텍스트를 동일한 규칙으로 토크나이즈
- 유니크 단어를 임베딩(BAAI/bge-large-en-v1.5) → KMeans로 단어 클러스터(코드북) 생성
- 각 축의 단어를 해당 클러스터 ID로 매핑 후, 행(row)×축별 원-핫/카운트 벡터 생성
- 결과물:
  - codebook(클러스터 센트로이드 포함) 및 메타데이터 저장
  - word_to_cluster.csv (단어-클러스터 매핑 + 빈도)
  - 축별(one-hot) 행렬(.npz)과 결합 행렬(.npz), 식별자(ids.csv)

기본 설정:
- 클러스터링: KMeans (필요 시 MiniBatchKMeans 옵션)
- 토크나이저: 04_build_embeddings.py의 `_split_to_words`와 동일 정규식
"""

from __future__ import annotations
import json
import pickle
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer
import os
import time
import hashlib
import sys
import platform

try:
    from sklearn.cluster import KMeans, MiniBatchKMeans
    from sklearn.metrics import silhouette_score
    from sklearn.decomposition import PCA
except Exception as e:  # pragma: no cover
    raise SystemExit("scikit-learn이 필요합니다. `pip install scikit-learn` 후 다시 시도하세요.")

# 시각화(선택적)
try:  # pragma: no cover
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MPL = True
except Exception:
    HAS_MPL = False


# 경로 및 상수 (04_build_embeddings.py와 동일 기본값 사용)
BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
DATA_DIR = REPO_ROOT / "data"
DATASET_DIR = DATA_DIR / "dataset"
ARTIFACTS_DIR = BASE_DIR / "artifacts"
DEFAULT_INPUT = DATASET_DIR / "BioArtlas.csv"
DEFAULT_MODEL = "BAAI/bge-large-en-v1.5"
DEFAULT_OUTDIR = ARTIFACTS_DIR / "05_word_codebook" / "bge_large_en_v1_5"
DEFAULT_SOURCE_EMB_DIR = ARTIFACTS_DIR / "04_embedding" / "bge_large_en_v1_5"

# 04의 축 정의를 그대로 복사
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
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def split_to_words(text: str) -> List[str]:
    """04_build_embeddings.py의 `_split_to_words`와 동일 규칙.
    알파뉴메릭/하이픈/아포스트로피를 포함한 토큰을 추출.
    """
    if not isinstance(text, str) or not text.strip():
        return []
    return [w for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-']*", text) if w]


def build_axis_words(df: pd.DataFrame) -> Tuple[Dict[str, List[List[str]]], Counter, List[str]]:
    """축별 단어 리스트 구성 및 전체 단어 빈도 카운트.

    Returns:
      - axis_to_row_words: {axis: [[w1, w2, ...] for each row]}
      - vocab_counter: 단어 → 전체 빈도
      - vocab_list: 유니크 단어 리스트 (빈도 내림차순)
    """
    axis_to_row_words: Dict[str, List[List[str]]] = {}
    vocab_counter: Counter = Counter()

    # 불용어/토큰 필터 설정
    use_stop = (os.getenv("PHASEC_STOPWORD_FILTER", "true").lower() == "true")
    STOP = {
        'the','and','of','in','on','for','to','a','an','is','are','be','with','by','from','as','at','or','not','no',
        'this','that','these','those','it','its','into','their','his','her','our','your','my','we','you','they','he','she',
        'was','were','been','being','than','then','there','here','over','under','up','down','out','through','across'
    }
    def _valid_token(t: str) -> bool:
        if not isinstance(t, str) or not t:
            return False
        if len(t) < 2:
            return False
        if t.isnumeric():
            return False
        if use_stop and t.lower() in STOP:
            return False
        return True

    for axis in ACTIVE_AXES:
        words_per_row: List[List[str]] = []
        s = df[axis] if axis in df.columns else pd.Series([""] * len(df))
        for val in s.tolist():
            words = [w for w in split_to_words(val) if _valid_token(w)]
            words_per_row.append(words)
            vocab_counter.update(words)
        axis_to_row_words[axis] = words_per_row

    # 유니크 단어를 빈도 내림차순으로 정렬
    vocab_list = [w for w, _ in vocab_counter.most_common()]
    return axis_to_row_words, vocab_counter, vocab_list


def embed_tokens(model: SentenceTransformer, tokens: List[str], batch_size: int, normalize: bool) -> np.ndarray:
    if not tokens:
        return np.zeros((0, model.get_sentence_embedding_dimension()), dtype=np.float32)
    emb = model.encode(
        tokens,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=normalize,
    )
    return emb.astype(np.float32)


def select_k_automatically(
    X: np.ndarray,
    use_minibatch: bool,
    random_state: int,
    max_iter: int,
    candidate_ks: List[int] | None = None,
    sample_for_silhouette: int = 20000,
) -> Dict[str, object]:
    """유니크 토큰 임베딩으로부터 K를 자동 선택.

    - 후보 K들 각각에 대해 (MiniBatch)KMeans 학습
    - 실루엣 스코어(유클리드, 임베딩이 정규화되어 있으면 코사인에 상응)를 샘플 기반으로 계산
    - 최고 점수의 K를 선택하되, 동점이면 더 작은 K 선호
    Returns metadata dict: {"chosen_k", "scores": {k: score}, "sample_size"}
    """
    import os
    n = X.shape[0]
    if candidate_ks is None:
        # n 규모에 따라 자동 후보 구성(세분화)
        base = [32, 48, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448, 480, 512, 576, 640, 768, 896, 1024]
        root_n = int(max(4, np.sqrt(n)))
        around_root = [root_n, int(root_n * 1.5), root_n * 2]
        candidate_ks = sorted({k for k in (base + around_root) if 4 <= k < n})
        # 목표 평균 클러스터 크기 기반 후보 보강
        try:
            target_avg = int(os.getenv("PHASEC_CODEBOOK_TARGET_AVG_CLUSTER_SIZE", "0"))
        except Exception:
            target_avg = 0
        if target_avg and target_avg > 0:
            k_t = max(4, min(n - 1, int(round(n / float(target_avg)))))
            for r in (0.8, 1.0, 1.25):
                candidate_ks.append(max(4, min(n - 1, int(round(k_t * r)))))
        # 최대 K 제한
        try:
            max_k = int(os.getenv("PHASEC_CODEBOOK_MAX_K", "0"))
        except Exception:
            max_k = 0
        if max_k and max_k > 0:
            candidate_ks = [k for k in candidate_ks if k <= max_k]
        # 고유화 및 정렬
        candidate_ks = sorted({int(k) for k in candidate_ks if 4 <= int(k) < n})
        if not candidate_ks:
            candidate_ks = [min(max(4, n // 50), max(2, n - 1))]

    # 샘플 선택(실루엣 계산 비용 절감)
    if n > sample_for_silhouette:
        rng = np.random.default_rng(seed=random_state)
        idx = rng.choice(n, size=sample_for_silhouette, replace=False)
        X_sil = X[idx]
    else:
        X_sil = X

    k_to_score: Dict[int, float] = {}
    k_to_score_adj: Dict[int, float] = {}
    # 추가: Calinski-Harabasz, Davies-Bouldin 점수 맵
    k_to_score_ch: Dict[int, float] = {}
    k_to_score_db: Dict[int, float] = {}
    # 패널티 계수(강화)
    def _getf(name: str, default: float) -> float:
        try:
            return float(os.getenv(name, str(default)))
        except Exception:
            return default
    alpha_singleton = _getf("PHASEC_ALPHA_SINGLETON", 0.6)
    alpha_empty = _getf("PHASEC_ALPHA_EMPTY", 0.8)
    alpha_gini = _getf("PHASEC_ALPHA_GINI", 0.2)
    singleton_max_ratio = _getf("PHASEC_SINGLETON_MAX_RATIO", 0.35)
    used_min_ratio = _getf("PHASEC_USED_MIN_RATIO", 0.7)
    for k in candidate_ks:
        if use_minibatch:
            km = MiniBatchKMeans(
                n_clusters=k,
                random_state=random_state,
                batch_size=2048,
                max_iter=max_iter,
                n_init="auto",
                verbose=0,
            )
        else:
            km = KMeans(
                n_clusters=k,
                random_state=random_state,
                max_iter=max_iter,
                n_init="auto",
                verbose=0,
            )
        km.fit(X)
        # 실루엣은 샘플 위에서 계산
        labels = km.predict(X_sil)
        # 유클리드(정규화 벡터면 코사인과 단조 관계)
        try:
            score = float(silhouette_score(X_sil, labels, metric="euclidean"))
        except Exception:
            score = float("nan")
        # CH/DB 점수 (전체 X, 예외 시 NaN)
        try:
            from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score
            labels_full = km.predict(X)
            ch = float(calinski_harabasz_score(X, labels_full))
            db = float(davies_bouldin_score(X, labels_full))
        except Exception:
            ch, db = float('nan'), float('nan')
        # 전체 라벨로 사용/단일/빈 클러스터 패널티 계산
        labels_full = km.predict(X)
        unique, counts = np.unique(labels_full, return_counts=True)
        used_k = int(unique.shape[0])
        singleton = int((counts == 1).sum())
        empty = int(k - used_k)
        singleton_ratio = singleton / float(k)
        empty_ratio = empty / float(k)
        # 불균형(지니) 계산
        if counts.size > 0:
            p = counts / counts.sum()
            gini = 1.0 - float(np.sum(p * p))
        else:
            gini = 0.0
        score_adj = score - alpha_singleton * singleton_ratio - alpha_empty * empty_ratio - alpha_gini * gini
        # 제약 위반 시 강한 패널티
        if singleton_ratio > singleton_max_ratio:
            score_adj -= 1.0 * (singleton_ratio - singleton_max_ratio)
        used_ratio = used_k / float(k)
        if used_ratio < used_min_ratio:
            score_adj -= 0.5 * (used_min_ratio - used_ratio)
        k_to_score[k] = score
        k_to_score_adj[k] = score_adj
        k_to_score_ch[k] = ch
        k_to_score_db[k] = db
        print(f"[05][K-scan] k={k:>4d} silhouette={score:.4f} used={used_k}/{k} singleton={singleton} empty={empty} adj={score_adj:.4f}")

    # 최고 스코어 선택(동점 시 더 작은 K)
    def sort_key(items):
        k, v = items
        val = v if not np.isnan(v) else -1e9
        return (-val, k)
    best_k = sorted(k_to_score_adj.items(), key=sort_key)[0][0]
    return {
        "chosen_k": int(best_k),
        "scores": {int(k): float(v) for k, v in k_to_score.items()},
        "scores_adjusted": {int(k): float(v) for k, v in k_to_score_adj.items()},
        "scores_ch": {int(k): float(v) for k, v in k_to_score_ch.items()},
        "scores_db": {int(k): float(v) for k, v in k_to_score_db.items()},
        "sample_size": int(X_sil.shape[0]),
    }


def fit_kmeans(X: np.ndarray, n_clusters: int, use_minibatch: bool, random_state: int, max_iter: int) -> object:
    if use_minibatch:
        km = MiniBatchKMeans(
            n_clusters=n_clusters,
            random_state=random_state,
            batch_size=2048,
            max_iter=max_iter,
            n_init="auto",
            verbose=0,
        )
    else:
        km = KMeans(
            n_clusters=n_clusters,
            random_state=random_state,
            max_iter=max_iter,
            n_init="auto",
            verbose=0,
        )
    km.fit(X)
    return km


def build_onehot_matrices(
    axis_to_row_words: Dict[str, List[List[str]]],
    word_to_cluster: Dict[str, int],
    n_rows: int,
    n_clusters: int,
    mode: str = "binary",  # "binary" or "count"
) -> Tuple[Dict[str, np.ndarray], np.ndarray]:
    """축별/결합 원핫(또는 카운트) 행렬 생성.

    Returns:
      - axis_onehots: {axis: (n_rows, n_clusters)}
      - combined: (n_rows, len(ACTIVE_AXES)*n_clusters)
    """
    assert mode in {"binary", "count"}
    axis_onehots: Dict[str, np.ndarray] = {}
    mats: List[np.ndarray] = []

    for axis in ACTIVE_AXES:
        mat = np.zeros((n_rows, n_clusters), dtype=np.float32)
        rows_words = axis_to_row_words[axis]
        for i, words in enumerate(rows_words):
            if not words:
                continue
            for w in words:
                cid = word_to_cluster.get(w)
                if cid is None:
                    continue
                if mode == "binary":
                    mat[i, cid] = 1.0
                else:  # count
                    mat[i, cid] += 1.0
        axis_onehots[axis] = mat
        mats.append(mat)

    combined = np.concatenate(mats, axis=1) if mats else np.zeros((n_rows, 0), dtype=np.float32)
    return axis_onehots, combined


def main():
    # 인자 없이 고정 설정으로 동작
    input_csv = DEFAULT_INPUT
    model_name = DEFAULT_MODEL
    out_dir = DEFAULT_OUTDIR
    source_embedding_dir = DEFAULT_SOURCE_EMB_DIR
    batch_size = 256
    normalize = True
    n_clusters = 256
    use_minibatch = True
    # 후보 알고리즘 리스트(콤마 구분)
    algos_env = os.getenv("PHASEC_CODEBOOK_ALGOS", "minibatch_kmeans,kmeans_cosine,agglomerative,kmeans")
    codebook_algos = [a.strip().lower() for a in algos_env.split(',') if a.strip()]
    # 단일 알고리즘 강제 시(하위 호환): PHASEC_CODEBOOK_ALGO가 지정되면 그 하나만 사용
    codebook_algo_single = os.getenv("PHASEC_CODEBOOK_ALGO", "").strip().lower()
    if codebook_algo_single:
        codebook_algos = [codebook_algo_single]
    random_state = 42
    max_iter = 300
    onehot_mode = "binary"  # or "count"
    auto_select_k = True
    # PCA 사전처리 설정(기본 on): 누적 분산 0.90 이상 보존
    # PCA 사전처리 끄기: 환경변수 PHASEC_PCA=false 로 제어
    use_pca_preprocess = (os.getenv("PHASEC_PCA", "true").lower() == "true")
    pca_variance_threshold = float(os.getenv("PHASEC_PCA_VAR", "0.95"))
    min_token_freq = int(os.getenv("PHASEC_MIN_TOKEN_FREQ", "2"))

    input_csv = Path(input_csv)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    t_start = time.time()
    # 재현성 시드
    seed = int(os.getenv("PHASEC_SEED", "42"))
    try:
        import random
        random.seed(seed)
    except Exception:
        pass
    try:
        np.random.seed(seed)
    except Exception:
        pass
    try:
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except Exception:
        pass
    # 데이터 로드
    df = pd.read_csv(input_csv, dtype=str, keep_default_na=False)
    # 입력 CSV 해시(재현)
    try:
        h = hashlib.sha256()
        with open(input_csv, 'rb') as _f:
            for chunk in iter(lambda: _f.read(8192), b""):
                h.update(chunk)
        input_hash = h.hexdigest()
    except Exception:
        input_hash = None
    missing = [c for c in ACTIVE_AXES if c not in df.columns]
    if missing:
        raise SystemExit(f"Missing required axis columns in input: {missing}")

    # 04 산출물(토큰 임베딩) 필수 로드
    src_dir = Path(source_embedding_dir)
    tokens_vocab_path = src_dir / "tokens_vocab.csv"
    # 토큰 임베딩 소스 자동 선택: combined_concat -> combined_avg -> secondary(any) -> primary
    order_env = os.getenv("PHASEC_TOKEN_EMB_ORDER", "combined_concat,combined_avg,secondary,primary")
    order = [o.strip().lower() for o in order_env.split(",") if o.strip()]
    cand_paths: List[Tuple[str, Path]] = []
    # 사전 후보 구성
    cand_map = {
        "combined_concat": src_dir / "tokens_embeddings__combined_concat.npy",
        "combined_avg": src_dir / "tokens_embeddings__combined_avg.npy",
        "primary": src_dir / "tokens_embeddings.npy",
    }
    # secondary는 와일드카드로 스캔 (combined_* 제외)
    secondary_paths = [p for p in sorted(src_dir.glob("tokens_embeddings__*.npy")) if "__combined_" not in p.name]
    # 우선순위대로 후보 나열
    for key in order:
        if key in ("combined_concat", "combined_avg", "primary"):
            cand_paths.append((key, cand_map[key]))
        elif key == "secondary":
            for p in secondary_paths:
                cand_paths.append((f"secondary:{p.stem}", p))
    # 존재하는 첫 경로 선택
    chosen_key = None
    tokens_embs_path = None
    for k, p in cand_paths:
        if p.exists():
            chosen_key, tokens_embs_path = k, p
            break
    if tokens_embs_path is None:
        # 최후 수단: primary 경로로 설정(없으면 이후에서 에러)
        chosen_key, tokens_embs_path = "primary", cand_map["primary"]
    axis_row_tokens_path = src_dir / "axis_row_tokens.jsonl"

    use_precomputed_tokens = tokens_vocab_path.exists() and tokens_embs_path.exists()
    vocab_list: List[str] = []
    token_embs: np.ndarray | None = None

    if not use_precomputed_tokens:
        raise SystemExit("04 단계 산출물(tokens_vocab.csv, tokens_embeddings.npy)이 필요합니다. 04를 먼저 실행하세요.")
    print("[05] Using precomputed tokens from 04 stage ...")
    print(f"[05] token embeddings source: {chosen_key} -> {tokens_embs_path}")
    df_vocab = pd.read_csv(tokens_vocab_path)
    if "word" not in df_vocab.columns:
        raise SystemExit("tokens_vocab.csv에 'word' 컬럼이 필요합니다.")
    vocab_list_all = df_vocab["word"].astype(str).tolist()
    vocab_freq_all = df_vocab["freq"].astype(int).tolist() if "freq" in df_vocab.columns else [1]*len(vocab_list_all)
    token_embs_all = np.load(tokens_embs_path)
    # 정합성 점검 및 보정
    n_from_vocab = len(vocab_list_all)
    n_from_npy = int(token_embs_all.shape[0])
    dim = int(token_embs_all.shape[1]) if token_embs_all.ndim == 2 else 0
    print(f"[05] tokens_vocab.csv entries: {n_from_vocab}")
    print(f"[05] tokens_embeddings.npy rows: {n_from_npy}, dim={dim}")
    if n_from_vocab != n_from_npy:
        print(f"[05][WARN] tokens_vocab({n_from_vocab}) != tokens_embeddings.npy({n_from_npy}); aligning to min length")
        n_min = min(n_from_vocab, n_from_npy)
        vocab_list_all = vocab_list_all[:n_min]
        vocab_freq_all = vocab_freq_all[:n_min]
        token_embs_all = token_embs_all[:n_min]
    # 희귀 토큰 필터링(min_freq)
    # stopword/짧은 토큰/숫자 제거 + 최소 빈도
    def _keep_idx(i: int) -> bool:
        w = vocab_list_all[i]
        f = vocab_freq_all[i]
        if f < min_token_freq:
            return False
        if len(w) < 2:
            return False
        if w.isnumeric():
            return False
        if (os.getenv("PHASEC_STOPWORD_FILTER", "true").lower() == "true") and (w.lower() in {
            'the','and','of','in','on','for','to','a','an','is','are','be','with','by','from','as','at','or','not','no',
            'this','that','these','those','it','its','into','their','his','her','our','your','my','we','you','they','he','she',
            'was','were','been','being','than','then','there','here','over','under','up','down','out','through','across'
        }):
            return False
        return True
    if min_token_freq > 1 or (os.getenv("PHASEC_STOPWORD_FILTER", "true").lower() == "true"):
        idx_keep = [i for i in range(len(vocab_list_all)) if _keep_idx(i)]
        if idx_keep and len(idx_keep) < len(vocab_list_all):
            vocab_list = [vocab_list_all[i] for i in idx_keep]
            vocab_freq = [vocab_freq_all[i] for i in idx_keep]
            token_embs = token_embs_all[idx_keep]
            print(f"[05] Filtered tokens: kept {len(vocab_list)}/{len(vocab_list_all)} (min_freq>={min_token_freq}, stopwords=True)")
        else:
            vocab_list = vocab_list_all
            vocab_freq = vocab_freq_all
            token_embs = token_embs_all
    else:
        vocab_list = vocab_list_all
        vocab_freq = vocab_freq_all
        token_embs = token_embs_all
    print(f"[05] Loaded token embeddings: {int(token_embs.shape[0])} with dim={dim}")
    vocab_count_before_merge = int(len(vocab_list))
    # 선택적: 중복/동의어 근접 토큰 병합(근사 최근접): prod 환경에서는 기본 off
    merge_similar = (os.getenv("PHASEC_CODEBOOK_MERGE_SIMILAR", "false").lower() == "true")
    if merge_similar and token_embs.shape[0] > 0:
        try:
            # 간단한 방식: 차원 축소 후 kNN 그래프에서 코사인 유사도 > thresh 이면 대표단어로 병합
            from sklearn.decomposition import TruncatedSVD
            from sklearn.neighbors import NearestNeighbors
            svd_m = int(os.getenv("PHASEC_CODEBOOK_MERGE_SVD", "64"))
            sim_th = float(os.getenv("PHASEC_CODEBOOK_MERGE_THRESH", "0.92"))
            max_deg = int(os.getenv("PHASEC_CODEBOOK_MERGE_MAX_DEG", "5"))
            Xr = token_embs
            if dim > svd_m:
                svd = TruncatedSVD(n_components=svd_m, random_state=42)
                Xr = svd.fit_transform(token_embs).astype(np.float32)
            # 정규화
            nrm = np.linalg.norm(Xr, axis=1, keepdims=True) + 1e-12
            Xn = (Xr / nrm).astype(np.float32)
            nn = NearestNeighbors(n_neighbors=min(max_deg+1, Xn.shape[0]), metric='cosine').fit(Xn)
            dist, idx = nn.kneighbors(Xn)
            # 간단 병합: 각 노드에서 유사도>=thresh 이면서 자기보다 앞 인덱스를 대표로 선택
            parent = list(range(Xn.shape[0]))
            def find(a):
                while parent[a] != a:
                    parent[a] = parent[parent[a]]
                    a = parent[a]
                return a
            def union(a,b):
                ra, rb = find(a), find(b)
                if ra != rb:
                    if ra < rb:
                        parent[rb] = ra
                    else:
                        parent[ra] = rb
            for i in range(Xn.shape[0]):
                for j_pos in range(1, idx.shape[1]):
                    j = int(idx[i, j_pos])
                    sim = 1.0 - float(dist[i, j_pos])
                    if sim >= sim_th:
                        union(i, j)
            # 대표 인덱스로 축소
            rep = [find(i) for i in range(Xn.shape[0])]
            keep_mask = np.array([i == rep[i] for i in range(Xn.shape[0])])
            if keep_mask.sum() < Xn.shape[0]:
                vocab_list = [w for w, m in zip(vocab_list, keep_mask.tolist()) if m]
                token_embs = token_embs[keep_mask]
                print(f"[05] Merged similar tokens: kept {token_embs.shape[0]}/{Xn.shape[0]}")
        except Exception as e:
            print(f"[05][WARN] Merge-similar skipped: {e}")
    vocab_count_after_merge = int(token_embs.shape[0])

    # 축별 단어 구성 및 vocabulary
    print("[05] Collecting tokens from axes ...")
    axis_to_row_words, vocab_counter, vocab_from_df = build_axis_words(df)
    n_rows = len(df)

    n_vocab = int(token_embs.shape[0])
    if n_vocab == 0:
        raise SystemExit("토큰이 비어 있습니다. 04 단계를 확인하세요.")

    # PCA 사전처리(선택)
    X_for_clustering = token_embs
    pca_info = None
    if use_pca_preprocess:
        print(f"[05] PCA preprocess: retaining >= {int(pca_variance_threshold*100)}% variance ...")
        # n_components에 비율을 직접 넣어 자동 선택 (svd_solver='full'), whiten으로 구면화
        pca = PCA(n_components=pca_variance_threshold, svd_solver='full', whiten=True, random_state=random_state)
        X_reduced = pca.fit_transform(token_embs)
        cumvar = np.cumsum(pca.explained_variance_ratio_)
        n_comp = int(X_reduced.shape[1])
        retained = float(cumvar[-1]) if cumvar.size > 0 else 0.0
        print(f"[05] PCA reduced dim: {token_embs.shape[1]} -> {n_comp} (cumvar={retained:.4f})")
        # 저장
        try:
            with open(out_dir / "pca.pkl", "wb") as f:
                pickle.dump(pca, f)
        except Exception as e:
            print(f"[05][WARN] Failed to save pca.pkl: {e}")
        try:
            np.save(out_dir / "pca_explained_variance_ratio.npy", pca.explained_variance_ratio_.astype(np.float32))
            np.save(out_dir / "tokens_embeddings_pca.npy", X_reduced.astype(np.float32))
        except Exception as e:
            print(f"[05][WARN] Failed to save PCA arrays: {e}")
        # 시각화(있으면)
        if HAS_MPL:
            try:
                import matplotlib.pyplot as plt
                plt.figure(figsize=(8,5))
                plt.plot(np.arange(1, len(cumvar)+1), cumvar, marker='o')
                plt.axhline(pca_variance_threshold, color='red', linestyle='--', linewidth=1, label=f"threshold={pca_variance_threshold}")
                plt.xlabel("num components")
                plt.ylabel("cumulative explained variance")
                plt.title("PCA cumulative variance")
                plt.legend()
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                plt.savefig(out_dir / "pca_cumulative_variance.png", dpi=150)
                plt.close()
                print("[05] Saved:", out_dir / "pca_cumulative_variance.png")
            except Exception as e:
                print(f"[05][WARN] Failed to plot PCA variance: {e}")
        X_for_clustering = X_reduced
        pca_info = {"enabled": True, "n_components": int(n_comp), "variance_retained": float(retained)}
    else:
        pca_info = {"enabled": False}

    # 자동 K 선택(옵션) + 목표 평균 클러스터 크기 기반 가드
    k_selection_info = None
    if auto_select_k:
        print("[05] Selecting K automatically (silhouette over candidates) ...")
        k_selection_info = select_k_automatically(
            X_for_clustering,
            use_minibatch=use_minibatch,
            random_state=random_state,
            max_iter=max_iter,
            candidate_ks=None,
            sample_for_silhouette=20000,
        )
        n_clusters = int(k_selection_info["chosen_k"])
        # 평균 클러스터 크기 제한(환경변수)
        try:
            min_avg = int(os.getenv("PHASEC_CODEBOOK_MIN_AVG_CLUSTER_SIZE", "0"))
        except Exception:
            min_avg = 0
        if min_avg and min_avg > 0:
            avg_size = token_embs.shape[0] / float(max(1, n_clusters))
            if avg_size < min_avg:
                # 평균 크기 보전 위해 K 축소
                n_clusters = max(4, int(token_embs.shape[0] // min_avg))
                print(f"[05][INFO] Adjusted K to {n_clusters} to respect min average cluster size {min_avg}")
        print(f"[05] Chosen K: {n_clusters} (candidates scored)")

    # KMeans로 코드북 학습
    # 코드북 학습: 후보 알고리즘 전부 시도 후 최적 선택(실루엣 기준)
    best = {"score": float('-inf'), "algo": None, "labels": None, "centers": None, "model": None, "meta": {}}
    from math import isfinite
    for algo in codebook_algos:
        algo = algo.lower()
        if algo not in ("kmeans", "minibatch_kmeans", "kmeans_cosine", "agglomerative"):
            print(f"[05][INFO] Skip unknown algo: {algo}")
            continue
        # 알고리즘별 입력 준비(구면 KMeans는 L2 정규화)
        X_alg = X_for_clustering
        if algo == "kmeans_cosine" and X_alg.size:
            nrm = np.linalg.norm(X_alg, axis=1, keepdims=True) + 1e-12
            X_alg = (X_alg / nrm).astype(np.float32)

        try:
            if algo in ("kmeans", "minibatch_kmeans", "kmeans_cosine"):
                print(f"[05] Fitting KMeans (algo={algo}, n_clusters={n_clusters}) ...")
                km = fit_kmeans(X_alg, n_clusters=n_clusters, use_minibatch=(use_minibatch or algo=="minibatch_kmeans"),
                                random_state=random_state, max_iter=max_iter)
                lbl = km.predict(X_alg)
                ctr = km.cluster_centers_.astype(np.float32)
                mdl = km
            else:  # agglomerative
                print(f"[05] Fitting AgglomerativeClustering (n_clusters={n_clusters}) ...")
                try:
                    from sklearn.cluster import AgglomerativeClustering
                except Exception as e:
                    print(f"[05][WARN] Agglomerative unavailable: {e}; skipping")
                    continue
                linkage = os.getenv("PHASEC_AGGLO_LINKAGE", "ward").strip().lower()
                if linkage == "ward":
                    model = AgglomerativeClustering(n_clusters=n_clusters, linkage='ward')
                else:
                    try:
                        model = AgglomerativeClustering(n_clusters=n_clusters, linkage=linkage, metric='euclidean')
                    except TypeError:
                        model = AgglomerativeClustering(n_clusters=n_clusters, linkage=linkage, affinity='euclidean')
                lbl = model.fit_predict(X_alg)
                ctr = np.zeros((n_clusters, X_alg.shape[1]), dtype=np.float32)
                for cid in range(n_clusters):
                    idx = np.where(lbl == cid)[0]
                    if idx.size == 0:
                        ridx = np.random.randint(0, X_alg.shape[0])
                        ctr[cid] = X_alg[ridx]
                    else:
                        ctr[cid] = X_alg[idx].mean(axis=0).astype(np.float32)
                mdl = {"algo": "agglomerative", "linkage": linkage}

            # 점수(실루엣) 계산 - 유클리드, 유효하지 않으면 -inf 취급
            try:
                from sklearn.metrics import silhouette_score
                s = float(silhouette_score(X_alg, lbl, metric='euclidean'))
            except Exception:
                s = float('-inf')
            print(f"[05] algo={algo} silhouette={s:.4f}")
            if isfinite(s) and s > best["score"]:
                best = {"score": s, "algo": algo, "labels": lbl, "centers": ctr, "model": mdl, "meta": {}}
        except Exception as e:
            print(f"[05][WARN] algo={algo} failed: {e}")

    if best["algo"] is None:
        raise SystemExit("No valid codebook algorithm succeeded.")
    print(f"[05] Chosen algo: {best['algo']} (silhouette={best['score']:.4f})")
    labels = best["labels"]
    centers = best["centers"]
    saved_model_obj = best["model"]

    # 단어 → 클러스터 매핑
    token_clusters: np.ndarray = np.asarray(labels, dtype=np.int32)
    word_to_cluster: Dict[str, int] = {w: int(c) for w, c in zip(vocab_list, token_clusters.tolist())}

    # 축별/결합 원핫(또는 카운트) 행렬 생성
    print(f"[05] Building {onehot_mode} matrices ...")
    axis_onehots, combined = build_onehot_matrices(
        axis_to_row_words=axis_to_row_words,
        word_to_cluster=word_to_cluster,
        n_rows=n_rows,
        n_clusters=n_clusters,
        mode=onehot_mode,
    )

    # 저장: 코드북, 매핑, 메타, 행렬들
    print("[05] Saving outputs ...")
    # 1) 코드북(KMeans 객체 및 센트로이드)
    with open(out_dir / "codebook_kmeans.pkl", "wb") as f:
        pickle.dump(saved_model_obj, f)
    np.save(out_dir / "codebook_centers.npy", centers.astype(np.float32))

    # 2) 단어-클러스터 매핑 CSV
    df_map = pd.DataFrame({
        "word": vocab_list,
        "cluster": token_clusters.astype(int),
        "freq": [int(vocab_counter.get(w, 0)) for w in vocab_list],
    })
    df_map.to_csv(out_dir / "word_to_cluster.csv", index=False)
    print(f"[05] word_to_cluster rows: {len(df_map)}, unique clusters used: {df_map['cluster'].nunique()}")

    # 3) 축별 행렬(.npz) + 결합 행렬(.npz)
    np.savez_compressed(
        out_dir / "axis_onehot_matrices.npz",
        **{slugify(axis): mat for axis, mat in axis_onehots.items()},
    )
    np.savez_compressed(out_dir / "combined_onehot.npz", combined=combined)

    # 4) 식별자 저장
    id_df = df[[c for c in ID_COLS if c in df.columns]].copy()
    id_df.to_csv(out_dir / "ids.csv", index=False)

    # 5) 메타데이터 저장
    meta = {
        "model": model_name,
        "normalize": normalize,
        "codebook": {
            "method": str(best["algo"]),
            "n_clusters": int(n_clusters),
            "random_state": int(random_state),
            "max_iter": int(max_iter),
            "selection": {
                "algos_tried": codebook_algos,
                "silhouette": float(best["score"]),
            }
        },
        "onehot_mode": onehot_mode,
        "axes": ACTIVE_AXES,
        "rows": int(n_rows),
        "vocab_size": int(n_vocab),
        "input_csv": str(input_csv),
    }
    if k_selection_info is not None:
        meta["codebook"]["auto_select_k"] = True
        meta["codebook"]["k_selection_scores"] = k_selection_info["scores"]
        meta["codebook"]["k_selection_sample_size"] = k_selection_info["sample_size"]
        if "scores_adjusted" in k_selection_info:
            meta["codebook"]["k_selection_scores_adjusted"] = k_selection_info["scores_adjusted"]
        # 추가: CH/DB 점수 맵
        if "scores_ch" in k_selection_info:
            meta["codebook"]["selection"] = meta["codebook"].get("selection", {})
            meta["codebook"]["selection"]["scores_ch"] = k_selection_info["scores_ch"]
        if "scores_db" in k_selection_info:
            meta["codebook"]["selection"] = meta["codebook"].get("selection", {})
            meta["codebook"]["selection"]["scores_db"] = k_selection_info["scores_db"]
    if pca_info is not None:
        meta["pca"] = pca_info
    with open(out_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # K 선택 결과 별도 저장
    if k_selection_info is not None:
        with open(out_dir / "k_selection.json", "w", encoding="utf-8") as f:
            json.dump(k_selection_info, f, ensure_ascii=False, indent=2)

    # K 선택 점수 시각화 저장
    if k_selection_info is not None and HAS_MPL:
        try:
            ks = sorted(map(int, k_selection_info.get("scores", {}).keys()))
            y_raw = [k_selection_info["scores"][k] for k in ks]
            y_adj = [k_selection_info.get("scores_adjusted", {}).get(k, np.nan) for k in ks]
            chosen_k = int(k_selection_info["chosen_k"])
            plt.figure(figsize=(8, 5))
            plt.plot(ks, y_raw, marker="o", label="silhouette")
            if any([not np.isnan(v) for v in y_adj]):
                plt.plot(ks, y_adj, marker="s", label="adjusted")
            plt.axvline(chosen_k, color="red", linestyle="--", linewidth=1, label=f"chosen K={chosen_k}")
            plt.xlabel("K")
            plt.ylabel("score")
            plt.title("K selection scores")
            plt.legend()
            plt.grid(True, alpha=0.3)
            fig_path = out_dir / "k_selection_scores.png"
            plt.tight_layout()
            plt.savefig(fig_path, dpi=150)
            plt.close()
            print("[05] Saved:", fig_path)
        except Exception as e:
            print(f"[05][WARN] Failed to save K selection plot: {e}")

    print("[05] Saved:")
    print(" -", out_dir / "codebook_kmeans.pkl")
    print(" -", out_dir / "codebook_centers.npy")
    print(" -", out_dir / "word_to_cluster.csv")
    print(" -", out_dir / "axis_onehot_matrices.npz")
    print(" -", out_dir / "combined_onehot.npz")
    print(" -", out_dir / "meta.json")
    print(" -", out_dir / "ids.csv")

    # ========= 논문 보고용 메트릭 산출/저장 =========
    try:
        # 클러스터 크기 통계
        counts = np.bincount(token_clusters.astype(int), minlength=n_clusters)
        used_k = int((counts > 0).sum())
        singleton = int((counts == 1).sum())
        empty = int(n_clusters - used_k)
        singleton_ratio = float(singleton) / float(max(1, n_clusters))
        empty_ratio = float(empty) / float(max(1, n_clusters))
        if counts.sum() > 0:
            p = counts / counts.sum()
            gini = float(1.0 - np.sum(p * p))
        else:
            gini = 0.0
        size_mean = float(counts[counts > 0].mean()) if used_k > 0 else 0.0
        size_median = float(np.median(counts[counts > 0])) if used_k > 0 else 0.0
        size_p90 = float(np.percentile(counts[counts > 0], 90)) if used_k > 0 else 0.0

        meta_metrics = {
            "input_csv": str(input_csv),
        "input_csv_sha256": input_hash,
            "vocab_all": int(len(vocab_list_all)),
            "vocab_filtered": int(vocab_count_before_merge),
            "vocab_after_merge": int(vocab_count_after_merge),
            "embedding_dim": int(dim),
            "pca": pca_info or {"enabled": False},
            "kmeans": {
                "algo": str(best.get("algo")),
                "n_clusters": int(n_clusters),
                "silhouette": float(best.get("score", float("nan"))),
                "cluster_used": int(used_k),
                "singleton": int(singleton),
                "empty": int(empty),
                "singleton_ratio": float(singleton_ratio),
                "empty_ratio": float(empty_ratio),
                "gini": float(gini),
                "size_mean": float(size_mean),
                "size_median": float(size_median),
                "size_p90": float(size_p90),
            },
            # 중립적 키(하위호환 유지)
            "codebook": {
                "algo": str(best.get("algo")),
                "n_clusters": int(n_clusters),
                "silhouette": float(best.get("score", float("nan"))),
                "cluster_used": int(used_k),
                "singleton": int(singleton),
                "empty": int(empty),
                "singleton_ratio": float(singleton_ratio),
                "empty_ratio": float(empty_ratio),
                "gini": float(gini),
                "size_mean": float(size_mean),
                "size_median": float(size_median),
                "size_p90": float(size_p90),
            },
            "k_selection": k_selection_info or {},
            "runtime_sec": float(time.time() - t_start),
            "versions": {
                "python": sys.version,
                "platform": platform.platform(),
                "numpy": np.__version__,
                "pandas": pd.__version__,
                "torch": torch.__version__,
            },
            "env": {
                "PHASEC_MIN_TOKEN_FREQ": os.getenv("PHASEC_MIN_TOKEN_FREQ", ""),
                "PHASEC_STOPWORD_FILTER": os.getenv("PHASEC_STOPWORD_FILTER", ""),
                "PHASEC_PCA": os.getenv("PHASEC_PCA", ""),
                "PHASEC_PCA_VAR": os.getenv("PHASEC_PCA_VAR", ""),
                "PHASEC_CODEBOOK_MERGE_SIMILAR": os.getenv("PHASEC_CODEBOOK_MERGE_SIMILAR", ""),
                "PHASEC_CODEBOOK_TARGET_AVG_CLUSTER_SIZE": os.getenv("PHASEC_CODEBOOK_TARGET_AVG_CLUSTER_SIZE", ""),
                "PHASEC_CODEBOOK_MIN_AVG_CLUSTER_SIZE": os.getenv("PHASEC_CODEBOOK_MIN_AVG_CLUSTER_SIZE", ""),
                "PHASEC_CODEBOOK_MAX_K": os.getenv("PHASEC_CODEBOOK_MAX_K", ""),
            },
        }
        with open(out_dir / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(meta_metrics, f, ensure_ascii=False, indent=2)
        # CSV 요약(테이블용)
        pd.DataFrame([{
            "vocab_all": meta_metrics["vocab_all"],
            "vocab_filtered": meta_metrics["vocab_filtered"],
            "vocab_after_merge": meta_metrics["vocab_after_merge"],
            "dim": meta_metrics["embedding_dim"],
            "K": meta_metrics["kmeans"]["n_clusters"],
            "silhouette": meta_metrics["kmeans"]["silhouette"],
            "used_k": meta_metrics["kmeans"]["cluster_used"],
            "singleton_ratio": meta_metrics["kmeans"]["singleton_ratio"],
            "gini": meta_metrics["kmeans"]["gini"],
            "size_mean": meta_metrics["kmeans"]["size_mean"],
            "size_median": meta_metrics["kmeans"]["size_median"],
            "size_p90": meta_metrics["kmeans"]["size_p90"],
            "runtime_sec": meta_metrics["runtime_sec"],
        }]).to_csv(out_dir / "metrics_summary.csv", index=False)
        print("[05] Saved:", out_dir / "metrics.json")
        print("[05] Saved:", out_dir / "metrics_summary.csv")
    except Exception as e:
        print(f"[05][WARN] Failed to save paper metrics: {e}")


if __name__ == "__main__":
    main()
