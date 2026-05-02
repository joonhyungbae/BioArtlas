#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
04_build_embeddings.py
- 공개된 data/dataset/BioArtlas.csv의 13개 영어 축 텍스트를 입력으로 하여
  Hugging Face BGE 임베딩 모델(BAAI/bge-large-en-v1.5)로 "단어(토큰) 단위 임베딩"을 추출해 평균하여 축 임베딩을 생성
- 결과: 축별 N x D 행렬(.npy) + 축 묶음(.npz) + 메타데이터(.json)

참고 모델: BAAI/bge-large-en-v1.5 (sentence-transformers 사용)
모델 카드: https://huggingface.co/BAAI/bge-large-en-v1.5
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict
import re
from collections import Counter

import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer
import os
import time
import sys
import platform
import hashlib

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
DATA_DIR = REPO_ROOT / "data"
DATASET_DIR = DATA_DIR / "dataset"
ARTIFACTS_DIR = BASE_DIR / "artifacts"
DEFAULT_INPUT = DATASET_DIR / "BioArtlas.csv"
DEFAULT_MODEL = "BAAI/bge-large-en-v1.5"
DEFAULT_OUTDIR = ARTIFACTS_DIR / "04_embedding" / "bge_large_en_v1_5"
# 추가 임베딩 모델(옵션)
SECOND_MODEL: str | None = "Alibaba-NLP/gte-large-en-v1.5"
COMBINE_MODE: str = "concat"  # "concat" | "none" | "avg" (avg는 차원 동일 시만 가능)

# 13 English axis columns (exact headers in the canonical dataset)
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

# Use all axes. Downstream 안정성을 위해 빈 칸은 0벡터로 대체합니다.
ACTIVE_AXES: List[str] = AXIS_EN_COLUMNS

ID_COLS: List[str] = ["Artist", "Artwork", "Year", "Gen"]


def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def build_texts_for_axis(series: pd.Series) -> List[str]:
    # 원문 문자열 그대로 반환 (단어 분리는 아래에서 수행)
    return [str(x) if isinstance(x, str) and x.strip() else "" for x in series.tolist()]


def _split_to_words(text: str) -> List[str]:
    """문장에서 단어(알파뉴메릭/하이픈/아포스트로피 포함)를 추출해 리스트로 반환."""
    if not isinstance(text, str) or not text.strip():
        return []
    # 예: microorganism (bacteria) -> [microorganism, bacteria]
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-']*", text)
    # 토큰 소문자화 옵션
    lower = (os.getenv("PHASEC_TOKEN_LOWER", "true").lower() == "true")
    if lower:
        words = [w.lower() for w in words]
    return [w for w in words if w]


def embed_texts(model: SentenceTransformer, texts: List[str], batch_size: int, normalize: bool) -> np.ndarray:
    # sentence-transformers encode supports normalization
    emb = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=normalize,
    )
    return emb


