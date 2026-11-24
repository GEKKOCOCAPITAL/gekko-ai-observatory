# Changelog

## 0.9.2 - 2026-11-24 (public release)
- Added the research report (November 2026, CC BY 4.0; ScienceOpen preprint DOI 10.14293/PR2199.004967.v1) in docs/research/.
- Added .zenodo.json metadata for archiving on Zenodo.
- NiceGUI dashboard deployed to Hugging Face Spaces.

## 0.9.1 - 2026-11-20
- Fix: the toolkit now finds its data and configuration when installed as a regular package (pip install . / Docker / CI).
- Repository renamed to gekko-ai-observatory.
- Internal review by the project leader recorded (docs/workshop/internal_review_2026-11-20.md, FB-001 to FB-008); report updated. External expert workshop still pending.

## 0.9.0 - 2026-11-20 (milestone M3, pre-workshop)
- O3 impact scenario module: three scenarios, 10,000 Monte-Carlo draws each, p05/p50/p95 ranges, sensitivity analysis.
- O4 risk taxonomy (11 categories) mapped to the AI Act (as amended by the Digital Omnibus on AI), DORA and FSB vulnerabilities;
  rule-based scoring grid; indicative AI Act classifier; Fleiss-kappa scorer for expert review.
- O5 integrated pipeline (`luxfin run`) with 24 automated validation checks, run manifest and input hashes;
  Streamlit dashboard; 18 tests; Docker and CI.
- Interfaces for WP2 task database and WP3 NLP adoption signals.
- Known open items: expert validation workshop; replacement of provisional task ratings and proxy adoption rates.
