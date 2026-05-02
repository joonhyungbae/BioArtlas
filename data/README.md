# Data Layout

[`data/`](.) is the single home for repo-managed data assets.

## Directories

- `dataset/`: canonical public dataset used by the reproduction pipeline
- `metadata/`: bilingual label metadata, artist labels, and QA reports
- `raw/`: raw source tables used by preprocessing helpers
- `processed/`: derived tables used by helper scripts and the web export path
- `models/`: large local model assets
- `web_migration/`: legacy snapshots migrated from the earlier web repo

## Canonical Files

- [`dataset/BioArtlas.csv`](dataset/BioArtlas.csv): public dataset used by the main pipeline
- [`metadata/artist_labels.csv`](metadata/artist_labels.csv): data-managed artist display labels
- [`metadata/keywords_hierarchy_ko_en_review.csv`](metadata/keywords_hierarchy_ko_en_review.csv):
  manually reviewed KO/EN hierarchy draft
- [`metadata/keywords_hierarchy_ko_en_reviewed.csv`](metadata/keywords_hierarchy_ko_en_reviewed.csv):
  corrected bilingual hierarchy used for mapping
- [`processed/keywords_hierarchy_ko_clean.csv`](processed/keywords_hierarchy_ko_clean.csv):
  cleaned Korean hierarchy exported by preprocessing
- [`processed/bioartlas_axes_bilingual.csv`](processed/bioartlas_axes_bilingual.csv):
  row-aligned bilingual axis table
- [`processed/final_cluster_assignments.csv`](processed/final_cluster_assignments.csv):
  final cluster assignment mirror
- [`processed/bioart_clustering_2d.json`](processed/bioart_clustering_2d.json):
  export payload for the separate interactive web repository

## Notes

- The maintained reproduction path reads `dataset/BioArtlas.csv`.
- The web export path reads `processed/bioartlas_axes_bilingual.csv` and
  `metadata/artist_labels.csv`.
- The default web JSON export is `processed/bioart_clustering_2d.json`.
- If you keep a local ignored `../BioArtlas_web/` checkout, you can mirror that
  export into `../BioArtlas_web/public/bioart_clustering_2d.json` with
  `BIOARTLAS_WEB_JSON_OUT`.
- `models/` and `web_migration/` are kept for local or legacy use and are not
  part of the compact active repo surface.
