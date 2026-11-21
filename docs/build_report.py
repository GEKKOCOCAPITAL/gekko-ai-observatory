"""Build the M3 technical results and validation report (PDF) from pipeline outputs.

Usage: python docs/build_report.py  (after `luxfin run` and `pytest --junitxml=outputs/test_results.xml`)
"""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image as RLImage, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DST = ROOT / "docs" / "GEKKO-AI_M3_Results_and_Validation_Report.pdf"

GOLD = colors.HexColor("#9c8660")
INK = colors.HexColor("#252424")
GREY = colors.HexColor("#5a5955")
LINE = colors.HexColor("#d9d6cf")
TINT = colors.HexColor("#f5f2ec")

# ---------------------------------------------------------------- data
subs = pd.read_csv(OUT / "scenario_subsector.csv")
tot = pd.read_csv(OUT / "scenario_total.csv")
val = pd.read_csv(OUT / "validation_results.csv").fillna("")
sens = pd.read_csv(OUT / "sensitivity_central.csv")
risk = pd.read_csv(OUT / "risk_subsector.csv")
grid = pd.read_csv(OUT / "risk_use_case_grid.csv")
cls = pd.read_csv(OUT / "ai_act_classification.csv").fillna("")
expo = pd.read_csv(OUT / "exposure_index.csv")
occ = pd.read_csv(OUT / "exposure_by_occupation.csv")
man = json.loads((OUT / "run_manifest.json").read_text())
ss = pd.read_csv(ROOT / "data/subsectors.csv")
src = pd.read_csv(ROOT / "data/sources.csv")
tax = yaml.safe_load((ROOT / "data/risk_taxonomy.yaml").read_text())
cfg = yaml.safe_load((ROOT / "config/default.yaml").read_text())
names = dict(zip(ss["code"], ss["name"]))
short = {k: v.split(" (")[0] for k, v in names.items()}
tests = ET.parse(OUT / "test_results.xml").getroot()
ts = tests if tests.tag == "testsuite" else tests[0]
n_tests, n_fail = int(ts.get("tests")), int(ts.get("failures")) + int(ts.get("errors"))

H = cfg["run"]["horizon"]
SC = {"cautious": "S1 Cautious", "central": "S2 Central", "accelerated": "S3 Accelerated"}


def T(metric, scen, q="p50", year=H, df=tot, sub="TOTAL"):
    d = df[(df.metric == metric) & (df.scenario == scen) & (df.year == year) & (df.subsector == sub)]
    return float(d[q].iloc[0])


def pct(x, d=1):
    return f"{x*100:+.{d}f}%"


def num(x):
    return f"{x:+,.0f}"


emp_total = int(ss["employment"].sum())
w_exp = float((expo.set_index("subsector")["exposure"] * ss.set_index("code")["employment"]).sum() / emp_total)

# ---------------------------------------------------------------- styles
st = getSampleStyleSheet()
base = ParagraphStyle("b", parent=st["Normal"], fontName="Helvetica", fontSize=9.6, leading=13.4, textColor=INK, spaceAfter=5)
small = ParagraphStyle("s", parent=base, fontSize=8, leading=10.2, textColor=GREY)
cell = ParagraphStyle("c", parent=base, fontSize=7.8, leading=9.6, spaceAfter=0)
cellb = ParagraphStyle("cb", parent=cell, fontName="Helvetica-Bold")
h1 = ParagraphStyle("h1", parent=base, keepWithNext=1, fontName="Times-Bold", fontSize=17, leading=21, textColor=INK, spaceBefore=4, spaceAfter=8)
h2 = ParagraphStyle("h2", parent=base, keepWithNext=1, fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=GOLD, spaceBefore=8, spaceAfter=4)
bullet = ParagraphStyle("bl", parent=base, leftIndent=12, bulletIndent=2)
cap = ParagraphStyle("cap", parent=small, spaceBefore=2, spaceAfter=10)


def P(t, s=base):
    return Paragraph(t, s)


def bullets(items):
    return [Paragraph(i, bullet, bulletText="•") for i in items]


