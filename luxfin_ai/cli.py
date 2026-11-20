"""Command-line interface: `luxfin run`, `luxfin assess`, `luxfin kappa`."""
from __future__ import annotations

import argparse
import json
import sys

import pandas as pd
import yaml


def main(argv=None):
    p = argparse.ArgumentParser(prog="luxfin", description="LuxFin-AI Observatory toolkit")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run the integrated pipeline")
    r.add_argument("--config", default="config/default.yaml")
    r.add_argument("--out", default="outputs")
    r.add_argument("--draws", type=int, default=None)
    r.add_argument("--no-figures", action="store_true")
    a = sub.add_parser("assess", help="score one AI use case (YAML with attributes, controls, annex_iii ...)")
    a.add_argument("file")
    k = sub.add_parser("kappa", help="Fleiss kappa from an expert-rating CSV (items x categories counts)")
    k.add_argument("file")
    args = p.parse_args(argv)

    if args.cmd == "run":
        from .pipeline import run
        res = run(args.config, args.out, figures=not args.no_figures, n_draws=args.draws)
        v = res["val"]
        print(v[["id", "objective", "status", "check"]].to_string(index=False))
        print(json.dumps(res["manifest"]["validation_summary"]))
        return 1 if (v["status"] == "FAIL").any() else 0
    if args.cmd == "assess":
        from . import io, risk
        cfg = io.load_config()
        inp = io.load_inputs(cfg)
        with open(args.file, encoding="utf-8") as fh:
            uc = yaml.safe_load(fh)
        controls = {**risk.controls_dict(inp["controls"]), **uc.get("controls", {})}
        sc = risk.score_use_case(uc.get("attributes", {}), controls, inp["taxonomy"])
        sc["band"] = sc["residual"].map(risk.rating_band)
        print(sc.round(2).to_string(index=False))
        print(json.dumps(risk.classify_ai_act(uc), indent=1))
        return 0
    if args.cmd == "kappa":
        from .risk import fleiss_kappa
        m = pd.read_csv(args.file, index_col=0).to_numpy()
        print(f"Fleiss kappa = {fleiss_kappa(m):.3f}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
