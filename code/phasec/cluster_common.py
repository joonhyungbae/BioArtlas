from __future__ import annotations

import os
from typing import Optional


def k_preference_bonus(used_k: int, k_value: Optional[int] = None) -> float:
    try:
        pref_min = int(os.getenv("PHASEC_PREF_K_MIN", "10"))
        pref_max = int(os.getenv("PHASEC_PREF_K_MAX", "30"))
        gamma = float(os.getenv("PHASEC_PREF_K_BONUS", "0.0"))
    except Exception:
        pref_min, pref_max, gamma = 10, 30, 0.0

    k_eff = int(k_value) if (k_value is not None and int(k_value) > 0) else int(max(0, used_k))
    if k_eff <= pref_min:
        return gamma * (k_eff - pref_min) / max(1.0, float(pref_min))
    if k_eff >= pref_max:
        return gamma
    return gamma * (k_eff - pref_min) / max(1.0, float(pref_max - pref_min))
