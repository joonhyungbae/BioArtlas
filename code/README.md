# BioArtlas Reproduction Code

[`code/`](.) contains the maintained reproduction pipeline. It starts from
[`../data/dataset/BioArtlas.csv`](../data/dataset/BioArtlas.csv) and writes
generated results under [`artifacts/`](artifacts/).

Web UI code lives in [`../BioArtlas_web/`](../BioArtlas_web/).

## Setup

```bash
pip install -r requirements.txt
```

## Main Entrypoints

1. `04_build_embeddings.py`
   Builds token-level and axis-level embeddings from the canonical dataset.
2. `05_build_word_codebook.py`
   Learns the word codebook from the token embeddings.
3. `06_apply_word_codebook.py`
   Applies the codebook and exports clustering features.
4. `07_run_clustering_sweep.py`
   Sweeps clustering configurations and saves the best run.
5. `08_build_web_json.py`
   Optional web-export step that refreshes the JSON payload used by the Vue app.
6. `09_export_final_artifacts.py`
   Standardizes the final artifacts under `artifacts/final/`.

The script numbering is kept stable to match the project workflow. Artifact
directory names such as `artifacts/04_embedding/` remain stable for
compatibility with previously generated outputs.

## Run

```bash
bash run.sh
```

## Outputs

Main generated outputs are written to:

- `artifacts/04_embedding/`
- `artifacts/05_word_codebook/`
- `artifacts/06_apply_codebook/`
- `artifacts/final/`

The final curated export lives under [`artifacts/final/`](artifacts/final).

## Verify The Paper

```bash
python verify_paper.py --seeds 50
```

This checks the accepted-paper target configuration:

- Agglomerative clustering
- `k=15`
- 4D UMAP
- `n_neighbors=10`
- `min_dist=0.01`

## Optional Experiments

```bash
python experiments/run_metric_push.py --profile silhouette_push
```

Available profiles are defined in
[`experiments/run_metric_push.py`](experiments/run_metric_push.py).

Manual sweeps can also be run by setting `PHASEC_OUTDIR` and other `PHASEC_*`
environment variables before calling `07_run_clustering_sweep.py`.

## Support Directories

- `preprocess/`: bilingual metadata normalization and processed-table builders
- `exporters/`: helper implementations for web JSON export
- `experiments/`: active non-canonical research workflows
