"""Compatibility facade for phase-C clustering helpers."""

from .cluster_common import k_preference_bonus
from .cluster_density import dbscan_sweep, hdbscan_try, meanshift_try, optics_try
from .cluster_partition import agglom_grid, kmeans_grid
from .cluster_stability import bootstrap_stability, refit_and_predict

__all__ = [
    "agglom_grid",
    "bootstrap_stability",
    "dbscan_sweep",
    "hdbscan_try",
    "k_preference_bonus",
    "kmeans_grid",
    "meanshift_try",
    "optics_try",
    "refit_and_predict",
]
