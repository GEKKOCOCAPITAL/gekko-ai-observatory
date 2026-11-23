"""GEKKO-AI Observatory - interactive dashboard (NiceGUI version).

Same six views as app/streamlit_app.py, built with NiceGUI.
Run locally:  python app/nicegui_app.py      (http://localhost:8080)
Port and host can be set with the PORT and HOST environment variables (Hugging Face Spaces uses 7860).
"""
import copy
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from nicegui import app, ui

from luxfin_ai import exposure as ex
from luxfin_ai import io
from luxfin_ai import risk as rk
from luxfin_ai import scenarios as sc

GOLD, INK = "#9c8660", "#252424"
COL = {"cautious": "#2a78d6", "central": "#eb6834", "accelerated": "#1baf7a"}
METRICS = {"jobs": "Jobs", "gva_eur_m": "GVA EUR m", "dLP": "Productivity %", "dL": "Employment %", "dVA": "GVA %"}

CFG = io.load_config()
INP = io.load_inputs(CFG)
EXPO = ex.exposure_index(INP["tasks"])
NAMES = dict(zip(INP["subsectors"]["code"], INP["subsectors"]["name"]))
GRID = rk.use_case_grid(INP["use_cases"], rk.controls_dict(INP["controls"]), INP["taxonomy"])
SUB_RISK = rk.subsector_risk(GRID, INP["use_case_mix"])
_SIM_CACHE: dict = {}

app.add_static_files("/assets", str(ROOT / "docs" / "assets"))


def table(df: pd.DataFrame, rows_per_page: int = 0, digits: int = 3):
    d = df.copy()
    for c in d.select_dtypes("number").columns:
        d[c] = d[c].round(digits)
    cols = [{"name": c, "label": c, "field": c, "sortable": True, "align": "left"} for c in d.columns]
    t = ui.table(columns=cols, rows=d.to_dict("records"), pagination=rows_per_page or None).classes("w-full")
    t.props("dense flat bordered")
    return t


def fig_layout(fig, height=360):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(color=INK))
    return fig


def run_scenario(scen: str, modes: dict, n: int):
    key = (scen, tuple(sorted(modes.items())), n)
    if key in _SIM_CACHE:
        return _SIM_CACHE[key]
    cfg = copy.deepcopy(CFG)
    p = cfg["scenarios"][scen]
    for k, new in modes.items():
        lo, mo, hi = p[k]
        f = new / mo if mo else 1
        p[k] = [min(lo * f, new), new, max(min(hi * f, 1.0), new)]
    sim = sc.simulate(cfg, INP["subsectors"], EXPO, scen, n=n)
    subs, tot = sc.summarise(sim)
    out = (subs, tot, sc.sensitivity(sim, "dL"))
    if len(_SIM_CACHE) > 32:
        _SIM_CACHE.clear()
    _SIM_CACHE[key] = out
    return out


# ------------------------------------------------------------------ views
def view_overview():
    ui.label("AI and Luxembourg's financial sector - impacts, opportunities and risks").classes("text-2xl font-bold")
    ss = INP["subsectors"].merge(EXPO, left_on="code", right_on="subsector")
    with ui.row().classes("gap-8"):
        for lab, val in [("Employment covered", f"{ss['employment'].sum():,}"),
                         ("Employment-weighted AI exposure", f"{ex.employment_weighted_exposure(EXPO, INP['subsectors']):.2f}"),
                         ("Sub-sectors", str(len(ss)))]:
            with ui.column().classes("gap-0"):
                ui.label(lab).classes("text-sm text-gray-600")
                ui.label(val).classes("text-3xl")
    table(ss[["code", "name", "employment", "employment_status", "exposure", "adoption_2024", "adoption_status"]])


def view_exposure():
    ui.label("Task-level AI exposure (E0/E1/E2 rubric)").classes("text-xl font-bold")
    d = EXPO.assign(name=EXPO["subsector"].map(NAMES)).sort_values("exposure")
    fig = px.bar(d, x="exposure", y="name", orientation="h", range_x=[0, 1],
                 labels={"exposure": "Exposure index (beta = E1 + 0.5 E2)", "name": ""}, color_discrete_sequence=["#2a78d6"])
    ui.plotly(fig_layout(fig)).classes("w-full")
    holder = ui.column().classes("w-full")

    def show(code):
        holder.clear()
        with holder:
            table(INP["tasks"].query("subsector == @code")[["task", "isco08", "time_share", "rating_label", "rationale"]])

    ui.select({k: v for k, v in NAMES.items()}, value="BANK", label="Task detail", on_change=lambda e: show(e.value)).classes("w-96")
    show("BANK")
    ui.label("Ratings v0.1 are LLM-assisted and pending human validation (WP2).").classes("text-sm text-gray-600")


