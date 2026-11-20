"""Adoption baseline, logistic diffusion and WP3 signal ingestion (interface to O2)."""
from __future__ import annotations

import numpy as np
import pandas as pd

SURVEY_TIME = 2024.55  # mid-point of the Jun-Aug 2024 CSSF/BCL survey


def logit(p):
    p = np.asarray(p, dtype=float)
    return np.log(p / (1 - p))


def calibrate_speed(obs: list[dict], ceiling: float) -> float:
    """Logistic speed r from two or more observations a(t) under ceiling K.

    a(t) = K / (1 + exp(-r (t - t0)))  =>  logit(a/K) = r (t - t0).
    With more than two points r is the OLS slope.
    """
    t = np.array([o["date"] for o in obs], dtype=float)
    y = logit(np.array([o["share"] for o in obs], dtype=float) / ceiling)
    if len(t) == 2:
        return float((y[1] - y[0]) / (t[1] - t[0]))
    return float(np.polyfit(t, y, 1)[0])


def adoption_path(a0, ceiling, speed, t, t_obs: float = SURVEY_TIME):
    """Logistic path passing through a0 at t_obs; arrays broadcast.

    Where the ceiling is not above a0 the share is held constant at a0.
    """
    a0 = np.asarray(a0, dtype=float)
    K = np.maximum(np.asarray(ceiling, dtype=float), a0)
    ratio = np.where(K > a0, (K - a0) / a0, 0.0)
    return K / (1.0 + ratio * np.exp(-np.asarray(speed) * (np.asarray(t) - t_obs)))


def depth_path(d0: float, d_h, base_year: int, horizon: int, year):
    frac = np.clip((np.asarray(year, dtype=float) - base_year) / (horizon - base_year), 0.0, 1.0)
    return d0 + (np.asarray(d_h) - d0) * frac


def apply_signals(subsectors: pd.DataFrame, signals: pd.DataFrame | None, min_docs: int = 30) -> pd.DataFrame:
    """Replace survey-based adoption by WP3 NLP adoption signals where enough documents exist.

    signals columns: subsector, year, adoption_share, n_docs. The latest year per sub-sector
    with n_docs >= min_docs is used; the status column records the provenance.
    """
    out = subsectors.copy()
    if signals is None or signals.empty:
        return out
    s = signals[signals["n_docs"] >= min_docs].sort_values("year").groupby("subsector").tail(1)
    for _, row in s.iterrows():
        mask = out["code"] == row["subsector"]
        out.loc[mask, "adoption_2024"] = float(row["adoption_share"])
        out.loc[mask, "adoption_status"] = f"nlp_signal_{int(row['year'])}"
    return out
