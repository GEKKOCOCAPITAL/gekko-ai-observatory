# Validation workshop – expert review form (M3 / O4–O5)

**Project:** AI and the Transformation of Luxembourg's Financial Sector (LuxFin-AI Observatory)
**Applicant:** Gekko & Co. Capital SCSp · General Partner: RM MANAGEMENT SPF
**Toolkit version reviewed:** 0.9.0 · **Run hash (central):** see `outputs/run_manifest.json`

Reviewer role: ☐ Risk / compliance ☐ Fund industry ☐ Banking ☐ Insurance ☐ Supervisor / public body ☐ Academic ☐ Other
Participation is voluntary; no budget transfer (application §7.3.4). No personal data beyond name/role is recorded.

## Part A – Risk taxonomy and scoring grid (O4)
For each category R01–R11 (`data/risk_taxonomy.yaml`), rate the likelihood/impact weights and the regulatory mapping:
**Agree / Partly agree / Disagree**. Enter the counts per item in `expert_ratings_template.csv`
and compute agreement with `luxfin kappa docs/workshop/expert_ratings_template.csv`.

| Item | Question |
|---|---|
| A1 | Are the 11 categories complete for AI use in Luxembourg financial institutions? Anything missing? |
| A2 | Is each category correctly mapped to the AI Act, DORA and FSB vulnerabilities? |
| A3 | Do the attribute weights produce a sensible ranking of the 13 use-case archetypes? |
| A4 | Are the default control-coverage figures (CSSF/BCL 2025 survey + assumptions) realistic? |
| A5 | Is the indicative AI Act classification of the 13 archetypes correct (note Digital Omnibus dates)? |

## Part B – Impact scenarios (O3)
| Item | Question |
|---|---|
| B1 | Are the scenario ranges (adoption ceiling, depth of use, time savings, reinstatement) plausible for 2030? |
| B2 | Are the sub-sector exposure scores and task ratings credible for Luxembourg roles (e.g. transfer agent, depositary officer)? |
| B3 | Are the results communicated with enough uncertainty and caveats? |

## Part C – Prototype usability (O5)
| Item | Question |
|---|---|
| C1 | Could you run the toolkit / use the dashboard without assistance? (1–5) |
| C2 | Which outputs would you use in practice? Which are missing? |

**Acceptance criteria (M3):** Fleiss' κ ≥ 0.40 on Part A; every comment logged in `feedback_log.csv`
with a decision; all comments rated *critical* resolved or explicitly deferred with justification.