def view_scenarios():
    ui.label("Impact scenarios to 2030 (Monte-Carlo)").classes("text-xl font-bold")
    state = {"scen": "central", "metric": "jobs", "n": 5000,
             "modes": {k: CFG["scenarios"]["central"][k][1] for k in ["time_saving", "depth_2030", "reinstatement", "ceiling"]}}
    out = ui.column().classes("w-full")
    sliders = {}

    def render():
        subs, tot, sens = run_scenario(state["scen"], state["modes"], state["n"])
        out.clear()
        with out:
            d = tot[tot["metric"] == state["metric"]]
            fig = go.Figure([
                go.Scatter(x=list(d["year"]) + list(d["year"][::-1]), y=list(d["p95"]) + list(d["p05"][::-1]),
                           fill="toself", fillcolor="rgba(235,104,52,0.15)", line=dict(width=0), name="90% band"),
                go.Scatter(x=d["year"], y=d["p50"], line=dict(color=COL[state["scen"]], width=2), name="Median")])
            ui.plotly(fig_layout(fig)).classes("w-full")
            y = subs[(subs["metric"] == state["metric"]) & (subs["year"] == CFG["run"]["horizon"])].copy()
            y["name"] = y["subsector"].map(NAMES)
            ui.label(f"By sub-sector, {CFG['run']['horizon']} (p05 / median / p95)").classes("font-bold")
            table(y[["name", "p05", "p50", "p95"]])
            ui.label("Sensitivity of 2030 employment effect").classes("font-bold mt-4")
            ui.plotly(fig_layout(px.bar(sens, x="spearman_rho", y="parameter", orientation="h", range_x=[-1, 1]), 320)).classes("w-full")

    def set_scen(s):
        state["scen"] = s
        state["modes"] = {k: CFG["scenarios"][s][k][1] for k in state["modes"]}
        for k, sl in sliders.items():
            sl.value = state["modes"][k]
        render()

    with ui.row().classes("items-end gap-6"):
        ui.select({s: CFG["scenarios"][s]["label"] for s in CFG["scenarios"]}, value="central", label="Scenario",
                  on_change=lambda e: set_scen(e.value)).classes("w-80")
        ui.select({1000: "1,000", 5000: "5,000", 10000: "10,000"}, value=5000, label="Draws",
                  on_change=lambda e: (state.update(n=e.value), render())).classes("w-32")
        ui.toggle(METRICS, value="jobs", on_change=lambda e: (state.update(metric=e.value), render()))
    with ui.expansion("Adjust scenario assumptions (mode values; min/max scale proportionally)").classes("w-full"):
        for k, lab in [("time_saving", "Time saving on AI-performed tasks"), ("depth_2030", "Depth of use in 2030"),
                       ("reinstatement", "Reinstatement (new tasks)"), ("ceiling", "Adoption ceiling")]:
            ui.label(lab).classes("text-sm")
            sliders[k] = ui.slider(min=0.01, max=1.0, step=0.01, value=state["modes"][k]).props("label-always")

            def changed(_e=None, key=k):
                state["modes"][key] = float(sliders[key].value)
                render()
            sliders[k].on("change", changed)
    render()


def view_risk():
    ui.label("AI risk taxonomy and scoring grid").classes("text-xl font-bold")
    hm = SUB_RISK.pivot(index="subsector", columns="category_id", values="residual")
    fig = px.imshow(hm, text_auto=".1f", color_continuous_scale=["#f1f6fd", "#2a78d6", "#123e74"], labels=dict(color="Residual (1-25)"))
    ui.plotly(fig_layout(fig, 420)).classes("w-full")
    cats = pd.DataFrame([{"id": c["id"], "category": c["name"], "AI Act": "; ".join(c["ai_act"]), "DORA": "; ".join(c["dora"]),
                          "FSB": ", ".join(c["fsb"])} for c in INP["taxonomy"]["categories"]])
    table(cats)


