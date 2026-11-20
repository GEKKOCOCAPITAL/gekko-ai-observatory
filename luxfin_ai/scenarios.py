"""Monte-Carlo impact scenarios to 2030 (O3).

For sub-sector s, draw n and year y (all effects relative to a no-AI counterfactual):

  P  = A(y) * D(y)                     effective penetration: adoption share x depth of use
  h  = E * P * g                       share of total working time saved
  dp = -pi * sL * h                    price change from unit-labour-cost saving
  dQ = (1 + dp) ** (-eta) - 1          demand (output volume) response, isoelastic
  dL = (1 + dQ) * (1 - h) + rho*h - 1  employment: remaining hours + hours re-deployed to new tasks
  dVA = dQ + rho * h                   real gross value added
  dLP = (1 + dVA) / (1 + dL) - 1       labour productivity (GVA per employee)

E exposure index (WP2), A logistic adoption calibrated on CSSF/BCL surveys, D depth of use,
g time saving on AI-performed exposed tasks, pi price pass-through, sL labour share of GVA,
eta price elasticity of demand, rho reinstatement (new-task) rate.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .adoption import adoption_path, calibrate_speed, depth_path

SCENARIO_PARAMS = ["ceiling", "speed_multiplier", "depth_2030", "time_saving", "reinstatement"]
COMMON_PARAMS = ["labour_share_va", "price_pass_through", "demand_elasticity"]


def tri(rng, spec, n):
    lo, mode, hi = spec
    if hi == lo:
        return np.full(n, float(lo))
    return rng.triangular(lo, mode, hi, n)


def core_equations(E, P, g, pi, sL, eta, rho):
    h = E * P * g
    dp = -pi * sL * h
    dQ = (1.0 + dp) ** (-eta) - 1.0
    dL = (1.0 + dQ) * (1.0 - h) + rho * h - 1.0
    dVA = dQ + rho * h
    dLP = (1.0 + dVA) / (1.0 + dL) - 1.0
    return {"h": h, "dQ": dQ, "dL": dL, "dVA": dVA, "dLP": dLP}


def draw_parameters(cfg: dict, scenario: str, n: int, rng) -> pd.DataFrame:
    sc = cfg["scenarios"][scenario]
    cm = cfg["common"]
    d = {p: tri(rng, sc[p], n) for p in SCENARIO_PARAMS}
    d.update({p: tri(rng, cm[p], n) for p in COMMON_PARAMS})
    return pd.DataFrame(d)


def simulate(cfg: dict, subsectors: pd.DataFrame, exposure: pd.DataFrame, scenario: str,
             n: int | None = None, seed: int | None = None) -> dict:
    """Run the Monte-Carlo for one scenario. Returns raw arrays (draw x subsector x year)."""
    run = cfg["run"]
    n = n or run["n_draws"]
    seed = run["seed"] if seed is None else seed
    rng = np.random.default_rng([seed, list(cfg["scenarios"]).index(scenario)])
    base, hor = run["base_year"], run["horizon"]
    years = np.arange(base, hor + 1)
    cm = cfg["common"]

    ss = subsectors.merge(exposure[["subsector", "exposure"]], left_on="code", right_on="subsector")
    S = len(ss)
    params = draw_parameters(cfg, scenario, n, rng)
    r_cal = calibrate_speed(cfg["calibration"]["adoption_obs"], cfg["calibration"]["ceiling_central"])

    # sub-sector specific uncertainty
    e_noise = np.clip(rng.normal(1.0, cm["exposure_rating_noise_sd"], (n, S)), 0.5, 1.5)
    E = np.clip(ss["exposure"].to_numpy()[None, :] * e_noise, 0.0, 1.0)
    a_noise = tri(rng, cm["adoption_baseline_noise"], n * S).reshape(n, S)
    proxy = (ss["adoption_status"] == "proxy").to_numpy()
    p_noise = np.where(proxy[None, :], tri(rng, cm["proxy_extra_noise"], n * S).reshape(n, S), 1.0)
    a0 = np.clip(ss["adoption_2024"].to_numpy()[None, :] * a_noise * p_noise, 0.01, 0.95)

    t = years[None, None, :] + 0.5
    K = params["ceiling"].to_numpy()[:, None, None]
    r = (r_cal * params["speed_multiplier"].to_numpy())[:, None, None]
    A = adoption_path(a0[:, :, None], K, r, t)
    D = depth_path(cfg["depth_base"], params["depth_2030"].to_numpy()[:, None, None], base, hor, years[None, None, :])
    P = A * D

    col = lambda name: params[name].to_numpy()[:, None, None]
    res = core_equations(E[:, :, None], P, col("time_saving"), col("price_pass_through"),
                         col("labour_share_va"), col("demand_elasticity"), col("reinstatement"))

    # levels: baseline employment and GVA paths (no-AI counterfactual)
    emp_ref_year = pd.to_datetime(ss["employment_ref_date"]).dt.year.to_numpy()
    L_base = ss["employment"].to_numpy()[:, None] * (1 + ss["baseline_emp_growth"].to_numpy()[:, None]) ** (years[None, :] - emp_ref_year[:, None])
    G_base = ss["gva_eur_m"].to_numpy()[:, None] * (1 + ss["baseline_gva_growth"].to_numpy()[:, None]) ** (years[None, :] - 2024)

    res.update({"A": A, "D": np.broadcast_to(D, A.shape), "P": P, "E": E,
                "jobs": res["dL"] * L_base[None], "gva_eur_m": res["dVA"] * G_base[None],
                "L_base": L_base, "G_base": G_base})
    return {"scenario": scenario, "years": years, "codes": ss["code"].tolist(), "params": params,
            "r_cal": r_cal, "res": res, "E_draw": E, "a0_draw": a0}


def summarise(sim: dict, quantiles=(0.05, 0.5, 0.95)) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Quantile tables by sub-sector-year and for the sector total (aggregated per draw)."""
    res, years, codes = sim["res"], sim["years"], sim["codes"]
    qs = list(quantiles)
    rows = []
    for metric in ["A", "P", "h", "dLP", "dL", "dVA", "jobs", "gva_eur_m"]:
        arr = res[metric]
        qv = np.quantile(arr, qs, axis=0)  # q x S x Y
        for i, c in enumerate(codes):
            for j, y in enumerate(years):
                rows.append({"scenario": sim["scenario"], "subsector": c, "year": int(y), "metric": metric,
                             **{f"p{int(q*100):02d}": float(qv[k, i, j]) for k, q in enumerate(qs)},
                             "mean": float(arr[:, i, j].mean())})
    by_sub = pd.DataFrame(rows)

    # sector totals computed per draw, then quantiles (preserves correlation across sub-sectors)
    L_base, G_base = res["L_base"], res["G_base"]
    tot = {
        "jobs": res["jobs"].sum(axis=1),
        "gva_eur_m": res["gva_eur_m"].sum(axis=1),
    }
    tot["dL"] = tot["jobs"] / L_base.sum(axis=0)[None, :]
    tot["dVA"] = tot["gva_eur_m"] / G_base.sum(axis=0)[None, :]
    tot["dLP"] = (1 + tot["dVA"]) / (1 + tot["dL"]) - 1
    w = L_base / L_base.sum(axis=0)[None, :]
    tot["P"] = (res["P"] * w[None]).sum(axis=1)
    tot["A"] = (res["A"] * w[None]).sum(axis=1)
    tot["h"] = (res["h"] * w[None]).sum(axis=1)
    rows = []
    for metric, arr in tot.items():
        qv = np.quantile(arr, qs, axis=0)
        for j, y in enumerate(years):
            rows.append({"scenario": sim["scenario"], "subsector": "TOTAL", "year": int(y), "metric": metric,
                         **{f"p{int(q*100):02d}": float(qv[k, j]) for k, q in enumerate(qs)},
                         "mean": float(arr[:, j].mean())})
    total = pd.DataFrame(rows)
    sim["totals_draws"] = tot
    return by_sub, total


def sensitivity(sim: dict, target: str = "dL", year: int | None = None) -> pd.DataFrame:
    """Spearman rank correlation of each uncertain input with the sector-total outcome."""
    years = sim["years"]
    j = len(years) - 1 if year is None else int(np.where(years == year)[0][0])
    y = sim["totals_draws"][target][:, j]
    p = sim["params"].copy()
    w = sim["res"]["L_base"][:, j] / sim["res"]["L_base"][:, j].sum()
    p["exposure_noise(emp-weighted)"] = sim["E_draw"] @ w
    p["adoption_baseline(emp-weighted)"] = sim["a0_draw"] @ w
    out = []
    for c in p.columns:
        rho, _ = stats.spearmanr(p[c], y)
        out.append({"parameter": c, "spearman_rho": float(rho)})
    df = pd.DataFrame(out)
    df["abs"] = df["spearman_rho"].abs()
    return df.sort_values("abs", ascending=False).drop(columns="abs").reset_index(drop=True)