def table(rows, widths, header=True, zebra=True, align_right_from=None):
    data = [[c if not isinstance(c, str) else Paragraph(c, cellb if (header and r == 0) else cell) for c in row]
            for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    sty = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, 0), 0.8, GOLD),
           ("LINEBELOW", (0, -1), (-1, -1), 0.4, LINE), ("TOPPADDING", (0, 0), (-1, -1), 3),
           ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if zebra:
        for r in range(1, len(rows)):
            if r % 2 == 0:
                sty.append(("BACKGROUND", (0, r), (-1, r), TINT))
    t.setStyle(TableStyle(sty))
    return t


def fig(name, width=165 * mm):
    p = OUT / "figures" / name
    w, h = Image.open(p).size
    return RLImage(str(p), width=width, height=width * h / w)


# ---------------------------------------------------------------- logo (pure-white background for print)
logo_src = Image.open(ROOT / "docs/assets/gekko_logo.jpg").convert("RGB")
a = np.array(logo_src).astype(int)
ys, xs = np.where(a.sum(axis=2) < 600)
pad = 30
crop = logo_src.crop((xs.min() - pad, ys.min() - pad, xs.max() + pad, ys.max() + pad))
arr = np.array(crop)
arr[arr.min(axis=2) > 228] = 255
logo_path = ROOT / "docs/assets/gekko_logo_cover.png"
Image.fromarray(arr).save(logo_path)


def cover(c, doc):
    W, Hh = A4
    c.saveState()
    c.setFillColor(colors.white)
    c.rect(0, 0, W, Hh, stroke=0, fill=1)
    lw = 120 * mm
    iw, ih = Image.open(logo_path).size
    lh = lw * ih / iw
    c.drawImage(str(logo_path), (W - lw) / 2, Hh - 70 * mm - lh, lw, lh)
    c.setStrokeColor(GOLD); c.setLineWidth(0.6)
    y = Hh - 128 * mm
    c.line(40 * mm, y, W - 40 * mm, y)
    c.setFillColor(INK); c.setFont("Times-Bold", 19)
    for i, line in enumerate(["Artificial Intelligence and the Transformation", "of Luxembourg's Financial Sector:",
                              "Impacts, Opportunities and Risks"]):
        c.drawCentredString(W / 2, y - 14 * mm - i * 8.5 * mm, line)
    c.setFillColor(GOLD); c.setFont("Helvetica", 10.5)
    c.drawCentredString(W / 2, y - 48 * mm, "PROTOTYPE TOOLKIT v" + man["toolkit_version"])
    c.setFillColor(INK); c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(W / 2, y - 62 * mm, "Milestone M3  Integrated prototype: results and validation report")
    c.setFont("Helvetica", 9.5); c.setFillColor(GREY)
    c.drawCentredString(W / 2, y - 69 * mm, "Objectives O3-O5  ·  Deliverables D4.1, D4.2, D5.1")
    c.line(40 * mm, 52 * mm, W - 40 * mm, 52 * mm)
    c.setFont("Helvetica", 8.3)
    lines = ["Gekko & Co. Capital SCSp  ·  RCS B311757  ·  54, Rue du Parc, L-3542 Dudelange, Luxembourg",
             "RDI-REDDEX experimental development  ·  Project period 12/10/2026 - 30/11/2026",
             "Version 0.9.1 - 20 November 2026"]
    for i, l in enumerate(lines):
        c.drawCentredString(W / 2, 44 * mm - i * 5 * mm, l)
    c.restoreState()


def later(c, doc):
    W, Hh = A4
    c.saveState()
    c.setStrokeColor(LINE); c.setLineWidth(0.4)
    c.line(18 * mm, Hh - 14 * mm, W - 18 * mm, Hh - 14 * mm)
    c.setFont("Times-Bold", 8.5); c.setFillColor(INK)
    c.drawString(18 * mm, Hh - 12 * mm, "GEKKO & CO")
    c.setFont("Helvetica", 7); c.setFillColor(GOLD)
    from reportlab.pdfbase.pdfmetrics import stringWidth
    c.drawString(18 * mm + stringWidth("GEKKO & CO", "Times-Bold", 8.5) + 5, Hh - 12 * mm, "CAPITAL SCSp")
    c.setFillColor(GREY)
    c.drawRightString(W - 18 * mm, Hh - 12 * mm, "GEKKO-AI Observatory · M3 results and validation report")
    c.line(18 * mm, 13 * mm, W - 18 * mm, 13 * mm)
    c.drawString(18 * mm, 9 * mm, "Scenario results are relative to a no-AI counterfactual and are not forecasts.")
    c.drawRightString(W - 18 * mm, 9 * mm, f"{doc.page}")
    c.restoreState()


