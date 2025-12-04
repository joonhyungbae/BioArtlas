# BioArtlas: Computational Clustering of Multi‑Dimensional Complexity in Bioart

Status: Under review (decision pending).

This repository provides the public dataset and project page for the BioArtlas project.

![BioArtlas Visualization](web/src/assets/bioartlas-visualization.png)

## TL;DR

- **Goal**: Structure the multi‑dimensional complexity of bioart works as data
- **Dataset**: [`BioArtlas.csv`](BioArtlas.csv) (per‑work metadata)
- **Project Page**: [joonhyungbae.github.io/BioArtlas](https://joonhyungbae.github.io/BioArtlas/)
- **Live Visualization**: [bioartlas.com](https://www.bioartlas.com)
- **Contact**: jh.bae@kaist.ac.kr

## Links

| Resource | URL |
|----------|-----|
| 📄 Project Page | https://joonhyungbae.github.io/BioArtlas/ |
| 🌐 Interactive Visualization | https://www.bioartlas.com |
| 📊 Dataset | [`BioArtlas.csv`](BioArtlas.csv) |

## Dataset

- **File**: `BioArtlas.csv`
- **Size (current)**: approximately 81 rows and 17 columns
- **Encoding**: UTF‑8
- **Delimiter**: comma (,)
- **Quoting**: values that contain commas are wrapped in double quotes

### Data Preview

| Artist | Artwork | Year | Gen | ... |
|--------|---------|------|-----|-----|
| Joe Davis | Microvenus | 1986 | 1 | ... |
| George Gessert | Iris Series | 1985- | 1 | ... |
| Eduardo Kac | Genesis | 1999 | 2 | ... |
| Stelarc | Ear on Arm | 2006- | 1 | ... |
| Oron Catts & Ionat Zurr | Victimless Leather | 2004 | 2 | ... |

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

## Quick Start

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

## Interactive Visualization

Explore interactive clustering and 2D projections built from this dataset at: [bioartlas.com](https://www.bioartlas.com)

The visualization includes:
- **8 Clusters** of bioart works
- **79 Artworks** from various artists
- **33 Artists** spanning from 1970s to 2023
- UMAP-based dimensionality reduction
- Interactive filtering by artist, cluster, and year range

## Project Page

For detailed information about the research methodology, key findings, and citation information, visit the project page:

**[https://joonhyungbae.github.io/BioArtlas/](https://joonhyungbae.github.io/BioArtlas/)**

## License

- **Data**: BioArtlas Research‑Only Data License (Noncommercial). See `LICENSE` for details.
- **Code**: MIT License (to be added separately if/when code is included)

Commercial use, internal commercial research, and integration into paid services/products/models are not permitted under this license. For commercial licensing, please contact: jh.bae@kaist.ac.kr.

Proper attribution and preserving the original context are encouraged.

### Recommended Attribution

```
BioArtlas dataset (Research‑Only Data License, Noncommercial). © 2025 Joonhyung Bae. 
Project: https://joonhyungbae.github.io/BioArtlas/
```

## Citation

```bibtex
@inproceedings{bae2025bioartlas,
  title={BioArtlas: Computational Clustering of Multi-Dimensional Complexity in Bioart},
  author={Bae, Joonhyung},
  booktitle={NeurIPS 2025 Creative AI Track},
  year={2025}
}
```

---

## Contact

For questions or collaboration, please contact: jh.bae@kaist.ac.kr
