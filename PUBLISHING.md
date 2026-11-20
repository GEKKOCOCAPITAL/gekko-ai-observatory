# Publishing this repository on GitHub

```bash
# from the repository folder (history already initialised)
gh repo create RMManagement/gekko-ai-observatory --public --source . --remote origin \
  --description "LuxFin-AI Observatory - AI exposure, impact scenarios and risk scoring for Luxembourg's financial sector"
git push -u origin main
git tag -a v0.9.0 -m "M3 integrated prototype (pre-workshop)" && git push origin v0.9.0
gh release create v0.9.0 docs/LuxFin-AI_M3_Results_and_Validation_Report.pdf --title "v0.9.0 - M3 integrated prototype" --notes-file CHANGELOG.md
```
Without the GitHub CLI: create an empty repository on github.com, then
`git remote add origin https://github.com/RMManagement/gekko-ai-observatory.git && git push -u origin main`.

Optional: connect the repository to Zenodo before creating the release to obtain a DOI for the dissemination record.
CI (`.github/workflows/ci.yml`) runs the tests and the pipeline on every push.
