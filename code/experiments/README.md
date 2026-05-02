# Experiments

This directory is reserved for active, non-canonical research experiments that
build on the official reproduction outputs in [`../artifacts/`](../artifacts/).

## Active Contents

- `run_metric_push.py`: parameter-sweep launcher for better clustering metrics
- `gpt_pipeline/`: alternative research workflow using the official embedding
  artifacts as inputs

## Cleanup Notes

- The duplicated bootstrap scripts in `gpt_pipeline/01-04` are thin
  compatibility wrappers with the same step names as the canonical pipeline,
  forwarding to the maintained scripts in [`../`](..) and
  [`../preprocess/`](../preprocess/).
- If you are reproducing the accepted paper, use [`../run.sh`](../run.sh) and
  [`../verify_paper.py`](../verify_paper.py) instead of the experiment
  directory.
