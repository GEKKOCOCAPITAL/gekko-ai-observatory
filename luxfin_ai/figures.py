"""Static figures for the report (matplotlib). Palette: validated reference categorical slots 1-3."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SCEN_COLORS = {"cautious": "#2a78d6", "central": "#eb6834", "accelerated": "#1baf7a"}
SCEN_LABEL = {"cautious": "S1 Cautious", "central": "S2 Central", "accelerated": "S3 Accelerated"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SEQ = ["#f1f6fd", "#cfe1f7", "#9cc2ee", "#5f9be2", "#2a78d6", "#1d5aa6", "#123e74"]

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150, "savefig.bbox": "tight",
})


def fan_total(total: pd.DataFrame, metric: str, ylabel: str, title: str, path: Path, scale=1.0, pct=False):
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    for s, col in SCEN_COLORS.items():
        d = total[(total["scenario"] == s) & (total["metric"] == metric)].sort_values("year")
        f = 100 if pct else scale
        ax.fill_between(d["year"], d["p05"] * f, d["p95"] * f, color=col, alpha=0.15, linewidth=0)
        ax.plot(d["year"], d["p50"] * f, color=col, linewidth=2, label=SCEN_LABEL[s])
        ax.annotate(SCEN_LABEL[s], (d["year"].iloc[-1], d["p50"].iloc[-1] * f), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=8, color=INK2)
    ax.axhline(0, color=INK2, linewidth=0.8)
    ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left", fontsize=10, color=INK)
    ax.legend(frameon=False, loc="lower left", fontsize=8)
    ax.set_xlim(total["year"].min(), total["year"].max() + 1.2)
    fig.savefig(path)
    plt.close(fig)


def bars_subsector(subs: pd.DataFrame, names: dict, metric: str, year: int, xlabel: str, title: str, path: Path):
    d = subs[(subs["metric"] == metric) & (subs["year"] == year)]
    order = d[d["scenario"] == "central"].sort_values("p50")["subsector"].tolist()
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    y = np.arange(len(order))
    off = {"cautious": -0.25, "central": 0.0, "accelerated": 0.25}
    for s, col in SCEN_COLORS.items():
        x = d[d["scenario"] == s].set_index("subsector").loc[order]
        ax.errorbar(x["p50"] * 100, y + off[s], xerr=[(x["p50"] - x["p05"]) * 100, (x["p95"] - x["p50"]) * 100],
                    fmt="o", color=col, ms=4, elinewidth=1.4, capsize=0, label=SCEN_LABEL[s])
    ax.set_yticks(y, [names[c].split(" (")[0] for c in order], fontsize=8)
    ax.axvline(0, color=INK2, linewidth=0.8)
    ax.set_xlabel(xlabel)
    ax.set_title(title, loc="left", fontsize=10, color=INK)
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3)
    fig.savefig(path)
    plt.close(fig)


def heatmap(sub_risk: pd.DataFrame, names: dict, path: Path):
    p = sub_risk.pivot(index="subsector", columns="category_id", values="residual")
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("seq", SEQ)
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    im = ax.imshow(p.values, cmap=cmap, aspect="auto", vmin=0, vmax=max(8, float(np.nanmax(p.values))))
    ax.set_xticks(range(p.shape[1]), p.columns, fontsize=8)
    ax.set_yticks(range(p.shape[0]), [names[c] for c in p.index], fontsize=8)
    ax.grid(False)
    for i in range(p.shape[0]):
        for j in range(p.shape[1]):
            v = p.values[i, j]
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=7,
                    color="white" if v > 0.6 * im.get_clim()[1] else INK)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("Residual risk score (1-25)", color=INK2)
    ax.set_title("Residual AI risk by sub-sector and risk category (use-case-mix weighted)", loc="left", fontsize=10, color=INK)
    fig.savefig(path)
    plt.close(fig)


def tornado(sens: pd.DataFrame, title: str, path: Path):
    d = sens.iloc[::-1]
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.barh(d["parameter"], d["spearman_rho"], color=np.where(d["spearman_rho"] > 0, "#2a78d6", "#eb6834"), height=0.6)
    ax.axvline(0, color=INK2, linewidth=0.8)
    ax.set_xlim(-1, 1)
    ax.set_xlabel("Spearman rank correlation with outcome")
    ax.set_title(title, loc="left", fontsize=10, color=INK)
    ax.tick_params(axis="y", labelsize=8)
    ax.grid(axis="y", visible=False)
    ax.set_axisbelow(True)
    fig.savefig(path)
    plt.close(fig)
