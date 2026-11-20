"""Automated validation checks for O3 (scenarios), O4 (risk) and O5 (integration)."""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from . import exposure as ex
from . import risk as rk
from . import scenarios as sc
from .adoption import adoption_path, calibrate_speed


def _r(obj, check, status, value="", threshold="", note=""):
    return {"objective": obj, "check": check, "status": status, "value": value,
            "threshold": threshold, "note": note}


def array_hash(*arrays) -> str:
    h = hashlib.sha256()
    for a in arrays:
        h.update(np.ascontiguousarray(np.round(a, 12)).tobytes())
    return h.hexdigest()[:16]


# ---------------------------------------------------------------- inputs
def check_inputs(inputs: dict) -> list[dict]:
    out = []
    errs = ex.validate_tasks(inputs["tasks"])
    out.append(_r("O5", "Task database integrity (ratings in {0,0.5,1}; time shares sum to 1)",
                  "PASS" if not errs else "FAIL", "; ".join(errs) or "no errors"))
    mix = inputs["use_case_mix"].set_index("subsector")
    dev = float((mix.sum(axis=1) - 1).abs().max())
    out.append(_r("O5", "Use-case mix rows sum to 1", "PASS" if dev < 1e-6 else "FAIL", f"{dev:.2e}", "< 1e-6"))
    codes = set(inputs["subsectors"]["code"])
    missing = codes - set(inputs["tasks"]["subsector"]) | codes - set(mix.index)
    out.append(_r("O5", "Every sub-sector has tasks and a use-case mix", "PASS" if not missing else "FAIL",
                  ", ".join(sorted(missing)) or "all present"))
    return out


