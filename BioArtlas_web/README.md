# BioArtlas Web

[`BioArtlas_web/`](.) contains the web-facing frontends for the project.

## Contents

- Interactive visualization app: Vue 3 + Vuetify
- Project page frontend: [`project_page/`](project_page/) with React + Vite

## Interactive Visualization

The root app in this directory renders the public interactive visualization and
consumes:

- [`public/bioart_clustering_2d.json`](public/bioart_clustering_2d.json)

Refresh that payload from the reproduction pipeline with:

```bash
python ../code/08_build_web_json.py
```

Run the Vue app locally from this directory:

```bash
npm install
npm run serve
```

Build it with:

```bash
npm run build
```

## Project Page

[`project_page/`](project_page/) is a separate frontend for the landing page,
research summary, and link hub. See its local README for development commands.

## Scope

Reproduction code and canonical dataset management do not live here. Those are
maintained in [`../code/`](../code/) and [`../data/`](../data/).
