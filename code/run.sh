#!/usr/bin/env bash

set -euo pipefail

export PHASEC_UMAP_MIN_DIST_LIST="${PHASEC_UMAP_MIN_DIST_LIST:-0.0,0.01,0.1,0.5}"

python 04_build_embeddings.py
python 05_build_word_codebook.py
python 06_apply_word_codebook.py
python 07_run_clustering_sweep.py
python 09_export_final_artifacts.py
