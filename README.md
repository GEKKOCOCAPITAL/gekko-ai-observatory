# LuxFin-AI Observatory – prototype toolkit (v0.9.1)

[![ci](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml) ![licence](https://img.shields.io/badge/licence-Apache--2.0-blue) ![version](https://img.shields.io/badge/version-0.9.1-9c8660)

Open, reproducible toolkit that links **AI exposure**, **adoption**, **impact scenarios** and **regulatory risk scoring**
for Luxembourg's financial sector. Developed by **Gekko & Co. Capital SCSp** (managed by RM MANAGEMENT SPF) under the
R&D project *"Artificial Intelligence and the Transformation of Luxembourg's Financial Sector: Impacts, Opportunities
and Risks"* — milestone **M3: toolkit, dashboard, scenario and risk modules integrated and validated (O3–O5)**.

| Objective | Module | What it does |
|---|---|---|
| O1 interface | `luxfin_ai/exposure.py` | Task-level exposure index (E0/E1/E2 rubric, Eloundou et al. 2024) by sub-sector and ISCO group |
| O2 interface | `luxfin_ai/adoption.py` | Adoption baseline (CSSF/BCL surveys), logistic diffusion calibration, ingestion of WP3 NLP adoption signals |
| **O3** | `luxfin_ai/scenarios.py` | Monte-Carlo scenarios to 2030: productivity, employment and real GVA by sub-sector, with p05/p50/p95 ranges and sensitivity analysis |
| **O4** | `luxfin_ai/risk.py`, `data/risk_taxonomy.yaml` | 11-category AI risk taxonomy mapped to the AI Act (as amended by the Digital Omnibus), DORA and FSB vulnerabilities; transparent scoring grid; AI Act classification helper; Fleiss-kappa for expert review |
| **O5** | `luxfin_ai/pipeline.py`, `app/` | One-command integrated run with validation checks, run manifest (input hashes, results hash), figures, dashboard payload and Streamlit dashboard |

## Quick start
```bash
pip install -e ".[app,dev]"
luxfin run                 # full pipeline: outputs/ + validation (≈5 s, 3 × 10,000 draws)
pytest -q                  # 18 unit/integration tests
streamlit run app/streamlit_app.py
luxfin assess examples/use_case_chatbot.yaml   # score a single AI use case
```
Or `docker build -t luxfin . && docker run -p 8501:8501 luxfin`.

## Outputs (`outputs/`)
`exposure_index.csv`, `exposure_by_occupation.csv`, `scenario_subsector.csv`, `scenario_total.csv`,
`sensitivity_central.csv`, `risk_use_case_grid.csv`, `ai_act_classification.csv`, `risk_subsector.csv`,
`risk_exposure.csv`, `validation_results.csv`, `dashboard_data.json`, `run_manifest.json`, `figures/*.png`.

## Data status – read before using results
Every input row carries a status: **official** (CSSF, LFF, BCL/CSSF survey), **proxy** (survey value of a similar
entity type), **dated** (older official figure) or **assumption** (documented, to be confirmed at the validation
workshop). Task ratings in `data/tasks.csv` are provisional (v0.1, LLM-assisted) and are replaced by the
human-validated WP2 database when available. Scenario results are **relative to a no-AI counterfactual**, not forecasts.
Sources: `data/sources.csv`. Method: `docs/methodology.md`. Validation: `outputs/validation_results.csv` and the
written report.

## Plugging in WP2/WP3 results
* Replace `data/tasks.csv` with the validated task database (same columns).
* Set `data.adoption_signals` in `config/default.yaml` to the WP3 adoption dataset
  (`subsector, year, adoption_share, n_docs`); sub-sectors with ≥30 documents switch from survey to NLP adoption.

## Licence
Code: Apache-2.0. Data compiled from public sources; see each source's terms. Datasets produced by the toolkit: CC BY 4.0
where source rights permit. "LuxFin-AI Observatory" name retained by the applicant.

## Written report
`docs/LuxFin-AI_M3_Results_and_Validation_Report.pdf` — M3 results and validation report (rebuild with
`make test && python docs/build_report.py` after `luxfin run`). Validation workshop materials: `docs/workshop/`.
