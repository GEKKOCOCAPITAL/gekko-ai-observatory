"""Loading of configuration and input data."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]


def resolve(path: str | Path, root: Path = ROOT) -> Path:
    p = Path(path)
    return p if p.is_absolute() else root / p


def load_config(path: str | Path = "config/default.yaml", root: Path = ROOT) -> dict:
    with open(resolve(path, root), encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    cfg["_root"] = str(root)
    return cfg


def load_inputs(cfg: dict) -> dict:
    root = Path(cfg["_root"])
    d = cfg["data"]
    inputs = {
        "subsectors": pd.read_csv(resolve(d["subsectors"], root)),
        "tasks": pd.read_csv(resolve(d["tasks"], root)),
        "use_cases": pd.read_csv(resolve(d["use_cases"], root), keep_default_na=False),
        "use_case_mix": pd.read_csv(resolve(d["use_case_mix"], root)),
        "controls": pd.read_csv(resolve("data/controls_baseline.csv", root)),
    }
    with open(resolve(d["risk_taxonomy"], root), encoding="utf-8") as fh:
        inputs["taxonomy"] = yaml.safe_load(fh)
    if d.get("adoption_signals"):
        inputs["adoption_signals"] = pd.read_csv(resolve(d["adoption_signals"], root))
    return inputs


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
