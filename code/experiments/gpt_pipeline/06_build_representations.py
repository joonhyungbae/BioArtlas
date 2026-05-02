#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
06_build_representations.py

역할:
- R-B: 축 임베딩 13×1024를 축별로 이어붙여(concat) L2 정규화한 특징 저장
  → results/runs/concat_features.npy
- R-C: 축별 코사인 커널(행 L2정규화 후 K=E Eᵀ) → trace normalize → 평균 커널 저장
  → results/runs/avg_kernel.npy
- (옵션) R-A: raw terms가 있으면 multi-hot 특징 생성/저장
  → results/runs/multihot_features.npy

설정은 루트의 config.yaml에서 읽습니다.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict
import importlib.util
import sys
import os

import numpy as np
import yaml


BASE_DIR = Path(__file__).resolve().parent


def import_utils_module() -> object:
    """숫자로 시작하는 파일명을 안전하게 임포트하기 위해 동적 임포트 사용."""
    util_path = BASE_DIR / "05_utils_srmva.py"
    if not util_path.exists():
        print(f"[06] 유틸 파일이 없습니다: {util_path}", file=sys.stderr)
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("utils_srmva", util_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore
    return module


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg or {}


def try_build_multihot(csv_path: Path, axis_columns: list[str]) -> np.ndarray | None:
    """콤마로 구분된 토큰이 담긴 컬럼들에서 multi-hot 특징을 생성.
    raw terms 파일이 없거나 문제 발생 시 None 반환.
    """
    if not csv_path.exists():
        return None
    try:
        import pandas as pd  # 지연 임포트
    except Exception:
        return None

    try:
        df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    except Exception:
        return None

    missing = [c for c in axis_columns if c not in df.columns]
    if missing:
        return None

    # 토큰 vocabulary 구축
    vocab: dict[str, int] = {}
    def add_token(tok: str):
        t = tok.strip().lower()
        if not t:
            return
        if t not in vocab:
            vocab[t] = len(vocab)

    for col in axis_columns:
        for text in df[col].tolist():
            if not isinstance(text, str) or not text.strip():
                continue
            tokens = [t for t in (x.strip() for x in text.split(',')) if t]
            for tok in tokens:
                add_token(tok)

    if not vocab:
        return None

    N = len(df)
    V = len(vocab)
    X = np.zeros((N, V), dtype=np.float32)
    for i, _ in enumerate(df.index):
        for col in axis_columns:
            text = df.at[i, col]
            if not isinstance(text, str) or not text.strip():
                continue
            tokens = [t for t in (x.strip() for x in text.split(',')) if t]
            for tok in tokens:
                j = vocab.get(tok.strip().lower())
                if j is not None:
                    X[i, j] = 1.0
    return X


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=str, default=str(BASE_DIR / "config.yaml"))
    args = ap.parse_args()

    cfg = load_config(Path(args.config))
    data_cfg = cfg.get("data", {})
    exp_cfg = cfg.get("exp", {})
    out_cfg = cfg.get("output", {})

    embeddings_npz = Path(data_cfg.get("embeddings_npz", "data/embeddings_axes.npz"))
    if not embeddings_npz.is_absolute():
        embeddings_npz = (BASE_DIR / embeddings_npz).resolve()

    output_root = Path(out_cfg.get("dir", "results"))
    if not output_root.is_absolute():
        output_root = (BASE_DIR / output_root).resolve()
    runs_dir = output_root / "runs"
    ensure_dir(runs_dir)

    use_trace_normalize = bool(exp_cfg.get("use_trace_normalize", True))

    utils = import_utils_module()

    print(f"[06] 로드: {embeddings_npz}")
    axes_embeddings: Dict[str, np.ndarray] = utils.load_embeddings(str(embeddings_npz))
    axis_names = sorted(axes_embeddings.keys())
    N = next(iter(axes_embeddings.values())).shape[0]
    print(f"[06] 축 개수: {len(axis_names)}, 샘플 N: {N}, 임베딩 차원: 1024")

    # R-B: concat features (13×1024 → L2)
    X_concat = utils.build_concat_features(axes_embeddings)
    concat_path = runs_dir / "concat_features.npy"
    np.save(concat_path, X_concat)
    row_norms = np.linalg.norm(X_concat, axis=1)
    print("[06][R-B] concat_features:")
    print(f"  shape={X_concat.shape}, row_norms(mean/min/max)="
          f"{row_norms.mean():.4f}/{row_norms.min():.4f}/{row_norms.max():.4f}")
    print(f"  → 저장: {concat_path}")

    # R-C: 축별 코사인 커널 → trace normalize → 평균
    axes_cos = {k: utils.l2_normalize_rows(v) for k, v in axes_embeddings.items()}
    K_axes = utils.build_axis_kernels(axes_cos, trace_normalize=use_trace_normalize)
    K_avg = utils.combine_kernels_average(K_axes)
    avgk_path = runs_dir / "avg_kernel.npy"
    np.save(avgk_path, K_avg)
    tr = float(np.trace(K_avg))
    print("[06][R-C] avg_kernel:")
    print(f"  shape={K_avg.shape}, min/max/mean={K_avg.min():.4f}/{K_avg.max():.4f}/{K_avg.mean():.4f}, trace={tr:.4f}")
    print(f"  → 저장: {avgk_path}")

    # (옵션) R-A: raw terms가 있으면 multi-hot 생성
    raw_terms_csv = data_cfg.get("raw_terms_csv")
    multihot_path = runs_dir / "multihot_features.npy"
    built_multihot = False
    if raw_terms_csv:
        csv_path = Path(raw_terms_csv)
        if not csv_path.is_absolute():
            csv_path = (BASE_DIR / csv_path).resolve()
        # meta.json의 'axes' 필드에서 축 컬럼명을 가져오는 것을 우선 시도
        axis_columns: list[str] = []
        meta_json_path = data_cfg.get("meta_json")
        if meta_json_path:
            mj = Path(meta_json_path)
            if not mj.is_absolute():
                mj = (BASE_DIR / mj).resolve()
            if mj.exists():
                try:
                    import json
                    with open(mj, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    axes_list = meta.get("axes")
                    if isinstance(axes_list, list) and axes_list:
                        axis_columns = [str(x) for x in axes_list]
                except Exception:
                    axis_columns = []
        X_mh = try_build_multihot(csv_path, axis_columns) if axis_columns else None
        if X_mh is not None:
            np.save(multihot_path, X_mh)
            nnz = int((X_mh > 0).sum())
            density = nnz / float(X_mh.size)
            print("[06][R-A] multihot_features:")
            print(f"  shape={X_mh.shape}, nnz={nnz}, density={density:.6f}")
            print(f"  → 저장: {multihot_path}")
            built_multihot = True

    if not built_multihot:
        print("[06][R-A] raw terms 소스가 없어 multihot 생성을 건너뜁니다.")

    print("[06] 완료.")


if __name__ == "__main__":
    main()