# ---------------------------------------------------------------- content
S = []
S.append(PageBreak())

# 1 Executive summary
S.append(P("1. Executive summary", h1))
cnt = val["status"].value_counts()
S.append(P(
    f"The LuxFin-AI Observatory prototype integrates the AI-exposure, adoption, impact-scenario (O3) and risk-scoring (O4) "
    f"modules into one reproducible toolkit with a dashboard (O5). A single command runs the full chain for "
    f"{len(ss)} sub-sectors covering {emp_total:,} employees of CSSF- and CAA-supervised entities, produces "
    f"{3*cfg['run']['n_draws']:,} Monte-Carlo draws in about {man['runtime_s']:.0f} seconds, and executes "
    f"{len(val)} automated validation checks: <b>{cnt.get('PASS',0)} pass, {cnt.get('FAIL',0)} fail</b>, "
    f"{cnt.get('PENDING',0)} pending (external expert workshop) and {cnt.get('INFO',0)} informational (including the project leader\'s internal review). "
    f"The unit and integration test suite returns {n_tests-n_fail}/{n_tests} passed."))
S.append(P("Headline results for 2030 (median and 90% range, relative to a no-AI counterfactual):", base))
rows = [["", "Labour productivity", "Employment", "Jobs", "Real GVA", "GVA (EUR m)"]]
for s, lab in SC.items():
    rows.append([lab] + [f"{pct(T(m, s))}<br/><font size=6.5 color='#5a5955'>{pct(T(m, s, 'p05'))} to {pct(T(m, s, 'p95'))}</font>" for m in ["dLP", "dL"]]
                + [f"{num(T('jobs', s))}<br/><font size=6.5 color='#5a5955'>{num(T('jobs', s, 'p05'))} to {num(T('jobs', s, 'p95'))}</font>"]
                + [f"{pct(T('dVA', s))}<br/><font size=6.5 color='#5a5955'>{pct(T('dVA', s, 'p05'))} to {pct(T('dVA', s, 'p95'))}</font>"]
                + [f"{num(T('gva_eur_m', s))}<br/><font size=6.5 color='#5a5955'>{num(T('gva_eur_m', s, 'p05'))} to {num(T('gva_eur_m', s, 'p95'))}</font>"])
S.append(table(rows, [32 * mm, 27 * mm, 27 * mm, 28 * mm, 25 * mm, 28 * mm]))
S.append(Spacer(1, 6))
top_risk = risk.groupby("category")["residual"].mean().sort_values(ascending=False)
S += bullets([
    f"<b>Exposure.</b> The employment-weighted AI-exposure index is {w_exp:.2f} (0 = none, 1 = all working time exposed). "
    f"Specialised PFS (fund administration, transfer agency, domiciliation) are the most exposed sub-sector "
    f"({expo.set_index('subsector').loc['SPFS','exposure']:.2f}); clerical support roles are the most exposed occupational group, consistent with ILO (2025).",
    f"<b>Productivity before jobs.</b> In the central scenario, AI raises sector labour productivity by {pct(T('dLP','central'))} by 2030 "
    f"(about {((1+T('dLP','central'))**(1/5)-1)*100:.2f}% a year) and real GVA by EUR {T('gva_eur_m','central'):,.0f}m. "
    f"Employment is {abs(T('jobs','central')):,.0f} jobs ({pct(T('dL','central'))}) below the no-AI path - a slower-growth effect "
    f"to be absorbed over five years rather than a contraction of today's workforce.",
    f"<b>Where it lands.</b> Payment/e-money institutions and specialised PFS show the largest relative effects; credit institutions "
    f"the largest absolute one ({abs(T('jobs','central',df=subs,sub='BANK')):,.0f} jobs, central median), because of their size.",
    f"<b>What matters most.</b> Time savings on AI-performed tasks, depth of use and reinstatement of saved hours into new tasks "
    f"explain most of the uncertainty - these, not adoption speed, are the levers for firms, social partners and training policy.",
    f"<b>Risks.</b> The highest residual risks across sub-sectors are {top_risk.index[0].lower()}, {top_risk.index[1].lower()} and "
    f"{top_risk.index[2].lower()}, driven by reliance on commercial GenAI models (75% of GenAI use cases use only commercial models, CSSF/BCL 2025). "
    f"High-risk AI Act use (credit scoring, life/health insurance pricing, HR) is about 7% of modelled AI use, close to the 5% self-classified in the CSSF/BCL survey.",
])

