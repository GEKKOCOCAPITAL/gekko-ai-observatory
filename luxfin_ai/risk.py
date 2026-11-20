"""AI risk taxonomy, scoring grid and AI Act classification helper (O4).

Scoring is rule-based and fully transparent:
  L_c = 1 + 4 * sum_k wL[c,k] * attr_k        likelihood (1-5)
  I_c = 1 + 4 * sum_k wI[c,k] * attr_k        impact (1-5)
  inherent_c = L_c * I_c                       (1-25)
  mitigation_c = min(max_mitigation, sum_j e[c,j] * coverage_j)
  residual_c = inherent_c * (1 - mitigation_c)
Weights e and w live in data/risk_taxonomy.yaml so that expert reviewers can amend them
without touching code.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ATTRS = ["genai", "client_facing", "autonomy", "decisions_on_persons", "vendor_dependence",
         "data_sensitivity", "materiality", "market_activity"]

AI_ACT_DATES = {
    "prohibited": "Art. 5 prohibitions apply since 2 Feb 2025",
    "high": "Annex III high-risk obligations apply from 2 Dec 2027 (Digital Omnibus on AI)",
    "limited": "Art. 50 transparency obligations (chatbot disclosure from 2 Aug 2026; marking of AI-generated content from 2 Dec 2026)",
    "minimal": "No specific AI Act obligations beyond Art. 4 AI literacy (since 2 Feb 2025)",
}


def _lin(weights: dict, attrs: dict) -> float:
    return 1.0 + 4.0 * sum(w * float(attrs.get(k, 0.0)) for k, w in weights.items())


def score_use_case(attrs: dict, controls: dict, taxonomy: dict) -> pd.DataFrame:
    cap = taxonomy["max_mitigation"]
    rows = []
    for c in taxonomy["categories"]:
        L = _lin(c["likelihood"], attrs)
        I = _lin(c["impact"], attrs)
        mit = min(cap, sum(e * float(controls.get(k, 0.0)) for k, e in c["controls"].items()))
        inh = L * I
        rows.append({"category_id": c["id"], "category": c["name"], "likelihood": L, "impact": I,
                     "inherent": inh, "mitigation": mit, "residual": inh * (1 - mit)})
    return pd.DataFrame(rows)


def rating_band(score: float) -> str:
    if score >= 15:
        return "Critical"
    if score >= 10:
        return "High"
    if score >= 5:
        return "Medium"
    return "Low"


def classify_ai_act(uc: dict) -> dict:
    """Indicative AI Act risk class for a use case. Not legal advice; requires legal review."""
    if str(uc.get("prohibited_practice", "")).strip() not in ("", "0", "False", "false"):
        return {"class": "prohibited", "basis": "Art. 5", "note": AI_ACT_DATES["prohibited"]}
    annex = str(uc.get("annex_iii", "")).strip()
    fraud = int(float(uc.get("fraud_detection", 0) or 0)) == 1
    if annex in {"5b", "5c", "4", "1", "3", "5a"} and not (annex == "5b" and fraud):
        return {"class": "high", "basis": f"Art. 6(2) + Annex III point {annex}", "note": AI_ACT_DATES["high"]}
    if annex == "5b" and fraud:
        basis = "Annex III 5(b) carve-out for financial-fraud detection"
    else:
        basis = ""
    if int(float(uc.get("interacts_with_persons", 0) or 0)) or int(float(uc.get("generates_public_content", 0) or 0)):
        return {"class": "limited", "basis": "Art. 50 transparency", "note": AI_ACT_DATES["limited"]}
    return {"class": "minimal", "basis": basis or "Not listed in Annex III", "note": AI_ACT_DATES["minimal"]}


def controls_dict(controls_df: pd.DataFrame) -> dict:
    return dict(zip(controls_df["control"], controls_df["coverage"].astype(float)))


def use_case_grid(use_cases: pd.DataFrame, controls: dict, taxonomy: dict) -> pd.DataFrame:
    frames = []
    for _, uc in use_cases.iterrows():
        sc = score_use_case(uc[ATTRS].astype(float).to_dict(), controls, taxonomy)
        cl = classify_ai_act(uc.to_dict())
        sc.insert(0, "use_case_id", uc["id"])
        sc.insert(1, "use_case", uc["name"])
        sc["ai_act_class"] = cl["class"]
        frames.append(sc)
    return pd.concat(frames, ignore_index=True)


def subsector_risk(grid: pd.DataFrame, mix: pd.DataFrame) -> pd.DataFrame:
    """Use-case-mix-weighted residual score per sub-sector and category."""
    m = mix.melt(id_vars="subsector", var_name="use_case_id", value_name="weight")
    j = m.merge(grid, on="use_case_id")
    j["w_res"] = j["weight"] * j["residual"]
    j["w_inh"] = j["weight"] * j["inherent"]
    out = j.groupby(["subsector", "category_id", "category"], as_index=False)[["w_res", "w_inh"]].sum()
    return out.rename(columns={"w_res": "residual", "w_inh": "inherent"})


def high_risk_share(grid: pd.DataFrame, mix: pd.DataFrame, weights: pd.Series | None = None) -> float:
    """Share of AI use (mix-weighted, optionally employment-weighted) classified high-risk."""
    cls = grid.drop_duplicates("use_case_id").set_index("use_case_id")["ai_act_class"]
    hr = [c for c in cls.index if cls[c] == "high"]
    m = mix.set_index("subsector")
    per_sub = m[hr].sum(axis=1)
    if weights is None:
        return float(per_sub.mean())
    w = weights.reindex(per_sub.index)
    return float((per_sub * w).sum() / w.sum())


def risk_exposure(sub_risk: pd.DataFrame, adoption: pd.DataFrame) -> pd.DataFrame:
    """Risk exposure index: residual severity x adoption share (scenario median).

    adoption columns: subsector, year, A (median adoption share).
    """
    j = sub_risk.merge(adoption, on="subsector")
    j["exposure_index"] = j["residual"] * j["A"]
    return j


def fleiss_kappa(ratings: np.ndarray) -> float:
    """Fleiss' kappa for an items x categories count matrix (each row sums to n raters)."""
    r = np.asarray(ratings, dtype=float)
    n = r.sum(axis=1)[0]
    if not np.allclose(r.sum(axis=1), n) or n < 2:
        raise ValueError("each item must be rated by the same number (>=2) of raters")
    p_j = r.sum(axis=0) / r.sum()
    P_i = (np.square(r).sum(axis=1) - n) / (n * (n - 1))
    P_bar, P_e = P_i.mean(), np.square(p_j).sum()
    return float((P_bar - P_e) / (1 - P_e)) if P_e < 1 else 1.0
