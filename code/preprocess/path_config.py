from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CODE_DIR = BASE_DIR.parent
REPO_ROOT = CODE_DIR.parent
DATA_DIR = REPO_ROOT / "data"

RAW_DATA_CSV = DATA_DIR / "raw" / "data.csv"
METADATA_DIR = DATA_DIR / "metadata"
PROCESSED_DIR = DATA_DIR / "processed"
QA_REPORTS_DIR = METADATA_DIR / "qa_reports"

KO_HIERARCHY_REVIEW_CSV = METADATA_DIR / "keywords_hierarchy_ko_en_review.csv"
KO_EN_REVIEWED_CSV = METADATA_DIR / "keywords_hierarchy_ko_en_reviewed.csv"

KO_HIERARCHY_CLEAN_CSV = PROCESSED_DIR / "keywords_hierarchy_ko_clean.csv"
KO_HIERARCHY_CLEAN_XLSX = PROCESSED_DIR / "keywords_hierarchy_ko_clean.xlsx"
KO_HIERARCHY_CLEAN_TSV = PROCESSED_DIR / "keywords_hierarchy_ko_clean.tsv"
KO_HIERARCHY_CLEAN_UNQUOTED_CSV = PROCESSED_DIR / "keywords_hierarchy_ko_clean_unquoted.csv"

BIOARTLAS_AXES_BILINGUAL_CSV = PROCESSED_DIR / "bioartlas_axes_bilingual.csv"
UNMAPPED_AXIS_TERMS_CSV = QA_REPORTS_DIR / "unmapped_axis_terms.csv"