# 2 Scope
S.append(P("2. Milestone M3 scope and status", h1))
S.append(P("M3 requires the toolkit, dashboard, scenario and risk modules to be integrated and validated (O3-O5), with the public report and "
           "open repository published; the minimal result is a working prototype with documented results. Status at 20 November 2026:"))
rows = [["Item", "Deliverable", "Status", "Location"],
        ["Impact scenario module (O3)", "D4.1", "Built and validated (12 automated checks)", "luxfin_ai/scenarios.py"],
        ["AI risk taxonomy and scoring grid (O4)", "D4.2", "Built; automated checks pass; expert review pending", "luxfin_ai/risk.py, data/risk_taxonomy.yaml"],
        ["Integrated toolkit and dashboard (O5)", "D5.1", "Built; end-to-end run, determinism and 18 tests pass", "luxfin_ai/pipeline.py, app/"],
        ["Internal review by the project leader", "M3", "Done 20/11/2026: agreed on items A1-B3, usability 5/5, no changes requested", "docs/workshop/internal_review_2026-11-20.md"],
        ["Validation workshop with external expert users", "M3", "Pending - materials ready", "docs/workshop/"],
        ["Public report and open repository", "D5.2, D5.3", "Repository on GitHub (private); public release pending", "github.com/GEKKOCOCAPITAL/gekko-ai-observatory"],
        ["Exposure index (O1) and NLP pipeline (O2)", "D2.1, D3.2", "Interfaces built; v0.1 provisional inputs used until WP2/WP3 outputs are plugged in", "data/tasks.csv, config adoption_signals"]]
S.append(table(rows, [48 * mm, 18 * mm, 58 * mm, 50 * mm]))

# 3 Data
S.append(P("3. Data and calibration", h1))
S.append(P("Each input carries a provenance status so that users see what is observed and what is assumed. "
           "<b>official</b> = published statistic; <b>proxy</b> = survey value of a comparable entity type; "
           "<b>dated</b> = official but older than 2024; <b>assumption</b> = documented value to confirm at the workshop."))
rows = [["Sub-sector", "Employees", "Ref. date", "Status", "GVA 2024 (EUR m)", "AI adoption 2024", "Status", "Exposure"]]
e = expo.set_index("subsector")["exposure"]
for _, r in ss.iterrows():
    rows.append([short[r.code], f"{r.employment:,}", r.employment_ref_date[:7], r.employment_status, f"{r.gva_eur_m:,}",
                 f"{r.adoption_2024:.0%}", r.adoption_status, f"{e[r.code]:.2f}"])
rows.append(["<b>Total / weighted</b>", f"<b>{emp_total:,}</b>", "", "", f"<b>{ss.gva_eur_m.sum():,}</b>", "", "", f"<b>{w_exp:.2f}</b>"])
S.append(table(rows, [42 * mm, 18 * mm, 16 * mm, 16 * mm, 22 * mm, 20 * mm, 18 * mm, 16 * mm]))
S.append(P("Employment: CSSF Financial centre releases (Jun-Sep 2026), Insurance Europe (2020), CAA via Paperjam (2025). GVA: LFF State of the "
           "Financial Sector 2025 (EUR 17.3bn; banking about 43%, fund management about 22%); other sub-sectors at EUR 236,400 per employee, the LFF method. "
           "Adoption: CSSF/BCL thematic review 2025 (share of entities with AI use cases in production or development).", cap))
