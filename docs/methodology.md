# Methodology (v0.9.1)

## 1. Scope
Eight sub-sectors of CSSF/CAA-supervised entities, 57,229 employees (CSSF, mid-2026; insurance 2020; brokers 2025):
credit institutions, authorised investment fund managers, investment firms, specialised PFS, support PFS,
payment/e-money institutions, insurance undertakings, insurance brokers. Legal, audit and consulting services
(≈28% of the LFF financial-sector employment definition) and SOPARFI holdings are outside the v0.9 scope.

## 2. Exposure (O1 interface)
Per sub-sector, 4–10 core tasks with shares of working time and an Eloundou et al. (2024) rating:
E1 = 1 (direct LLM exposure), E2 = 0.5 (LLM plus tools), E0 = 0. Index β = Σ time_share × rating.
Rating uncertainty: multiplicative N(1, 0.10) per draw and sub-sector, clipped to [0.5, 1.5].

## 3. Adoption (O2 interface)
Baseline A₀ = share of entities with AI use cases in production or development (CSSF/BCL survey Jun–Aug 2024):
banks 38%, IFMs 24%, investment firms 15%, PI/EMI 63%. Non-surveyed sub-sectors use documented proxies with
extra uncertainty. Diffusion is logistic, A(t) = K / (1 + ((K − A₀)/A₀)·e^(−r(t − 2024.55))). The speed
r = 0.232/yr is calibrated on the two survey waves for banks/PI/EMI (30% in 2021/22 → 43% in 2024, K = 0.90).
Depth of use D (share of exposed tasks actually performed with AI inside adopting entities) rises linearly from
0.10 (2025) to a scenario value in 2030. WP3 NLP adoption signals override the survey baseline when supplied.

## 4. Impact scenarios (O3)
Effective penetration P = A·D; time saved h = β·P·g. Unit-labour-cost saving is passed to prices
(dp = −π·s_L·h); output responds with elasticity η (dQ = (1+dp)^(−η) − 1); a share ρ of saved hours is
reinstated in new tasks (Acemoglu–Restrepo / IMF complementarity). Then:
dL = (1+dQ)(1−h) + ρh − 1, dVA = dQ + ρh, dLP = (1+dVA)/(1+dL) − 1, all relative to a no-AI counterfactual.
Three scenarios set triangular distributions for K, r multiplier, D₂₀₃₀, g and ρ (see `config/default.yaml`);
g ranges from 14% (Brynjolfsson et al. 2025) to 40% (Noy & Zhang 2023). 10,000 draws per scenario; sector
totals are aggregated draw-by-draw so that ranges keep cross-sector correlation. Sensitivity: Spearman rank
correlation of each input with the 2030 sector outcome.

## 5. Risk taxonomy and scoring (O4)
11 categories (model, data/privacy, third-party/concentration, cyber, market correlation, governance, explainability,
fairness/consumer protection, regulatory classification, operational resilience, AI-enabled fraud), each mapped to
AI Act articles (as amended by the Digital Omnibus on AI, in force 27 Jul 2026), DORA articles, FSB (2024)
vulnerabilities and sectoral rules. Use cases are described by eight attributes in [0,1]; likelihood and impact are
linear in the attributes (weights sum to 1, scores 1–5); inherent = L×I (1–25); control coverage reduces it,
capped at 70% mitigation. Default control coverage uses the CSSF/BCL 2025 survey where available.
Sub-sector severity = use-case-mix-weighted residual; risk exposure = severity × scenario adoption share.
AI Act classification is rule-based (Annex III 5(b), 5(c), 4 etc., fraud-detection carve-out, Art. 50) and indicative only.

## 6. Integration and reproducibility (O5)
`luxfin run` executes O1→O4 in one pass, writes all outputs, a run manifest with SHA-256 of every input and a
results hash, and 24 automated validation checks. Fixed seeds make runs bit-identical. The Streamlit dashboard
re-runs scenarios live with user-set assumptions and includes a use-case risk assessor.

## 7. Known limitations
Provisional task ratings; proxy adoption for four sub-sectors; dated insurance employment; GVA for six sub-sectors
allocated by employment (LFF method); single demand elasticity for all sub-sectors; no general-equilibrium or
cross-border-worker effects; risk weights pending expert review. All are flagged in data files and the report.