def main():
    # 인자 없이 고정 설정으로 동작
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
    input_csv = DEFAULT_INPUT
    model_name = DEFAULT_MODEL
    out_dir = DEFAULT_OUTDIR
    batch_size = 64
    normalize = True
    # 토큰/임베딩 아티팩트 저장은 기본 활성화
    dump_tokens = True
    save_row_tokens = True
    max_vocab = 0  # 0이면 제한 없음

    input_csv = Path(input_csv)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load data
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

    # Validate columns (only for active axes)
    missing = [c for c in ACTIVE_AXES if c not in df.columns]
    if missing:
        raise SystemExit(f"Missing required axis columns in input: {missing}")

    # Load model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[04] Loading model {model_name} on {device} ...")
    model = SentenceTransformer(model_name, device=device)
    dim = model.get_sentence_embedding_dimension()
    print(f"[04] Embedding dimension: {dim}")

    # 보조 모델 로딩(선택)
    model2 = None
    dim2: int | None = None
    model2_name: str | None = SECOND_MODEL
    if model2_name:
        print(f"[04] Loading secondary model {model2_name} on {device} ...")
        # 일부 HF 모델은 remote code 신뢰 설정이 필요
        model2 = SentenceTransformer(model2_name, device=device, trust_remote_code=True)
        dim2 = model2.get_sentence_embedding_dimension()
        print(f"[04] Secondary embedding dimension: {dim2}")

    n_rows = len(df)
    axis_to_embeddings: Dict[str, np.ndarray] = {}
    axis_to_embeddings_2: Dict[str, np.ndarray] = {}
    # 토큰 수집 구조
    vocab_counter: Counter = Counter()
    row_tokens_per_axis: Dict[str, List[List[str]]] = {axis: [] for axis in ACTIVE_AXES}

    # 1) 전 데이터에서 토큰만 먼저 수집 (중복 제거용 vocabulary 구축)
    print("[04] Collecting tokens across all axes ...")
    for axis in ACTIVE_AXES:
        texts = build_texts_for_axis(df[axis])
        for t in texts:
            words = _split_to_words(t)
            vocab_counter.update(words)
            row_tokens_per_axis[axis].append(words)

    # 유니크 토큰 목록 (빈도 내림차순)
    vocab_list = [w for w, _ in vocab_counter.most_common()]
    print(f"[04] Unique tokens: {len(vocab_list)} (total occurrences: {sum(vocab_counter.values())})")

    # 2) 유니크 토큰 임베딩 1회 계산 후 캐시 사용
    print("[04] Encoding unique tokens once ...")
    token_embs = embed_texts(model, vocab_list, batch_size=batch_size, normalize=normalize)
    token_embs = token_embs.astype(np.float32)
    word_to_emb: Dict[str, np.ndarray] = {w: token_embs[i] for i, w in enumerate(vocab_list)}

    # 보조 모델 토큰 임베딩(선택)
    token_embs_2: np.ndarray | None = None
    word_to_emb_2: Dict[str, np.ndarray] | None = None
    if model2 is not None:
        print("[04] Encoding unique tokens once (secondary model) ...")
        token_embs_2 = embed_texts(model2, vocab_list, batch_size=batch_size, normalize=normalize)
        token_embs_2 = token_embs_2.astype(np.float32)
        word_to_emb_2 = {w: token_embs_2[i] for i, w in enumerate(vocab_list)}

    # 3) 축별 임베딩: 각 행의 토큰 임베딩을 평균
    for axis in ACTIVE_AXES:
        print(f"[04] Aggregating axis (word_mean): {axis}")
        embs = np.zeros((n_rows, dim), dtype=np.float32)
        rows_words = row_tokens_per_axis[axis]
        for i, words in enumerate(rows_words):
            if not words:
                continue
            vecs = [word_to_emb[w] for w in words if w in word_to_emb]
            if not vecs:
                continue
            embs[i] = np.mean(vecs, axis=0).astype(np.float32)
        axis_to_embeddings[axis] = embs
        np.save(out_dir / f"{slugify(axis)}.npy", embs)

        # 보조 모델 축 임베딩(선택)
        if model2 is not None and word_to_emb_2 is not None and dim2 is not None:
            embs2 = np.zeros((n_rows, dim2), dtype=np.float32)
            for i, words in enumerate(rows_words):
                if not words:
                    continue
                vecs2 = [word_to_emb_2[w] for w in words if w in word_to_emb_2]
                if not vecs2:
                    continue
                embs2[i] = np.mean(vecs2, axis=0).astype(np.float32)
            axis_to_embeddings_2[axis] = embs2
            np.save(out_dir / f"{slugify(axis)}__{slugify(model2_name.split('/')[-1])}.npy", embs2)

    # Save combined NPZ and metadata
    np.savez_compressed(
        out_dir / "embeddings_axes.npz",
        **{slugify(k): v for k, v in axis_to_embeddings.items()},
    )

    # 보조 모델 결과 NPZ 저장
    if axis_to_embeddings_2:
        np.savez_compressed(
            out_dir / f"embeddings_axes__{slugify(model2_name.split('/')[-1])}.npz",
            **{slugify(k): v for k, v in axis_to_embeddings_2.items()},
        )

    # 결합 저장
    if axis_to_embeddings_2 and COMBINE_MODE in {"concat", "avg"}:
        combined: Dict[str, np.ndarray] = {}
        for axis in ACTIVE_AXES:
            if axis not in axis_to_embeddings or axis not in axis_to_embeddings_2:
                continue
            a = axis_to_embeddings[axis]
            b = axis_to_embeddings_2[axis]
            if COMBINE_MODE == "concat":
                c = np.concatenate([a, b], axis=1)
            else:  # avg
                if a.shape[1] != b.shape[1]:
                    print(f"[04][WARN] Cannot average embeddings for axis '{axis}' due to dim mismatch: {a.shape[1]} vs {b.shape[1]}; falling back to concat.")
                    c = np.concatenate([a, b], axis=1)
                else:
                    c = ((a + b) / 2.0).astype(np.float32)
            combined[axis] = c
            np.save(out_dir / f"{slugify(axis)}__combined_{COMBINE_MODE}.npy", c)
        if combined:
            np.savez_compressed(
                out_dir / f"embeddings_axes__combined_{COMBINE_MODE}.npz",
                **{slugify(k): v for k, v in combined.items()},
            )

    # 메타 + 논문용 지표 포함
    meta = {
        "model": model_name,
        "normalize": normalize,
        "pooling": "word_mean",
        "rows": int(n_rows),
        "dim": int(dim),
        # Save only active axes in metadata so downstream uses the same set
        "axes": ACTIVE_AXES,
        "input_csv": str(input_csv),
        "input_csv_sha256": input_hash,
        "token_lower": (os.getenv("PHASEC_TOKEN_LOWER", "true").lower() == "true"),
        "vocab": {
            "unique": int(len(vocab_list)),
            "total_occurrences": int(sum(vocab_counter.values())),
        },
        "runtime_sec": float(time.time() - t_start),
        "versions": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "torch": torch.__version__,
            "sentence_transformers": getattr(SentenceTransformer, "__module__", "sentence_transformers"),
        },
    }
    with open(out_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # 보조/결합 메타 저장
    if axis_to_embeddings_2:
        meta2 = {
            "primary_model": model_name,
            "secondary_model": model2_name,
            "normalize": normalize,
            "pooling": "word_mean",
            "rows": int(n_rows),
            "dim_primary": int(dim),
            "dim_secondary": int(dim2) if dim2 is not None else None,
            "combine_mode": COMBINE_MODE,
            "axes": ACTIVE_AXES,
            "input_csv": str(input_csv),
        }
        with open(out_dir / f"meta__{slugify(model2_name.split('/')[-1])}.json", "w", encoding="utf-8") as f:
            json.dump(meta2, f, ensure_ascii=False, indent=2)

    # Also save identifiers for traceability
    id_df = df[[c for c in ID_COLS if c in df.columns]].copy()
    id_df.to_csv(out_dir / "ids.csv", index=False)

    print("[04] Saved:")
    print(" -", out_dir / "embeddings_axes.npz")
    print(" -", out_dir / "meta.json")
    print(" -", out_dir / "ids.csv")
    print(" - Per-axis .npy files in:", out_dir)

    # 유니크 토큰 임베딩 및 매핑 저장 (항상 저장)
    if len(vocab_list) > 0:
        print("[04] Saving unique tokens and embeddings ...")
        vocab_to_save = vocab_list
        token_embs_to_save = token_embs
        if max_vocab and max_vocab > 0:
            vocab_to_save = vocab_list[: max_vocab]
            token_embs_to_save = token_embs[: max_vocab]
        np.save(out_dir / "tokens_embeddings.npy", token_embs_to_save)
        # vocab csv 저장
        df_vocab = pd.DataFrame({
            "word": vocab_to_save,
            "freq": [int(vocab_counter[w]) for w in vocab_to_save],
        })
        df_vocab.to_csv(out_dir / "tokens_vocab.csv", index=False)
        # word->index 매핑 저장
        vocab_to_index = {w: i for i, w in enumerate(vocab_to_save)}
        with open(out_dir / "vocab_to_index.json", "w", encoding="utf-8") as f:
            json.dump(vocab_to_index, f, ensure_ascii=False)
        print("[04] Saved tokens:")
        print(" -", out_dir / "tokens_embeddings.npy")
        print(" -", out_dir / "tokens_vocab.csv")
        print(" -", out_dir / "vocab_to_index.json")

        # 보조 모델 토큰 임베딩 저장 및 결합 토큰 임베딩 저장
        if token_embs_2 is not None:
            token_embs_2_to_save = token_embs_2
            if max_vocab and max_vocab > 0:
                token_embs_2_to_save = token_embs_2[: max_vocab]
            np.save(out_dir / f"tokens_embeddings__{slugify(model2_name.split('/')[-1])}.npy", token_embs_2_to_save)
            print(" -", out_dir / f"tokens_embeddings__{slugify(model2_name.split('/')[-1])}.npy")

            # 결합 토큰 임베딩(BGE+보조)
            if COMBINE_MODE in {"concat", "avg"}:
                if COMBINE_MODE == "concat":
                    token_embs_combined = np.concatenate([token_embs_to_save, token_embs_2_to_save], axis=1)
                else:  # avg
                    if token_embs_to_save.shape[1] != token_embs_2_to_save.shape[1]:
                        print(f"[04][WARN] Cannot average token embeddings due to dim mismatch: {token_embs_to_save.shape[1]} vs {token_embs_2_to_save.shape[1]}; falling back to concat.")
                        token_embs_combined = np.concatenate([token_embs_to_save, token_embs_2_to_save], axis=1)
                    else:
                        token_embs_combined = ((token_embs_to_save + token_embs_2_to_save) / 2.0).astype(np.float32)
                np.save(out_dir / f"tokens_embeddings__combined_{COMBINE_MODE}.npy", token_embs_combined)
                print(" -", out_dir / f"tokens_embeddings__combined_{COMBINE_MODE}.npy")

    # 선택적: 행×축별 토큰 JSONL 저장
    if save_row_tokens:
        print("[04] Writing axis_row_tokens.jsonl ...")
        jsonl_path = out_dir / "axis_row_tokens.jsonl"
        with open(jsonl_path, "w", encoding="utf-8") as f:
            # row 단위로 직렬화: { axis_name: [tokens...] }
            for i in range(n_rows):
                obj = {axis: row_tokens_per_axis[axis][i] if i < len(row_tokens_per_axis[axis]) else [] for axis in ACTIVE_AXES}
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        print("[04] Saved:")
        print(" -", jsonl_path)


if __name__ == "__main__":
    main()