S.append(P(f"<b>Diffusion calibration.</b> Two CSSF/BCL survey waves show AI use among banks, payment and e-money institutions rising from 30% "
           f"(Oct 2021-Jan 2022) to 43% (Jun-Aug 2024). With a central ceiling of 90%, this gives a logistic speed of "
           f"{json.loads((OUT/'dashboard_data.json').read_text())['calibration']['r']:.3f} per year, used for all sub-sectors and varied by scenario. "
           f"<b>Task exposure</b> follows the Eloundou et al. (2024) rubric (E1 = 1, E2 = 0.5, E0 = 0) on 4-10 core tasks per sub-sector; the v0.1 ratings "
           f"are LLM-assisted and will be replaced by the human-validated WP2 database."))
rows = [["ISCO-08 major group", "Exposure", "FTE equivalent"]] + [
    [r.isco_major_group, f"{r.exposure:.2f}", f"{r.fte_equivalent:,.0f}"] for r in occ.itertuples()]
S.append(KeepTogether([P("Exposure by occupational group (employment-weighted)", h2), table(rows, [70 * mm, 25 * mm, 30 * mm])]))

# 4 O3
S.append(PageBreak())
S.append(P("4. Impact scenarios to 2030 (O3)", h1))
S.append(P("For each sub-sector, the share of working time saved is <i>h = exposure x adoption x depth of use x time saving</i>. "
           "Part of the cost saving passes into prices and raises demand; a share of saved hours is reinstated in new tasks. "
           "Employment, real GVA and labour productivity follow from accounting identities (see docs/methodology.md). "
           "Three scenarios define ranges for the uncertain parameters; 10,000 draws each give the documented uncertainty."))
rows = [["Parameter (triangular min / mode / max)", "S1 Cautious", "S2 Central", "S3 Accelerated", "Basis"]]
basis = {"ceiling": "Assumption; S2 matches calibration", "speed_multiplier": "x calibrated speed (0.232/yr)",
         "depth_2030": "From 10% in 2025 (CSSF/BCL: 54% of use cases in production)", "time_saving": "Brynjolfsson et al. 2025 (14%); Noy & Zhang 2023 (40%)",
         "reinstatement": "IMF 2024 complementarity; Acemoglu 2024"}
lab = {"ceiling": "Adoption ceiling", "speed_multiplier": "Diffusion speed multiplier", "depth_2030": "Depth of use 2030",
       "time_saving": "Time saving on AI-performed tasks", "reinstatement": "Reinstatement of saved hours"}
for k in basis:
    rows.append([lab[k]] + [" / ".join(f"{v:g}" for v in cfg["scenarios"][s][k]) for s in SC] + [basis[k]])
for k, l in [("labour_share_va", "Labour share of GVA"), ("price_pass_through", "Price pass-through"), ("demand_elasticity", "Demand elasticity")]:
    rows.append([l, " / ".join(f"{v:g}" for v in cfg["common"][k]), "same", "same", "Assumption (all scenarios)"])
S.append(table(rows, [46 * mm, 24 * mm, 24 * mm, 24 * mm, 56 * mm]))
S.append(Spacer(1, 6))
S.append(fig("fan_jobs.png", 150 * mm))
S.append(P("Figure 1 - Sector employment relative to the no-AI path; lines are medians, bands the 5th-95th percentiles.", cap))
S.append(fig("fan_gva.png", 150 * mm))
S.append(P("Figure 2 - Sector real GVA relative to the no-AI path.", cap))
S.append(fig("subsector_employment.png", 150 * mm))
S.append(P("Figure 3 - Employment effect by sub-sector in 2030.", cap))
rows = [["Sub-sector (S2 Central, 2030)", "Productivity", "Employment", "Jobs", "GVA (EUR m)"]]
for c in ss["code"]:
    rows.append([short[c]] + [f"{pct(T(m,'central',df=subs,sub=c))} <font size=6.5 color='#5a5955'>[{pct(T(m,'central','p05',df=subs,sub=c))}; {pct(T(m,'central','p95',df=subs,sub=c))}]</font>" for m in ["dLP", "dL"]]
                + [f"{num(T('jobs','central',df=subs,sub=c))}", f"{num(T('gva_eur_m','central',df=subs,sub=c))}"])
