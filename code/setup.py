#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
setup.py
- conda 환경(bio, Python 3.10) 생성 및 의존성 설치 자동화 스크립트
- 본 프로젝트 스크립트(01~04, 05_phaseA_*, 06_phaseB_clustering.py) 실행에 필요한 패키지 일괄 설치

GPU(PyTorch CUDA) 설치 옵션:
- 항상 GPU 빌드만 설치합니다. CPU 빌드는 지원하지 않습니다.
- --torch-index-url 로 PyTorch CUDA 휠 인덱스를 지정하면 해당 GPU 빌드를 설치합니다.
  예) --torch-index-url https://download.pytorch.org/whl/cu124  또는  cu121
  (cu129는 존재하지 않으며 자동으로 cu124로 대체됩니다.)
  미지정 시 기본값은 cu124이며, 실패하면 자동으로 cu121로 폴백합니다.

사용 예시:
  python3 setup.py                                   # env=bio, python=3.10 기본값, GPU torch(cu124)
  python3 setup.py --env bio --py 3.10 \
      --torch-index-url https://download.pytorch.org/whl/cu124   # CUDA 12.4 빌드

주의: conda가 설치되어 있어야 합니다.
"""

from __future__ import annotations
import argparse
import shutil
import subprocess
import sys
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent

CONDA_PACKAGES = [
    # 핵심
    "python=3.10",
    # 데이터/과학 연산
    "pandas>=2.0",
    "numpy>=1.23",
    # 머신러닝/클러스터링
    "scikit-learn>=1.4",
    "umap-learn>=0.5.9",
    # 유틸
    "tqdm",
    "scipy",
    "matplotlib",
    "hdbscan",
    "pyyaml",
    "seaborn",
    # PyTorch (CPU 기본). GPU 환경이면 사용자 측에서 cudatoolkit 조합 설치 권장.
    # pytorch 채널에서 가져옴
]

# 채널 구성: pytorch는 별도 채널, 나머지는 conda-forge 우선
CONDA_CHANNELS = ["-c", "pytorch", "-c", "conda-forge"]


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def conda_exists() -> bool:
    return shutil.which("conda") is not None


def env_exists(env_name: str) -> bool:
    """Check env existence by attempting to run a trivial command in it.
    This avoids false positives from substring matching in `conda env list`.
    """
    try:
        subprocess.run([
            "conda", "run", "-n", env_name, "python", "-c", "import sys; print('ok')"
        ], check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default="bio", help="conda 환경 이름")
    ap.add_argument("--py", default="3.10", help="Python 버전")
    ap.add_argument("--torch-index-url", default=None, help="PyTorch CUDA pip index-url 또는 별칭(cu121|cu124). 예: https://download.pytorch.org/whl/cu124 | cu121")
    args = ap.parse_args()

    if not conda_exists():
        print("[setup] conda가 감지되지 않았습니다. Miniconda/Anaconda 설치 후 다시 시도하세요.", file=sys.stderr)
        sys.exit(1)

    env_name = args.env
    py_ver = args.py

    # 환경 생성 (이미 있으면 건너뜀)
    if not env_exists(env_name):
        print(f"[setup] conda env '{env_name}' 생성 (python={py_ver}) ...")
        run(["conda", "create", "-y", "-n", env_name, f"python={py_ver}"])
    else:
        print(f"[setup] conda env '{env_name}'가 이미 존재합니다. 생성 단계는 건너뜁니다.")

    # 패키지 설치 (PyTorch/torchvision 제외; pip로 설치)
    print("[setup] 패키지 설치(채널: pytorch, conda-forge) ...")
    # python=3.10은 이미 포함되어 있으므로 제외하고 설치
    install_pkgs = [p for p in CONDA_PACKAGES if not p.startswith("python=")]
    try:
        run(["conda", "install", "-y", "-n", env_name] + CONDA_CHANNELS + install_pkgs)
    except subprocess.CalledProcessError as e:
        # 환경 경로 불일치 등으로 실패 시 한 번 더 보수적으로 재시도
        print("[setup] 설치 재시도: 환경 보장 후 다시 시도합니다 ...")
        if not env_exists(env_name):
            run(["conda", "create", "-y", "-n", env_name, f"python={py_ver}"])
        run(["conda", "install", "-y", "-n", env_name] + CONDA_CHANNELS + install_pkgs)

    # pip 최신화 및 PyTorch/torchvision 설치 (GPU only)
    print("[setup] pip 업그레이드 ...")
    run(["conda", "run", "-n", env_name, "python", "-m", "pip", "install", "--upgrade", "pip"])

    # 선행 제거(혼선 방지)
    try:
        run(["conda", "run", "-n", env_name, "python", "-m", "pip", "uninstall", "-y", "torch", "torchvision", "torchaudio"])  # noqa: E501
    except subprocess.CalledProcessError:
        pass

    if args.torch_index_url:
        # 별칭/URL 정규화 (GPU 전용)
        raw_value = args.torch_index_url.strip()
        alias = raw_value.lower()
        if alias == "cpu":
            print("[setup] 오류: 이 스크립트는 GPU 전용입니다. 'cpu' 별칭은 지원하지 않습니다.", file=sys.stderr)
            sys.exit(2)
        if alias == "cu121":
            torch_index_url = "https://download.pytorch.org/whl/cu121"
        elif alias == "cu124":
            torch_index_url = "https://download.pytorch.org/whl/cu124"
        elif "download.pytorch.org/whl/cu129" in raw_value or alias == "cu129":
            print("[setup] 경고: cu129 채널은 존재하지 않습니다. cu124로 자동 대체합니다.")
            torch_index_url = "https://download.pytorch.org/whl/cu124"
        else:
            torch_index_url = raw_value  # 사용자가 직접 URL 제공

        print(f"[setup] Installing PyTorch (GPU 채널) from: {torch_index_url}")
        run(["conda", "run", "-n", env_name, "python", "-m", "pip", "install",
             "torch", "torchvision", "--index-url", torch_index_url])
    else:
        # 기본 GPU 채널(cu124) 시도, 실패 시 cu121로 폴백
        primary = "https://download.pytorch.org/whl/cu124"
        fallback = "https://download.pytorch.org/whl/cu121"
        print(f"[setup] Installing PyTorch (GPU 기본 채널) from: {primary}")
        try:
            run(["conda", "run", "-n", env_name, "python", "-m", "pip", "install",
                 "torch", "torchvision", "--index-url", primary])
        except subprocess.CalledProcessError:
            print(f"[setup] 1차 설치 실패. 폴백 채널로 재시도: {fallback}")
            run(["conda", "run", "-n", env_name, "python", "-m", "pip", "install",
                 "torch", "torchvision", "--index-url", fallback])

    # sentence-transformers는 pip로 설치하여 torch와 호환 보장
    run(["conda", "run", "-n", env_name, "python", "-m", "pip", "install", "sentence-transformers"]) 

    # 헬스 체크: 주요 모듈 import 검사
    print("[setup] 설치 확인(import test) ...")
    code = (
        "import pandas, numpy, sklearn, umap, tqdm, sentence_transformers, matplotlib; "
        "import torch; "
        "import hdbscan; "
        "print('OK:', pandas.__version__, numpy.__version__, sklearn.__version__, torch.__version__, 'CUDA:', torch.cuda.is_available())"
    )
    run(["conda", "run", "-n", env_name, "python", "-c", code])

    print("[setup] 완료: conda env '", env_name, "'", sep="")
    print("  활성화:    conda activate", env_name)
    print("  실행 예시1: conda run -n", env_name, "python 05_phaseA_benchmark.py", sep=" ")
    print("  실행 예시2: conda run -n", env_name, "python 06_phaseB_clustering.py", sep=" ")


if __name__ == "__main__":
    main()
