# BioArtlas

BioArtlas is a computational framework for analyzing bioart through
multi-dimensional clustering. This repository contains the public dataset, the
maintained reproduction pipeline, and the interactive web frontends.

## Links

- Project page: https://joonhyungbae.github.io/BioArtlas/
- Interactive visualization: https://www.bioartlas.com
- Dataset: [`data/dataset/BioArtlas.csv`](data/dataset/BioArtlas.csv)
- Reproduction pipeline: [`code/`](code/)

## Repository Layout

- [`code/`](code/): maintained reproduction pipeline and verification scripts
- [`data/`](data/): canonical dataset, metadata, raw tables, and processed tables
- [`BioArtlas_web/`](BioArtlas_web/): web-facing frontends
- [`BioArtlas_web/project_page/`](BioArtlas_web/project_page/): landing/project page frontend

## Dataset

The canonical public dataset is [`data/dataset/BioArtlas.csv`](data/dataset/BioArtlas.csv).
It covers 81 bioart works across 13 analytical dimensions.

Important companion tables live under [`data/`](data/):

- [`data/metadata/keywords_hierarchy_ko_en_review.csv`](data/metadata/keywords_hierarchy_ko_en_review.csv):
  manually reviewed KO/EN keyword hierarchy draft
- [`data/metadata/keywords_hierarchy_ko_en_reviewed.csv`](data/metadata/keywords_hierarchy_ko_en_reviewed.csv):
  corrected bilingual hierarchy used for mapping
- [`data/processed/bioartlas_axes_bilingual.csv`](data/processed/bioartlas_axes_bilingual.csv):
  row-aligned bilingual axis table used by helpers and web export
- [`data/processed/final_cluster_assignments.csv`](data/processed/final_cluster_assignments.csv):
  mirrored final cluster assignment table

## Reproduce The Pipeline

Install dependencies and run the maintained pipeline from [`code/`](code/):

```bash
cd code
pip install -r requirements.txt
bash run.sh
```

The standard final outputs are written to
[`code/artifacts/final/`](code/artifacts/final).

To verify the accepted-paper target configuration:

```bash
cd code
python verify_paper.py --seeds 50
```

## Web Frontends

[`BioArtlas_web/`](BioArtlas_web/) contains the interactive Vue visualization.
It consumes [`BioArtlas_web/public/bioart_clustering_2d.json`](BioArtlas_web/public/bioart_clustering_2d.json),
which can be refreshed from the reproduction outputs with:

```bash
python code/08_build_web_json.py
```

[`BioArtlas_web/project_page/`](BioArtlas_web/project_page/) contains the
separate React/Vite landing page.

## Citation

```bibtex
@inproceedings{bae2025bioartlas,
  title     = {BioArtlas: Computational Clustering of Multi-Dimensional Complexity in Bioart},
  author    = {Bae, Joonhyung},
  booktitle = {Proceedings of the 39th Conference on Neural Information Processing Systems},
  year      = {2025},
  note      = {Creative AI Track}
}
```

## License

- Data: research-only, noncommercial use. See [`LICENSE`](LICENSE).
- Code: MIT License.

For licensing questions, contact `jh.bae@kaist.ac.kr`.