S.append(KeepTogether([table(rows, [52 * mm, 38 * mm, 38 * mm, 20 * mm, 24 * mm]), P("Median with 90% range in brackets.", cap)]))
S.append(KeepTogether([fig("tornado_employment.png", 140 * mm),
                       P("Figure 4 - Sensitivity: Spearman rank correlation between each uncertain input and the 2030 sector employment effect (S2).", cap)]))
S.append(P("<b>Reading the results.</b> Effects are gradual and modest at sector level by 2030 because adoption depth is still low today "
           "(92% of reported use cases are internal, CSSF/BCL 2025). The accelerated scenario shows what agentic GenAI could imply if depth of use "
           "and time savings reach the upper end of field evidence. Because Luxembourg's financial workforce is largely cross-border, effects on "
           "residents and cross-border workers will differ; this split is outside v0.9."))

# 5 O4
S.append(PageBreak())
S.append(P("5. AI risk taxonomy and scoring grid (O4)", h1))
S.append(P("Eleven risk categories are mapped to the AI Act (Regulation (EU) 2024/1689 as amended by the Digital Omnibus on AI, in force since "
           "27 July 2026, with Annex III high-risk obligations applying from 2 December 2027), to DORA (Regulation (EU) 2022/2554) and to the "
           "vulnerabilities identified by the FSB (November 2024). Scores are rule-based and transparent: likelihood and impact (1-5) are weighted "
           "sums of eight use-case attributes; control coverage reduces inherent risk (cap 70%). Default control coverage uses CSSF/BCL survey figures "
           "(e.g. 90% human-in-the-loop, 54% good explainability, 56% performance monitoring)."))
rows = [["ID", "Category", "AI Act", "DORA", "FSB vulnerability"]]
for c in tax["categories"]:
    rows.append([c["id"], c["name"], "; ".join(c["ai_act"]) or "-", "; ".join(c["dora"]) or "-",
                 "; ".join(tax["fsb_vulnerabilities"][v] for v in c["fsb"])])
S.append(table(rows, [10 * mm, 34 * mm, 52 * mm, 40 * mm, 38 * mm]))
S.append(Spacer(1, 6))
S.append(KeepTogether([fig("risk_heatmap.png", 165 * mm),
                       P("Figure 5 - Residual risk (1-25) by sub-sector and category, weighted by each sub-sector's AI use-case mix.", cap)]))
rows = [["Use-case archetype", "Indicative AI Act class", "Basis", "Max residual (category)"]]
g = grid.loc[grid.groupby("use_case_id")["residual"].idxmax()].set_index("use_case_id")
for r in cls.itertuples():
    rows.append([r.use_case, r._3 if False else r[3], r.basis, f"{g.loc[r.use_case_id,'residual']:.1f} ({g.loc[r.use_case_id,'category_id']})"])
S.append(KeepTogether([P("AI Act classification of the 13 archetypes", h2), table(rows, [66 * mm, 26 * mm, 52 * mm, 30 * mm]),
                       P("Indicative classification for analysis purposes; not legal advice. Fraud detection is carved out of Annex III 5(b).", cap)]))
S.append(P("<b>Findings.</b> Third-party dependency and concentration, and cyber/adversarial risk, are the highest residual risks in every "
           "sub-sector; the support PFS that host AI services for others concentrate this exposure. Fairness and consumer-protection risk is "
           "material only where credit scoring, insurance pricing or HR screening are used, i.e. banks, payment institutions and insurers. "
           "Market-correlation risk is low today but concentrated in investment firms and fund managers. Red-teaming (assumed 20% coverage) and "
           "vendor exit planning (40%) are the weakest controls and the most effective places to reduce residual risk."))

