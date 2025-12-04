# BioArtlas: Computational Clustering of Multi‑Dimensional Complexity in Bioart

<p align="center">
  <a href="https://neurips.cc/Conferences/2025"><img src="https://img.shields.io/badge/NeurIPS-2025-blue" alt="NeurIPS 2025"></a>
  <a href="https://joonhyungbae.github.io/BioArtlas/"><img src="https://img.shields.io/badge/Project-Page-green" alt="Project Page"></a>
  <a href="https://www.bioartlas.com"><img src="https://img.shields.io/badge/Demo-Live-orange" alt="Live Demo"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Research--Only-red" alt="License"></a>
</p>

> **🎉 Accepted at NeurIPS 2025 Creative AI Track**

This is the official repository for **BioArtlas**, a computational framework for analyzing bioart through multi-dimensional clustering.

![BioArtlas Visualization](web/src/assets/bioartlas-visualization.png)

## TL;DR

- **Goal**: Structure the multi‑dimensional complexity of bioart works as data
- **Dataset**: [`BioArtlas.csv`](BioArtlas.csv) — 81 works × 17 columns
- **Project Page**: [joonhyungbae.github.io/BioArtlas](https://joonhyungbae.github.io/BioArtlas/)
- **Live Visualization**: [bioartlas.com](https://www.bioartlas.com)
- **Author**: Joonhyung Bae (KAIST)
- **Contact**: jh.bae@kaist.ac.kr

## 📢 News

| Date | Event |
|------|-------|
| **Dec 4, 2025** | 🎤 Presented BioArtlas at NeurIPS 2025 Creative AI Track |
| **Aug 31, 2025** | 🤝 Expanded research collaboration with curators, artists, and biotechnologists |
| **Aug 12, 2025** | 📊 Released complete dataset on GitHub (81 works × 13 dimensions) |

## 🔗 Links

| Resource | URL |
|----------|-----|
| 📄 Project Page | https://joonhyungbae.github.io/BioArtlas/ |
| 🌐 Interactive Visualization | https://www.bioartlas.com |
| 📊 Dataset | [`BioArtlas.csv`](BioArtlas.csv) |

## Abstract

Bioart represents a convergence of artistic practice, biological science, and technological innovation—encompassing transgenic organisms, tissue engineering, and biosemiotic inquiry. Traditional taxonomic frameworks prove insufficient for capturing this multidimensional complexity, as works simultaneously function as aesthetic objects, scientific instruments, ethical provocations, and political statements.

We present **BioArtlas**, a computational framework analyzing **81 significant bioart works** across **thirteen curated analytical dimensions**—materiality, methodology, actor relations, ethical approaches, aesthetic strategies, epistemic functions, philosophical stances, social contexts, audience engagement, temporal and spatial scales, power dynamics, and documentation practices.

**Key Results:**
- **Optimal Configuration**: Agglomerative clustering (k=15) on 4D UMAP
- **Silhouette Coefficient**: 0.664 ± 0.008
- **Neighborhood Preservation**: Trustworthiness/Continuity ≈ 0.81

## Dataset

- **File**: `BioArtlas.csv`
- **Size**: 81 rows × 17 columns
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

### Data Dictionary

| Column | Description | Example |
|--------|-------------|---------|
| `Artist` | Artist name | "Joe Davis" |
| `Artwork` | Work title | "Microvenus" |
| `Year` | Production year/period | `1985-`, `2015–2017` |
| `Gen` | Generation/group index | 1, 2, 3 |
| `Materiality` | Materials/organisms/data | multi‑valued |
| `Methodology` | Methods/technologies | multi‑valued |
| `Actor Relationships & Configuration` | Actor relationships | `Artist‑Led`, `Multi‑Actor Network` |
| `Ethical Approach` | Ethical approach | `Care‑Based`, `Provocative` |
| `Aesthetic Strategy` | Aesthetic strategy | `Conceptual`, `Spectacle` |
| `Epistemic Function` | Epistemic function | `Knowledge Production` |
| `Philosophical Stance` | Philosophical stance | `Posthumanism`, `Ecofeminism` |
| `Social Context` | Exhibition/social context | `Art Gallery`, `Laboratory` |
| `Audience Engagement` | Audience engagement | `Observational`, `Interactive` |
| `Temporal Scale` | Temporal scale/persistence | `Short‑Term`, `Evolutionary` |
| `Spatio Scale` | Spatial scale | `Molecular Unit`, `Global Network` |
| `Power and Capital Critique` | Power/capital critique | `Biopolitics` |
| `Documentation & Representation` | Documentation methods | `Live Video`, `Narrative` |

Multi‑category values are comma‑separated within a quoted string.

## Quick Start

```python
import pandas as pd

df = pd.read_csv('BioArtlas.csv')
print(df.shape)           # (81, 17)
print(df.columns.tolist())

# Convert multi-category columns into lists
multi_cols = [
    'Materiality', 'Methodology', 'Actor Relationships & Configuration',
    'Ethical Approach', 'Aesthetic Strategy', 'Epistemic Function',
    'Philosophical Stance', 'Social Context', 'Audience Engagement',
    'Documentation & Representation', 'Power and Capital Critique'
]
for c in multi_cols:
    if c in df.columns:
        df[c] = df[c].fillna('').apply(
            lambda x: [s.strip() for s in x.split(',')] if isinstance(x, str) and len(x) > 0 else []
        )
```

## Interactive Visualization

Explore interactive clustering and 2D projections at: **[bioartlas.com](https://www.bioartlas.com)**

Features:
- **8 Clusters** of bioart works
- **79 Artworks** from various artists
- **33 Artists** spanning from 1970s to 2023
- UMAP-based dimensionality reduction
- Interactive filtering by artist, cluster, and year range
- Tooltip mode for detailed artwork information

## Citation

If you use this dataset or find our work helpful, please cite:

```bibtex
@inproceedings{bae2025bioartlas,
  title     = {BioArtlas: Computational Clustering of 
               Multi-Dimensional Complexity in Bioart},
  author    = {Bae, Joonhyung},
  booktitle = {Proceedings of the 39th Conference on Neural
               Information Processing Systems},
  year      = {2025},
  note      = {Creative AI Track}
}
```

## License

- **Data**: BioArtlas Research‑Only Data License (Noncommercial). See [`LICENSE`](LICENSE) for details.
- **Code**: MIT License

⚠️ Commercial use, internal commercial research, and integration into paid services/products/models are **not permitted** under this license.

For commercial licensing, please contact: **jh.bae@kaist.ac.kr**

### Recommended Attribution

```
BioArtlas dataset (Research‑Only Data License, Noncommercial). 
© 2025 Joonhyung Bae. Project: https://joonhyungbae.github.io/BioArtlas/
```

---

## Contact

**Joonhyung Bae**  
Graduate School of Culture Technology, KAIST  
📧 jh.bae@kaist.ac.kr

---

<p align="center">
  <i>BioArtlas: Mapping the Complex Landscape of Bioart</i>
</p>