# ---------------------------------------------------------------- O3
def check_scenarios(cfg, sims: dict, totals: pd.DataFrame, subs: pd.DataFrame, subsectors, expo) -> list[dict]:
    out = []
    hor = cfg["run"]["horizon"]

    # identities on the raw draws
    errs = []
    for s in sims.values():
        r = s["res"]
        lhs = (1 + r["dVA"]) / (1 + r["dL"]) - 1
        errs.append(np.abs(lhs - r["dLP"]).max())
    out.append(_r("O3", "Accounting identity dLP = (1+dVA)/(1+dL)-1 on all draws", "PASS" if max(errs) < 1e-9 else "FAIL",
                  f"max error {max(errs):.1e}", "< 1e-9"))

    z = sc.core_equations(E=0.6, P=0.0, g=0.3, pi=0.5, sL=0.5, eta=0.7, rho=0.2)
    zero = max(abs(v) for v in z.values())
    out.append(_r("O3", "Zero adoption implies zero impact", "PASS" if zero < 1e-12 else "FAIL", f"max |effect| {zero:.1e}", "< 1e-12"))

    Es = np.linspace(0, 1, 21)
    zz = sc.core_equations(E=Es, P=0.5, g=0.3, pi=0.5, sL=0.5, eta=0.7, rho=0.2)
    mono = bool(np.all(np.diff(zz["h"]) > 0) and np.all(np.diff(zz["dLP"]) > 0))
    out.append(_r("O3", "Monotonicity: higher exposure -> more time saved and higher productivity", "PASS" if mono else "FAIL", "21 exposure grid points (0 to 1)"))

    obs = cfg["calibration"]["adoption_obs"]
    r_cal = calibrate_speed(obs, cfg["calibration"]["ceiling_central"])
    fit = float(adoption_path(obs[0]["share"], cfg["calibration"]["ceiling_central"], r_cal, obs[1]["date"], obs[0]["date"]))
    out.append(_r("O3", "Diffusion calibration reproduces CSSF/BCL adoption 2021/22 -> 2024 (30% -> 43%)",
                  "PASS" if abs(fit - obs[1]["share"]) < 1e-6 else "FAIL",
                  f"r = {r_cal:.3f}/yr; fitted 2024 share = {fit:.3f}", "|error| < 1e-6",
                  "Exactly identified with two survey waves - calibration, not an out-of-sample test"))

    # convergence: N vs N/2 and seed stability
    c = sims["central"]
    tot = c["totals_draws"]["dL"][:, -1]
    n = len(tot)
    half = np.median(tot[: n // 2])
    full = np.median(tot)
    rel = abs(half - full) / max(abs(full), 1e-9)
    out.append(_r("O3", "Monte-Carlo convergence: median 2030 employment effect, N/2 vs N draws", "PASS" if rel < 0.02 else "REVIEW",
                  f"relative difference {rel:.3%}", "< 2%"))

    alt = sc.simulate(cfg, subsectors, expo, "central", seed=cfg["run"]["seed"] + 1)
    sc.summarise(alt)
    med_alt = np.median(alt["totals_draws"]["dL"][:, -1])
    rel2 = abs(med_alt - full) / max(abs(full), 1e-9)
    out.append(_r("O3", "Seed stability: median 2030 employment effect under a different seed", "PASS" if rel2 < 0.02 else "REVIEW",
                  f"relative difference {rel2:.3%}", "< 2%"))

    t = totals[(totals["year"] == hor) & (totals["metric"] == "dLP")].set_index("scenario")["p50"]
    ordered = t["cautious"] < t["central"] < t["accelerated"]
    out.append(_r("O3", "Scenario ordering of median 2030 productivity effect (S1 < S2 < S3)", "PASS" if ordered else "FAIL",
                  " < ".join(f"{k} {v:.2%}" for k, v in t.items())))

    q = pd.concat([subs, totals])
    q = q[q["metric"].isin(["dLP", "dL", "dVA", "jobs", "gva_eur_m"]) & (q["year"] > cfg["run"]["base_year"])]
    ok = bool(((q["p05"] <= q["p50"]) & (q["p50"] <= q["p95"]) & (q["p95"] > q["p05"])).all())
    out.append(_r("O3", "Documented uncertainty: p05 <= p50 <= p95 with non-zero width for every sub-sector, year and metric",
                  "PASS" if ok else "FAIL", f"{len(q)} ranges checked"))

    yrs = hor - cfg["run"]["base_year"]
    ann = {k: (1 + v) ** (1 / yrs) - 1 for k, v in t.items()}
    band = {"cautious": (0.0005, 0.01), "central": (0.002, 0.03), "accelerated": (0.005, 0.06)}
    within = all(band[k][0] <= ann[k] <= band[k][1] for k in ann)
    out.append(_r("O3", "Plausibility vs literature: implied annual labour-productivity contribution 2025-2030",
                  "PASS" if within else "REVIEW",
                  "; ".join(f"{k} {v:.2%}/yr" for k, v in ann.items()),
                  "S1 0.05-1%, S2 0.2-3%, S3 0.5-6% per year",
                  "Bands bracket Acemoglu (2024) economy-wide lower bound and task-level field evidence (14-40% time savings) scaled by exposure and adoption"))

    cover = subs.groupby(["scenario", "metric"])["subsector"].nunique().min()
    out.append(_r("O3", "Coverage: every sub-sector has ranges for every scenario, metric and year",
                  "PASS" if cover == len(subsectors) else "FAIL", f"{cover}/{len(subsectors)} sub-sectors"))
    return out


# ---------------------------------------------------------------- O4
def check_risk(inputs: dict, grid: pd.DataFrame) -> list[dict]:
    out = []
    tax = inputs["taxonomy"]
    no_ref = [c["id"] for c in tax["categories"] if not (c["ai_act"] or c["dora"] or c["other"])]
    out.append(_r("O4", "Every risk category maps to at least one regulatory reference", "PASS" if not no_ref else "FAIL",
                  ", ".join(no_ref) or f"{len(tax['categories'])}/{len(tax['categories'])} mapped"))

    fsb_covered = {v for c in tax["categories"] for v in c["fsb"]}
    miss = set(tax["fsb_vulnerabilities"]) - fsb_covered
    out.append(_r("O4", "All FSB (2024) AI vulnerabilities covered by the taxonomy", "PASS" if not miss else "FAIL",
                  ", ".join(miss) or f"{len(tax['fsb_vulnerabilities'])}/{len(tax['fsb_vulnerabilities'])} covered"))

    dora = sum(1 for c in tax["categories"] if c["dora"])
    aia = sum(1 for c in tax["categories"] if c["ai_act"])
    out.append(_r("O4", "Alignment depth: categories referencing the AI Act / DORA", "PASS" if dora >= 4 and aia >= 8 else "REVIEW",
                  f"AI Act {aia}/11, DORA {dora}/11", "AI Act >= 8, DORA >= 4"))

    bad_w = []
    for c in tax["categories"]:
        for k in ("likelihood", "impact"):
            if abs(sum(c[k].values()) - 1) > 1e-9:
                bad_w.append(f"{c['id']}.{k}")
    out.append(_r("O4", "Likelihood and impact weights sum to 1 (scores bounded 1-25)", "PASS" if not bad_w else "FAIL",
                  ", ".join(bad_w) or "all valid"))

    uc = inputs["use_cases"]
    got = uc.apply(lambda r: rk.classify_ai_act(r.to_dict())["class"], axis=1)
    hits = int((got == uc["expected_class"]).sum())
    out.append(_r("O4", "AI Act classification vignettes (13 archetypes incl. Annex III 5(b)/5(c)/4 and fraud carve-out)",
                  "PASS" if hits == len(uc) else "FAIL", f"{hits}/{len(uc)} correct", "13/13"))

    ok_bounds = bool(((grid["inherent"] >= 1) & (grid["inherent"] <= 25) & (grid["residual"] <= grid["inherent"] + 1e-12)).all())
    out.append(_r("O4", "Residual <= inherent and inherent within [1, 25] for all use-case x category cells",
                  "PASS" if ok_bounds else "FAIL", f"{len(grid)} cells"))

    rng = np.random.default_rng(7)
    ctrl_names = list(tax["controls"])
    viol_c = viol_a = 0
    for _ in range(500):
        a = dict(zip(rk.ATTRS, rng.random(len(rk.ATTRS))))
        c1 = dict(zip(ctrl_names, rng.random(len(ctrl_names))))
        c2 = {k: min(1.0, v + rng.random() * 0.3) for k, v in c1.items()}
        s1, s2 = rk.score_use_case(a, c1, tax), rk.score_use_case(a, c2, tax)
        viol_c += int((s2["residual"] > s1["residual"] + 1e-12).sum())
        k = rng.choice(rk.ATTRS)
        a2 = dict(a); a2[k] = min(1.0, a[k] + 0.2)
        viol_a += int((rk.score_use_case(a2, c1, tax)["inherent"] < s1["inherent"] - 1e-12).sum())
    out.append(_r("O4", "Monotonicity (500 random profiles): more controls never raise residual; riskier attributes never lower inherent",
                  "PASS" if viol_c == 0 and viol_a == 0 else "FAIL", f"violations: controls {viol_c}, attributes {viol_a}"))

    w = inputs["subsectors"].set_index("code")["employment"]
    share = rk.high_risk_share(grid, inputs["use_case_mix"], w)
    out.append(_r("O4", "Benchmark: employment-weighted share of AI use classified high-risk vs CSSF/BCL self-assessment (5%)",
                  "PASS" if 0.02 <= share <= 0.12 else "REVIEW", f"{share:.1%}", "2%-12% (5% +/- survey uncertainty incl. 29% unclassified)"))

    out.append(_r("O4", "Expert review of taxonomy, weights and control coverage (validation workshop)", "PENDING",
                  "review form and Fleiss-kappa scorer ready (docs/workshop)", "kappa >= 0.40 and all critical comments resolved",
                  "Requires the expert-user workshop; results to be entered in docs/workshop/feedback_log.csv"))
    return out