# 6 O5 validation
S.append(PageBreak())
S.append(P("6. Integration and validation (O5)", h1))
S.append(P(f"<b>Integration.</b> <font face='Courier'>luxfin run</font> loads all inputs, validates them, computes exposure, simulates the three "
           f"scenarios, scores risks, links risk exposure to the scenario adoption paths, writes 12 output files, 7 figures and a dashboard payload, "
           f"and records a run manifest with SHA-256 hashes of all inputs and a results hash (central: <font face='Courier'>{man['results_hash_central']}</font>). "
           f"The Streamlit dashboard re-runs scenarios live with user-adjusted assumptions, shows the risk grid and includes a single use-case assessor; "
           f"all six dashboard views were smoke-tested headlessly without errors. Environment: Python {man['python']}, numpy {man['numpy']}, pandas {man['pandas']}; "
           f"a Dockerfile and CI workflow reproduce the run."))
rows = [["ID", "Obj.", "Check", "Result", "Threshold", "Status"]]
for r in val.itertuples():
    color = {"PASS": "#1a7f37", "FAIL": "#b42318", "PENDING": "#9c6b00", "INFO": "#5a5955", "REVIEW": "#9c6b00"}[r.status]
    rows.append([r.id, r.objective, r.check, str(r.value), str(r.threshold), f"<font color='{color}'><b>{r.status}</b></font>"])
S.append(table(rows, [10 * mm, 10 * mm, 66 * mm, 44 * mm, 28 * mm, 16 * mm]))
S.append(P(f"Automated test suite (pytest): {n_tests-n_fail}/{n_tests} passed - exposure identities, diffusion calibration, scenario identities and ordering, "
           f"reproducibility, AI Act vignettes, score bounds, control monotonicity, Fleiss' kappa, and a full end-to-end pipeline run.", cap))

# 7 Limitations
S.append(P("7. Limitations and open items before M3 sign-off", h1))
S += bullets([
    "<b>Internal review (done).</b> On 20 November 2026 the project leader, Rafael Mendes, reviewed the toolkit with the "
    "expert review form: he agreed on all rated items A1-B3 (taxonomy, scoring, AI Act classification, scenarios, exposure, caveats), "
    "rated usability 5/5, said he would use all four main outputs and requested no changes (feedback log FB-001 to FB-008). As an internal, single-reviewer review it "
    "does not replace the external workshop below.",
    "<b>Expert validation workshop (pending).</b> O4 requires validation by expert review and M3 a workshop with expert users and a feedback log. "
    "The review form, rating template, Fleiss' kappa scorer (<font face='Courier'>luxfin kappa</font>) and feedback log are ready in docs/workshop; "
    "acceptance criteria: kappa of at least 0.40 and every critical comment resolved or justified.",
    "<b>Provisional inputs.</b> Task ratings are v0.1 (LLM-assisted, not yet human-validated); four sub-sectors use proxy adoption rates; "
    "insurance employment is a 2020 figure; GVA for six sub-sectors is allocated by employment. Replacing these with WP2/WP3 outputs and CAA/STATEC "
    "data requires no code change.",
    "<b>Model scope.</b> Partial-equilibrium, sector-level model with a single demand elasticity; no resident vs cross-border split, wage effects "
    "or second-round effects on the rest of the economy (LFF estimates one additional job elsewhere per financial-sector job).",
    "<b>Out of scope in v0.9.</b> Legal, audit and consulting services and SOPARFI holdings (included in the LFF 73,272 total).",
    "<b>Publication.</b> The repository is on GitHub (GEKKOCOCAPITAL/gekko-ai-observatory, release v0.9.1) under an Apache-2.0 "
    "licence and is kept private until the external workshop; the public report (D5.2) and public release (D5.3) follow then.",
])

# 8 Sources
S.append(P("8. Sources", h1))
for r in src.itertuples():
    S.append(P(f"[{r.id}] {r.source}. <font color='#5a5955'>{r.url}</font>", small))

doc = SimpleDocTemplate(str(DST), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=20 * mm, bottomMargin=18 * mm,
                        title="LuxFin-AI Observatory - M3 results and validation report", author="Gekko & Co. Capital SCSp",
                        subject="AI and the Transformation of Luxembourg's Financial Sector")
doc.build(S, onFirstPage=cover, onLaterPages=later)
print(DST)