def view_assessor():
    ui.label("Assess an AI use case").classes("text-xl font-bold")
    attrs = {a: 0.5 for a in INP["taxonomy"]["attributes"]}
    base = rk.controls_dict(INP["controls"])
    ctrl = {c: float(base.get(c, 0)) for c in INP["taxonomy"]["controls"]}
    flags = {"annex_iii": "", "fraud_detection": 0, "interacts_with_persons": 0, "generates_public_content": 0}
    result = ui.column().classes("w-full")

    def render():
        s = rk.score_use_case(attrs, ctrl, INP["taxonomy"])
        s["band"] = s["residual"].map(rk.rating_band)
        cl = rk.classify_ai_act(flags)
        result.clear()
        with result:
            table(s, digits=2)
            ui.label(f"Indicative AI Act class: {cl['class']} - {cl['basis']}. {cl['note']}. Not legal advice.") \
                .classes("p-3 rounded bg-blue-50 w-full")

    with ui.grid(columns=2).classes("w-full gap-x-8"):
        for a, desc in INP["taxonomy"]["attributes"].items():
            with ui.column().classes("gap-0"):
                ui.label(desc).classes("text-sm")
                ui.slider(min=0, max=1, step=0.1, value=0.5, on_change=lambda e, k=a: (attrs.__setitem__(k, e.value), render()))
    with ui.expansion("Control coverage (defaults: sector baseline from CSSF/BCL 2025)").classes("w-full"):
        for c, desc in INP["taxonomy"]["controls"].items():
            ui.label(desc).classes("text-sm")
            ui.slider(min=0, max=1, step=0.05, value=ctrl[c], on_change=lambda e, k=c: (ctrl.__setitem__(k, e.value), render()))
    with ui.row().classes("items-center gap-6"):
        ui.select({"": "none", "5b": "5(b) creditworthiness", "5c": "5(c) life/health insurance pricing", "4": "4 employment/HR",
                   "1": "1 biometrics", "3": "3 education", "5a": "5(a) public benefits"}, value="", label="Annex III area",
                  on_change=lambda e: (flags.__setitem__("annex_iii", e.value), render())).classes("w-72")
        ui.checkbox("Used for financial-fraud detection", on_change=lambda e: (flags.__setitem__("fraud_detection", int(e.value)), render()))
        ui.checkbox("Interacts directly with natural persons", on_change=lambda e: (flags.__setitem__("interacts_with_persons", int(e.value)), render()))
        ui.checkbox("Generates content published to the public", on_change=lambda e: (flags.__setitem__("generates_public_content", int(e.value)), render()))
    render()


def view_validation():
    ui.label("Validation results").classes("text-xl font-bold")
    p = ROOT / "outputs" / "validation_results.csv"
    if p.exists():
        table(pd.read_csv(p).fillna(""))
    else:
        ui.label("Run `luxfin run` first.")


VIEWS = {"Overview": view_overview, "Exposure": view_exposure, "Scenarios (O3)": view_scenarios,
         "Risk (O4)": view_risk, "Use-case assessor": view_assessor, "Validation (O5)": view_validation}


@ui.page("/")
def index():
    ui.colors(primary=GOLD)
    ui.page_title("GEKKO-AI Observatory")
    content = ui.column().classes("w-full max-w-6xl mx-auto p-4")

    def show(name):
        content.clear()
        with content:
            VIEWS[name]()

    drawer = ui.left_drawer(value=True).classes("bg-gray-50")
    with drawer:
        ui.image("/assets/gekko_logo_crop.png").classes("w-44")
        ui.markdown("**GEKKO-AI Observatory** - prototype v0.9")
        ui.radio(list(VIEWS), value="Overview", on_change=lambda e: show(e.value))
        ui.label("Results are model scenarios relative to a no-AI counterfactual, not forecasts.").classes("text-xs text-gray-600")
    with ui.header().classes("bg-white text-black items-center"):
        ui.button(icon="menu", on_click=drawer.toggle).props("flat color=black")
        ui.label("GEKKO-AI Observatory").classes("text-lg font-bold")
    show("Overview")

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="GEKKO-AI Observatory", host=os.environ.get("HOST", "0.0.0.0"),
           port=int(os.environ.get("PORT", "8080")), reload=False, show=False, favicon="📊")
