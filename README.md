# BioArtlas: Computational Clustering of Multi‑Dimensional Complexity in Bioart

Status: Under review (decision pending).

This repository provides the public dataset for the BioArtlas project.

## TL;DR

- Goal: Structure the multi‑dimensional complexity of bioart works as data
- Dataset: `BioArtlas.csv` (per‑work metadata)
- Live visualization: [bioartlas.com](https://www.bioartlas.com)
- Contact: jh.bae[at]kaist.ac.kr

## Dataset

- File: `BioArtlas.csv`
- Size (current): approximately 81 rows and 17 columns
- Encoding: UTF‑8
- Delimiter: comma (,)
- Quoting: values that contain commas are wrapped in double quotes

## Data Dictionary

- `Artist`: Artist name (e.g., "Joe Davis")
- `Artwork`: Work title (e.g., "Microvenus")
- `Year`: Production year or period (e.g., `1985-`, `2015–2017`)
- `Gen`: Generation/group index (integer category)
- `Materiality`: Materials/organisms/data involved (multi‑valued)
- `Methodology`: Methods/technologies used (multi‑valued)
- `Actor Relationships & Configuration`: Actor relationships and configuration (e.g., `Artist‑Led`, `Multi‑Actor Network`)
- `Ethical Approach`: Ethical approach (e.g., `Care‑Based`, `Relational Ethics`, `Provocative`)
- `Aesthetic Strategy`: Aesthetic strategy (e.g., `Conceptual`, `Spectacle`, `Data Aesthetics`)
- `Epistemic Function`: Epistemic function (e.g., `Knowledge Production`, `Science Communication`)
- `Philosophical Stance`: Philosophical stance (e.g., `Posthumanism`, `Ecofeminism`)
- `Social Context`: Exhibition/social context (e.g., `Art Gallery`, `Laboratory`, `Online Platform`)
- `Audience Engagement`: Audience engagement (e.g., `Observational`, `Interactive`, `Participatory`)
- `Temporal Scale`: Temporal scale/persistence (e.g., `Short‑Term Exhibition`, `Evolutionary`)
- `Spatio Scale`: Spatial scale (e.g., `Molecular Unit`, `Installation Scale`, `Global Network`)
- `Power and Capital Critique`: Power/capital critique (e.g., `Biopolitics`, `Commercialization`)
- `Documentation & Representation`: Documentation/representation (e.g., `Live Video`, `Photographic Records`, `Narrative`)

Multi‑category values are comma‑separated within a quoted string; commas inside quotes are part of the value, not field separators.

## Quick start

```python
import pandas as pd

df = pd.read_csv('BioArtlas.csv')
print(df.shape)           # e.g., (81, 17)
print(df.columns.tolist())

# Convert multi-category columns into lists (example)
multi_cols = [
    'Materiality','Methodology','Actor Relationships & Configuration','Ethical Approach',
    'Aesthetic Strategy','Epistemic Function','Philosophical Stance','Social Context',
    'Audience Engagement','Documentation & Representation','Power and Capital Critique'
]
for c in multi_cols:
    if c in df.columns:
        df[c] = df[c].fillna('').apply(lambda x: [s.strip() for s in x.split(',')] if isinstance(x, str) and len(x) > 0 else [])
```

---

## Live visualization

Explore interactive clustering and 2D projections built from this dataset at: [bioartlas.com](https://www.bioartlas.com)

## License

- Code: MIT License (to be added in `LICENSE`)
- Data: CC BY 4.0 recommended (final data license text to be added)

I encourage proper attribution and preserving the original context when using the dataset in downstream work.

---

## Contact

For questions or collaboration, please contact: jh.bae[at]kaist.ac.kr
