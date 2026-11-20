"""Task-level AI-exposure index (interface to WP2 / O1).

Each task carries a share of working time and an exposure rating following the
E0/E1/E2 rubric of Eloundou et al. (2024): E1 (directly exposed to an LLM) = 1.0,
E2 (exposed when the LLM is combined with tools) = 0.5, E0 (not exposed) = 0.0.
The sub-sector index is the time-weighted mean, i.e. beta = E1 + 0.5 * E2.

The ratings shipped in data/tasks.csv are provisional (LLM-assisted, v0.1) and are
replaced by the human-validated WP2 task database when available.
"""
from __future__ import annotations

import pandas as pd

VALID_RATINGS = {0.0, 0.5, 1.0}


def validate_tasks(tasks: pd.DataFrame, tol: float = 1e-6) -> list[str]:
    errors = []
    bad = tasks.loc[~tasks["rating"].isin(VALID_RATINGS), "task_id"].tolist()
    if bad:
        errors.append(f"invalid ratings for tasks {bad}")
    sums = tasks.groupby("subsector")["time_share"].sum()
    for s, v in sums.items():
        if abs(v - 1.0) > tol:
            errors.append(f"time shares for {s} sum to {v:.4f} (expected 1)")
    if tasks["task_id"].duplicated().any():
        errors.append("duplicate task ids")
    return errors


def exposure_index(tasks: pd.DataFrame) -> pd.DataFrame:
    t = tasks.copy()
    t["w"] = t["time_share"] * t["rating"]
    t["e1"] = t["time_share"] * (t["rating"] == 1.0)
    t["e2"] = t["time_share"] * (t["rating"] == 0.5)
    g = t.groupby("subsector")
    out = pd.DataFrame({
        "exposure": g["w"].sum() / g["time_share"].sum(),
        "e1_share": g["e1"].sum(),
        "e2_share": g["e2"].sum(),
        "n_tasks": g.size(),
    })
    out["e0_share"] = 1 - out["e1_share"] - out["e2_share"]
    return out.reset_index()


def exposure_by_occupation(tasks: pd.DataFrame, subsectors: pd.DataFrame) -> pd.DataFrame:
    """Employment-weighted exposure by ISCO-08 major group (1-digit)."""
    t = tasks.merge(subsectors[["code", "employment"]], left_on="subsector", right_on="code")
    t["jobs"] = t["time_share"] * t["employment"]
    t["isco1"] = t["isco08"].astype(str).str[0]
    names = {"1": "Managers", "2": "Professionals", "3": "Technicians and associate professionals",
             "4": "Clerical support workers"}
    g = t.groupby("isco1")
    out = pd.DataFrame({
        "exposure": (g.apply(lambda x: (x["rating"] * x["jobs"]).sum() / x["jobs"].sum(), include_groups=False)),
        "fte_equivalent": g["jobs"].sum(),
    }).reset_index()
    out["isco_major_group"] = out["isco1"].map(names)
    return out[["isco1", "isco_major_group", "exposure", "fte_equivalent"]]


def employment_weighted_exposure(expo: pd.DataFrame, subsectors: pd.DataFrame) -> float:
    m = expo.merge(subsectors[["code", "employment"]], left_on="subsector", right_on="code")
    return float((m["exposure"] * m["employment"]).sum() / m["employment"].sum())
