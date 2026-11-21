"""GEKKO-AI Observatory - interactive dashboard (Streamlit).

Run:  streamlit run app/streamlit_app.py
"""
import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from luxfin_ai import exposure as ex
from luxfin_ai import io
from luxfin_ai import risk as rk
from luxfin_ai import scenarios as sc

COL = {"cautious": "#2a78d6", "central": "#eb6834", "accelerated": "#1baf7a"}
st.set_page_config(page_title="GEKKO-AI Observatory", layout="wide")


@st.cache_data
def load():
    cfg = io.load_config()
    inp = io.load_inputs(cfg)
    return cfg, inp, ex.exposure_index(inp["tasks"])


@st.cache_data
def simulate(cfg_items: str, scenario: str, n: int):
    cfg = io.load_config()
    import json
    cfg.update(json.loads(cfg_items))
    _, inp, expo = load()
    sim = sc.simulate(cfg, inp["subsectors"], expo, scenario, n=n)
    subs, tot = sc.summarise(sim)
    return subs, tot, sc.sensitivity(sim, "dL")


cfg, inp, expo = load()
names = dict(zip(inp["subsectors"]["code"], inp["subsectors"]["name"]))
logo = ROOT / "docs/assets/gekko_logo.jpg"
with st.sidebar:
    if logo.exists():
        st.image(str(logo), width=180)
    st.markdown("**GEKKO-AI Observatory** - prototype v0.9")
    page = st.radio("View", ["Overview", "Exposure", "Scenarios (O3)", "Risk (O4)", "Use-case assessor", "Validation (O5)"])
    st.caption("Results are model scenarios relative to a no-AI counterfactual, not forecasts.")

if page == "Overview":
    st.title("AI and Luxembourg's financial sector - impacts, opportunities and risks")
    ss = inp["subsectors"].merge(expo, left_on="code", right_on="subsector")
    c1, c2, c3 = st.columns(3)
    c1.metric("Employment covered", f"{ss['employment'].sum():,}")
    c2.metric("Employment-weighted AI exposure", f"{ex.employment_weighted_exposure(expo, inp['subsectors']):.2f}")
    c3.metric("Sub-sectors", len(ss))
    st.dataframe(ss[["code", "name", "employment", "employment_status", "exposure", "adoption_2024", "adoption_status"]],
                 hide_index=True, width="stretch")

elif page == "Exposure":
    st.header("Task-level AI exposure (E0/E1/E2 rubric)")
    d = expo.assign(name=expo["subsector"].map(names)).sort_values("exposure")
    st.plotly_chart(px.bar(d, x="exposure", y="name", orientation="h", range_x=[0, 1],
                           labels={"exposure": "Exposure index (beta = E1 + 0.5 E2)", "name": ""},
                           color_discrete_sequence=["#2a78d6"]), width="stretch")
    sub = st.selectbox("Task detail", list(names), format_func=names.get)
    st.dataframe(inp["tasks"].query("subsector == @sub")[["task", "isco08", "time_share", "rating_label", "rationale"]],
                 hide_index=True, width="stretch")
    st.caption("Ratings v0.1 are LLM-assisted and pending human validation (WP2).")

