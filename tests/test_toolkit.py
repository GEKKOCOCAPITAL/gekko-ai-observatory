"""Unit and integration tests for the LuxFin-AI Observatory prototype (O3-O5)."""
import json

import numpy as np
import pandas as pd
import pytest

from luxfin_ai import adoption as ad
from luxfin_ai import exposure as ex
from luxfin_ai import io
from luxfin_ai import risk as rk
from luxfin_ai import scenarios as sc
from luxfin_ai.pipeline import EXPECTED_OUTPUTS, run


@pytest.fixture(scope="module")
def cfg():
    c = io.load_config()
    c["run"]["n_draws"] = 2000
    return c


@pytest.fixture(scope="module")
def inputs(cfg):
    return io.load_inputs(cfg)


@pytest.fixture(scope="module")
def expo(inputs):
    return ex.exposure_index(inputs["tasks"])


# ---------------------------------------------------------------- exposure (O1 interface)
def test_task_database_valid(inputs):
    assert ex.validate_tasks(inputs["tasks"]) == []


def test_exposure_bounds_and_identity(expo):
    assert expo["exposure"].between(0, 1).all()
    np.testing.assert_allclose(expo["exposure"], expo["e1_share"] + 0.5 * expo["e2_share"])


def test_validate_tasks_detects_errors(inputs):
    bad = inputs["tasks"].copy()
    bad.loc[0, "rating"] = 0.7
    bad.loc[1, "time_share"] += 0.2
    assert len(ex.validate_tasks(bad)) == 2


# ---------------------------------------------------------------- adoption (O2 interface)
def test_calibration_two_points():
    obs = [{"date": 2022.0, "share": 0.30}, {"date": 2024.5, "share": 0.43}]
    r = ad.calibrate_speed(obs, 0.9)
    assert ad.adoption_path(0.30, 0.9, r, 2024.5, 2022.0) == pytest.approx(0.43, abs=1e-9)


def test_adoption_path_bounded_and_monotone():
    t = np.linspace(2024, 2040, 50)
    a = ad.adoption_path(0.3, 0.9, 0.25, t)
    assert np.all(np.diff(a) > 0) and a.max() < 0.9 and a.min() > 0


def test_adoption_ceiling_below_baseline_holds_constant():
    a = ad.adoption_path(0.63, 0.55, 0.3, np.array([2025, 2030]))
    np.testing.assert_allclose(a, 0.63)


def test_apply_signals_overrides_only_with_enough_docs(inputs):
    sig = pd.DataFrame({"subsector": ["BANK", "IFM"], "year": [2026, 2026],
                        "adoption_share": [0.55, 0.40], "n_docs": [120, 5]})
    out = ad.apply_signals(inputs["subsectors"], sig)
    assert out.set_index("code").loc["BANK", "adoption_2024"] == 0.55
    assert out.set_index("code").loc["BANK", "adoption_status"] == "nlp_signal_2026"
    assert out.set_index("code").loc["IFM", "adoption_2024"] == 0.24


# ---------------------------------------------------------------- scenarios (O3)
def test_core_equations_zero_and_identity():
    z = sc.core_equations(0.5, 0.0, 0.3, 0.5, 0.5, 0.7, 0.2)
    assert all(abs(v) < 1e-12 for v in z.values())
    r = sc.core_equations(0.5, 0.4, 0.3, 0.5, 0.5, 0.7, 0.2)
    assert (1 + r["dVA"]) / (1 + r["dL"]) - 1 == pytest.approx(r["dLP"])


def test_more_reinstatement_more_jobs():
    lo = sc.core_equations(0.5, 0.4, 0.3, 0.5, 0.5, 0.7, 0.0)["dL"]
    hi = sc.core_equations(0.5, 0.4, 0.3, 0.5, 0.5, 0.7, 0.4)["dL"]
    assert hi > lo


def test_simulation_shapes_and_reproducibility(cfg, inputs, expo):
    a = sc.simulate(cfg, inputs["subsectors"], expo, "central")
    b = sc.simulate(cfg, inputs["subsectors"], expo, "central")
    n, S, Y = 2000, len(inputs["subsectors"]), cfg["run"]["horizon"] - cfg["run"]["base_year"] + 1
    assert a["res"]["dL"].shape == (n, S, Y)
    np.testing.assert_array_equal(a["res"]["dL"], b["res"]["dL"])
    assert np.all(a["res"]["P"] >= 0) and np.all(a["res"]["P"] <= 1)


def test_scenario_ordering(cfg, inputs, expo):
    med = {}
    for s in cfg["scenarios"]:
        sim = sc.simulate(cfg, inputs["subsectors"], expo, s)
        _, tot = sc.summarise(sim)
        med[s] = tot.query("metric == 'dLP' and year == 2030")["p50"].iloc[0]
    assert med["cautious"] < med["central"] < med["accelerated"]


def test_summary_quantiles_ordered(cfg, inputs, expo):
    sim = sc.simulate(cfg, inputs["subsectors"], expo, "central")
    subs, tot = sc.summarise(sim)
    q = pd.concat([subs, tot])
    assert ((q["p05"] <= q["p50"]) & (q["p50"] <= q["p95"])).all()


# ---------------------------------------------------------------- risk (O4)
def test_ai_act_vignettes(inputs):
    uc = inputs["use_cases"]
    got = uc.apply(lambda r: rk.classify_ai_act(r.to_dict())["class"], axis=1)
    assert (got == uc["expected_class"]).all()


def test_prohibited_flag():
    assert rk.classify_ai_act({"prohibited_practice": "social scoring"})["class"] == "prohibited"


def test_scores_bounded_and_controls_reduce(inputs):
    tax = inputs["taxonomy"]
    attrs = dict.fromkeys(rk.ATTRS, 1.0)
    none = rk.score_use_case(attrs, {}, tax)
    full = rk.score_use_case(attrs, dict.fromkeys(tax["controls"], 1.0), tax)
    assert none["inherent"].max() <= 25 + 1e-9 and none["inherent"].min() >= 1
    assert (full["residual"] <= none["residual"]).all()
    assert (full["mitigation"] <= tax["max_mitigation"] + 1e-12).all()


def test_rating_bands():
    assert [rk.rating_band(x) for x in (2, 6, 12, 20)] == ["Low", "Medium", "High", "Critical"]


def test_fleiss_kappa_known_values():
    perfect = np.array([[3, 0], [0, 3], [3, 0]])
    assert rk.fleiss_kappa(perfect) == pytest.approx(1.0)
    # Fleiss (1971) style check: uniform random-like agreement gives kappa near or below 0
    split = np.array([[2, 1], [1, 2], [2, 1], [1, 2]])
    assert rk.fleiss_kappa(split) < 0.1


# ---------------------------------------------------------------- integration (O5)
def test_end_to_end_pipeline(tmp_path):
    res = run(out_dir=tmp_path, figures=False, n_draws=1500)
    for f in EXPECTED_OUTPUTS:
        assert (tmp_path / f).exists(), f
    val = pd.read_csv(tmp_path / "validation_results.csv")
    assert not (val["status"] == "FAIL").any(), val[val["status"] == "FAIL"]
    dash = json.loads((tmp_path / "dashboard_data.json").read_text())
    assert {"scenario_total", "risk_subsector", "validation"} <= set(dash)
    man = json.loads((tmp_path / "run_manifest.json").read_text())
    assert man["inputs"] and man["results_hash_central"] == res["manifest"]["results_hash_central"]
