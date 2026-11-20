"""Integrated, reproducible end-to-end pipeline (O5)."""
from __future__ import annotations

import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import __version__
from . import adoption as ad
from . import exposure as ex
from . import figures as fg
from . import io
from . import risk as rk
from . import scenarios as sc
from . import validation as va

EXPECTED_OUTPUTS = [
    "exposure_index.csv", "exposure_by_occupation.csv", "scenario_subsector.csv", "scenario_total.csv",
    "sensitivity_central.csv", "risk_use_case_grid.csv", "ai_act_classification.csv", "risk_subsector.csv",
    "risk_exposure.csv", "validation_results.csv", "dashboard_data.json", "run_manifest.json",
]


def run(config: str | Path = "config/default.yaml", out_dir: str | Path = "outputs", figures: bool = True,
        n_draws: int | None = None) -> dict:
    t0 = time.time()
    cfg = io.load_config(config)
    if n_draws:
        cfg["run"]["n_draws"] = n_draws
    out = io.resolve(out_dir)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    inputs = io.load_inputs(cfg)
    checks = va.check_inputs(inputs)

    subsectors = ad.apply_signals(inputs["subsectors"], inputs.get("adoption_signals"))
    names = dict(zip(subsectors["code"], subsectors["name"]))

    # O1 interface - exposure
    expo = ex.exposure_index(inputs["tasks"])
    expo.to_csv(out / "exposure_index.csv", index=False)
    occ = ex.exposure_by_occupation(inputs["tasks"], subsectors)
    occ.to_csv(out / "exposure_by_occupation.csv", index=False)

    # O3 - scenarios
    sims, subs, tots = {}, [], []
    for s in cfg["scenarios"]:
        sims[s] = sc.simulate(cfg, subsectors, expo, s)
        a, b = sc.summarise(sims[s], cfg["run"]["quantiles"])
        subs.append(a); tots.append(b)
    subs, tots = pd.concat(subs), pd.concat(tots)
    subs.to_csv(out / "scenario_subsector.csv", index=False)
    tots.to_csv(out / "scenario_total.csv", index=False)
    sens = pd.concat([sc.sensitivity(sims["central"], "dL").assign(target="employment 2030"),
                      sc.sensitivity(sims["central"], "dVA").assign(target="real GVA 2030")])
    sens.to_csv(out / "sensitivity_central.csv", index=False)

    # O4 - risk
    controls = rk.controls_dict(inputs["controls"])
    grid = rk.use_case_grid(inputs["use_cases"], controls, inputs["taxonomy"])
    grid.to_csv(out / "risk_use_case_grid.csv", index=False)
    cls = pd.DataFrame([{"use_case_id": r["id"], "use_case": r["name"], **rk.classify_ai_act(r.to_dict())}
                        for _, r in inputs["use_cases"].iterrows()])
    cls.to_csv(out / "ai_act_classification.csv", index=False)
    sub_risk = rk.subsector_risk(grid, inputs["use_case_mix"])
    sub_risk.to_csv(out / "risk_subsector.csv", index=False)

    # O5 - integration: risk exposure grows with scenario adoption paths
    A = subs[(subs["metric"] == "A")][["scenario", "subsector", "year", "p50"]].rename(columns={"p50": "A"})
    rx = pd.concat([rk.risk_exposure(sub_risk, A[A["scenario"] == s].drop(columns="scenario")).assign(scenario=s)
                    for s in cfg["scenarios"]])
    rx.to_csv(out / "risk_exposure.csv", index=False)

    # validation
    checks += va.check_scenarios(cfg, sims, tots, subs, subsectors, expo)
    checks += va.check_risk(inputs, grid)
    h1 = va.array_hash(sims["central"]["res"]["dL"], sims["central"]["res"]["dVA"])
    rerun = sc.simulate(cfg, subsectors, expo, "central")
    h2 = va.array_hash(rerun["res"]["dL"], rerun["res"]["dVA"])
    checks.append(va._r("O5", "Determinism: identical results when re-run with the same seed", "PASS" if h1 == h2 else "FAIL",
                        f"{h1} / {h2}"))
    covered = int(subsectors["employment"].sum())
    checks.append(va._r("O5", "Employment covered by integrated sub-sectors (CSSF/CAA-registered entities)", "INFO",
                        f"{covered:,} employees in {len(subsectors)} sub-sectors",
                        "", "LFF 2024 total of 73,272 also includes legal/audit/consulting (~28%), holdings and other financial services"))

    if figures:
        f = out / "figures"
        fg.fan_total(tots, "jobs", "Jobs vs no-AI baseline", "Sector employment effect (median, 90% band)", f / "fan_jobs.png")
        fg.fan_total(tots, "gva_eur_m", "EUR m (real) vs no-AI baseline", "Sector real GVA effect (median, 90% band)", f / "fan_gva.png")
        fg.fan_total(tots, "dLP", "% vs no-AI baseline", "Sector labour-productivity effect (median, 90% band)", f / "fan_lp.png", pct=True)
        fg.bars_subsector(subs, names, "dL", cfg["run"]["horizon"], "% employment vs no-AI baseline, 2030",
                          "Employment effect by sub-sector, 2030 (median, 90% range)", f / "subsector_employment.png")
        fg.bars_subsector(subs, names, "dLP", cfg["run"]["horizon"], "% labour productivity vs no-AI baseline, 2030",
                          "Productivity effect by sub-sector, 2030 (median, 90% range)", f / "subsector_productivity.png")
        fg.heatmap(sub_risk, {k: k for k in names}, f / "risk_heatmap.png")
        fg.tornado(sens[sens["target"] == "employment 2030"].drop(columns="target"),
                   "What drives the 2030 employment effect (S2 Central)", f / "tornado_employment.png")

    val = pd.DataFrame(checks)
    val.insert(0, "id", [f"V{i+1:02d}" for i in range(len(val))])
    val.to_csv(out / "validation_results.csv", index=False)

    # dashboard payload
    dash = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "version": __version__,
        "subsectors": subsectors[["code", "name", "employment", "employment_ref_date", "employment_status",
                                  "gva_eur_m", "adoption_2024", "adoption_status"]].merge(
            expo, left_on="code", right_on="subsector").drop(columns="subsector").to_dict("records"),
        "scenario_total": tots.to_dict("records"),
        "scenario_subsector": subs[subs["metric"].isin(["A", "dLP", "dL", "dVA", "jobs", "gva_eur_m"])].to_dict("records"),
        "risk_subsector": sub_risk.to_dict("records"),
        "risk_exposure": rx[["scenario", "subsector", "year", "category_id", "exposure_index"]].to_dict("records"),
        "ai_act": cls.to_dict("records"),
        "sensitivity": sens.to_dict("records"),
        "validation": val.to_dict("records"),
        "calibration": {"r": sims["central"]["r_cal"], "obs": cfg["calibration"]["adoption_obs"]},
    }
    (out / "dashboard_data.json").write_text(json.dumps(dash, indent=1, default=float), encoding="utf-8")

    root = Path(cfg["_root"])
    input_files = [io.resolve(p, root) for p in [config, *[v for v in cfg["data"].values() if v],
                                                  "data/controls_baseline.csv", "data/sources.csv"]]
    manifest = {
        "toolkit_version": __version__, "run_utc": dash["generated"], "python": platform.python_version(),
        "numpy": np.__version__, "pandas": pd.__version__, "seed": cfg["run"]["seed"], "n_draws": cfg["run"]["n_draws"],
        "runtime_s": round(time.time() - t0, 1),
        "inputs": {str(p.relative_to(root)): io.sha256(p) for p in input_files},
        "results_hash_central": h1,
        "validation_summary": val["status"].value_counts().to_dict(),
    }
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    manifest["outputs_present"] = all((out / f).exists() for f in EXPECTED_OUTPUTS)
    return {"cfg": cfg, "sims": sims, "subs": subs, "tots": tots, "sens": sens, "grid": grid, "cls": cls,
            "sub_risk": sub_risk, "rx": rx, "val": val, "expo": expo, "occ": occ, "subsectors": subsectors,
            "manifest": manifest, "out": out}