elif page == "Scenarios (O3)":
    st.header("Impact scenarios to 2030 (Monte-Carlo)")
    scen = st.selectbox("Scenario", list(cfg["scenarios"]), index=1, format_func=lambda s: cfg["scenarios"][s]["label"])
    p = copy.deepcopy(cfg["scenarios"][scen])
    with st.expander("Adjust scenario assumptions (mode values; min/max scale proportionally)"):
        for k, lab in [("time_saving", "Time saving on AI-performed tasks"), ("depth_2030", "Depth of use in 2030"),
                       ("reinstatement", "Reinstatement (new tasks)"), ("ceiling", "Adoption ceiling")]:
            lo, mo, hi = p[k]
            new = st.slider(lab, 0.0, 1.0, float(mo), 0.01, key=k)
            f = new / mo if mo else 1
            p[k] = [min(lo * f, new), new, max(min(hi * f, 1.0), new)]
    n = st.select_slider("Draws", [1000, 5000, 10000], value=5000)
    import json
    subs, tot, sens = simulate(json.dumps({"scenarios": {scen: p}}), scen, n)
    metric = st.radio("Metric", ["jobs", "gva_eur_m", "dLP", "dL", "dVA"], horizontal=True,
                      format_func={"jobs": "Jobs", "gva_eur_m": "GVA EUR m", "dLP": "Productivity %",
                                   "dL": "Employment %", "dVA": "GVA %"}.get)
    d = tot[tot["metric"] == metric]
    fig = go.Figure([
        go.Scatter(x=list(d["year"]) + list(d["year"][::-1]), y=list(d["p95"]) + list(d["p05"][::-1]),
                   fill="toself", fillcolor="rgba(235,104,52,0.15)", line=dict(width=0), name="90% band"),
        go.Scatter(x=d["year"], y=d["p50"], line=dict(color=COL[scen], width=2), name="Median")])
    fig.update_layout(height=360, margin=dict(t=20))
    st.plotly_chart(fig, width="stretch")
    y = subs[(subs["metric"] == metric) & (subs["year"] == cfg["run"]["horizon"])].copy()
    y["name"] = y["subsector"].map(names)
    st.dataframe(y[["name", "p05", "p50", "p95"]], hide_index=True, width="stretch")
    st.subheader("Sensitivity of 2030 employment effect")
    st.plotly_chart(px.bar(sens, x="spearman_rho", y="parameter", orientation="h", range_x=[-1, 1]), width="stretch")

elif page == "Risk (O4)":
    st.header("AI risk taxonomy and scoring grid")
    grid = rk.use_case_grid(inp["use_cases"], rk.controls_dict(inp["controls"]), inp["taxonomy"])
    sr = rk.subsector_risk(grid, inp["use_case_mix"])
    hm = sr.pivot(index="subsector", columns="category_id", values="residual")
    st.plotly_chart(px.imshow(hm, text_auto=".1f", color_continuous_scale=["#f1f6fd", "#2a78d6", "#123e74"],
                              labels=dict(color="Residual (1-25)")), width="stretch")
    cats = pd.DataFrame([{"id": c["id"], "category": c["name"], "AI Act": "; ".join(c["ai_act"]),
                          "DORA": "; ".join(c["dora"]), "FSB": ", ".join(c["fsb"])} for c in inp["taxonomy"]["categories"]])
    st.dataframe(cats, hide_index=True, width="stretch")

elif page == "Use-case assessor":
    st.header("Assess an AI use case")
    attrs = {a: st.slider(desc, 0.0, 1.0, 0.5, 0.1, key=a) for a, desc in inp["taxonomy"]["attributes"].items()}
    base = rk.controls_dict(inp["controls"])
    with st.expander("Control coverage (defaults: sector baseline from CSSF/BCL 2025)"):
        ctrl = {c: st.slider(desc, 0.0, 1.0, float(base.get(c, 0)), 0.05, key="c_" + c)
                for c, desc in inp["taxonomy"]["controls"].items()}
    annex = st.selectbox("Annex III area", ["", "5b", "5c", "4", "1", "3", "5a"],
                         format_func=lambda x: {"": "none", "5b": "5(b) creditworthiness", "5c": "5(c) life/health insurance pricing",
                                                "4": "4 employment/HR", "1": "1 biometrics", "3": "3 education", "5a": "5(a) public benefits"}[x])
    fraud = st.checkbox("Used for financial-fraud detection")
    chat = st.checkbox("Interacts directly with natural persons")
    pub = st.checkbox("Generates content published to the public")
    s = rk.score_use_case(attrs, ctrl, inp["taxonomy"])
    s["band"] = s["residual"].map(rk.rating_band)
    st.dataframe(s.round(2), hide_index=True, width="stretch")
    cl = rk.classify_ai_act({"annex_iii": annex, "fraud_detection": int(fraud), "interacts_with_persons": int(chat),
                             "generates_public_content": int(pub)})
    st.info(f"Indicative AI Act class: **{cl['class']}** - {cl['basis']}. {cl['note']}. Not legal advice.")

else:
    st.header("Validation results")
    p = ROOT / "outputs/validation_results.csv"
    if p.exists():
        st.dataframe(pd.read_csv(p), hide_index=True, width="stretch")
    else:
        st.warning("Run `luxfin run` first.")
