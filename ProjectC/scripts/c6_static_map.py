"""C6: A3 landscape static map of a pilot neighbourhood: system type and QA issues.

Output: outputs/maps/<pilot>_drainage_qa_A3.pdf and .png (also docs/img/)
Usage:  python scripts/c6_static_map.py [pilot]   (default: Ottewell)
"""
import pathlib
import sys
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle, FancyArrow

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "clean" / "edmonton_drainage.gpkg"
QA = ROOT / "data" / "clean" / "edmonton_drainage_qa.gpkg"
OUTDIR = ROOT / "outputs" / "maps"
SYS = {"COMBINED": ("#7B5EA7", "Combined"), "STORM": ("#2C7FB8", "Storm"), "SANITARY": ("#D95F0E", "Sanitary"), "FOUNDATION DRAIN": ("#8C8C8C", "Foundation drain")}
SEV = {"High": ("#C0392B", "X", 70), "Medium": ("#E69F00", "D", 42), "Low": ("#52606D", "^", 22)}
INK, MUTED = "#1F2933", "#616E7C"
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK, "axes.labelcolor": INK})


def scalebar(ax, length_m=500, xy=(0.04, 0.04)):
    x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
    x = x0 + (x1 - x0) * xy[0]; y = y0 + (y1 - y0) * xy[1]
    for i in range(2):
        ax.add_patch(Rectangle((x + i * length_m / 2, y), length_m / 2, (y1 - y0) * 0.006, facecolor=INK if i == 0 else "white", edgecolor=INK, lw=0.6, zorder=20))
    for t, lab in [(0, "0"), (length_m / 2, f"{length_m // 2}"), (length_m, f"{length_m} m")]:
        ax.text(x + t, y + (y1 - y0) * 0.012, lab, ha="center", va="bottom", fontsize=7, zorder=20)


def north(ax, xy=(0.95, 0.9)):
    ax.annotate("N", xy=xy, xytext=(xy[0], xy[1] - 0.07), xycoords="axes fraction", ha="center", va="center", fontsize=10, fontweight="bold",
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.2), zorder=20)


def main(pilot="Ottewell"):
    area = gpd.read_file(SRC, layer="pilot_areas").query("pilot == @pilot")
    b = area.total_bounds
    nb = gpd.read_file(SRC, layer="neighbourhoods_2019")
    hood = nb[nb.neighbourhood_name.str.lower() == pilot.lower()]
    p = gpd.read_file(SRC, layer="pipes", bbox=tuple(b))
    mh = gpd.read_file(SRC, layer="manholes", bbox=tuple(b))
    cb = gpd.read_file(SRC, layer="catch_basins", bbox=tuple(b))
    cont = gpd.read_file(SRC, layer="contours_pilot").query("pilot == @pilot")
    qa = gpd.read_file(QA, layer="qa_issues", bbox=tuple(b))
    swm = gpd.read_file(SRC, layer="swm_facilities", bbox=tuple(b))
    summ = gpd.read_file(QA, layer="neighbourhood_summary")

    fig = plt.figure(figsize=(16.54, 11.69))  # A3 landscape
    fig.patch.set_facecolor("white")
    mh_frac = 0.84
    w_frac = mh_frac * 11.69 * (b[2] - b[0]) / (b[3] - b[1]) / 16.54
    ax = fig.add_axes([0.025, 0.035, w_frac, mh_frac])
    # relief: 1 m contours, every 5 m slightly darker
    c1 = cont[(cont.elevation * 2) % 2 == 0]
    c1[c1.elevation % 5 != 0].plot(ax=ax, color="#E3E6EA", lw=0.35, zorder=1)
    c1[c1.elevation % 5 == 0].plot(ax=ax, color="#CDD2D8", lw=0.6, zorder=1)
    swm.plot(ax=ax, color="#CFE3F3", edgecolor="#9CC3E4", lw=0.5, zorder=2)
    nb.boundary.plot(ax=ax, color="#B8BEC6", lw=0.6, linestyle="--", zorder=2)
    hood.boundary.plot(ax=ax, color=INK, lw=1.4, zorder=3)
    for s in ["STORM", "SANITARY", "FOUNDATION DRAIN", "COMBINED"]:
        d = p[p.system == s]
        if len(d):
            d.plot(ax=ax, color=SYS[s][0], lw=1.15 if s == "COMBINED" else 0.95, zorder=4)
    cb.plot(ax=ax, color="#9AA5B1", markersize=1.2, zorder=5)
    mh.plot(ax=ax, color="white", edgecolor=INK, markersize=5, lw=0.35, zorder=6)
    for sev in ["Low", "Medium", "High"]:
        d = qa[qa.severity == sev]
        if len(d):
            c, m, sz = SEV[sev]
            d.plot(ax=ax, color=c, marker=m, markersize=sz, edgecolor="white", lw=0.5, zorder=8 + list(SEV).index(sev) * -1)
    ax.set_xlim(b[0], b[2]); ax.set_ylim(b[1], b[3]); ax.set_aspect("equal"); ax.set_axis_off()
    ax.add_patch(Rectangle((0, 0), 1, 1, transform=ax.transAxes, fill=False, edgecolor="#9AA5B1", lw=0.8, zorder=30))
    lab = hood.representative_point().iloc[0] if len(hood) else None
    if lab is not None:
        ax.text(lab.x, hood.total_bounds[3] - 60, pilot.upper(), ha="center", fontsize=11, fontweight="bold", color=INK, alpha=0.75, zorder=25,
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.7, pad=2))
    scalebar(ax); north(ax)

    # Title block
    fig.text(0.025, 0.955, f"{pilot}: drainage network and data issues", fontsize=22, fontweight="bold")
    fig.text(0.025, 0.925, "Storm, sanitary and combined sewers checked against nine QA rules before Utility Network migration or hydraulic modelling",
             fontsize=11.5, color=MUTED)

    # Right panel
    x0 = 0.025 + w_frac + 0.035
    xr = 0.975  # right edge for numbers
    fig.text(x0, 0.86, "Pipes by system", fontsize=11, fontweight="bold")
    km = p.groupby("system").length_m.sum() / 1000
    y = 0.835
    for s in ["COMBINED", "STORM", "SANITARY", "FOUNDATION DRAIN"]:
        if s in km.index:
            fig.lines.append(Line2D([x0, x0 + 0.025], [y, y], color=SYS[s][0], lw=2.4, transform=fig.transFigure))
            fig.text(x0 + 0.032, y, f"{SYS[s][1]}", va="center", fontsize=9.5)
            fig.text(xr, y, f"{km[s]:,.1f} km", va="center", ha="right", fontsize=9.5, color=MUTED)
            y -= 0.022
    for lab_, kw in [("Manhole", dict(marker="o", color="white", markeredgecolor=INK, markersize=5)),
                     ("Catch basin", dict(marker="o", color="#9AA5B1", markersize=3)),
                     ("Stormwater pond", dict(marker="s", color="#CFE3F3", markeredgecolor="#9CC3E4", markersize=8))]:
        fig.lines.append(Line2D([x0 + 0.0125], [y], transform=fig.transFigure, ls="", **kw))
        fig.text(x0 + 0.032, y, lab_, va="center", fontsize=9.5); y -= 0.022

    y -= 0.012
    fig.text(x0, y, "QA issues in this map area", fontsize=11, fontweight="bold"); y -= 0.025
    counts = qa.groupby(["severity", "rule", "rule_name"]).size().reset_index(name="n")
    for sev in ["High", "Medium", "Low"]:
        c, m, sz = SEV[sev]
        fig.lines.append(Line2D([x0 + 0.0125], [y], transform=fig.transFigure, ls="", marker=m, color=c, markersize=8 if sev != "Low" else 6, markeredgecolor="white"))
        fig.text(x0 + 0.032, y, f"{sev} severity", va="center", fontsize=9.5, fontweight="bold")
        fig.text(xr, y, f"{counts[counts.severity == sev].n.sum():,}", va="center", ha="right", fontsize=9.5, fontweight="bold")
        y -= 0.02
        for _, r in counts[counts.severity == sev].sort_values("rule").iterrows():
            fig.text(x0 + 0.032, y, f"{r.rule}  {r.rule_name}", va="center", fontsize=8.5, color=MUTED)
            fig.text(xr, y, f"{r.n:,}", va="center", ha="right", fontsize=8.5, color=MUTED)
            y -= 0.018
        y -= 0.006

    # Inset: citywide combined share
    ax2 = fig.add_axes([x0, 0.215, 0.17, 0.2])
    summ.plot(ax=ax2, color="#F1F3F5", edgecolor="white", lw=0.2)
    d = summ[summ.pipe_km >= 1]
    d.plot(ax=ax2, column="combined_share", cmap="Purples", vmin=0, vmax=1, edgecolor="white", lw=0.2)
    for _, r in gpd.read_file(SRC, layer="pilot_areas").to_crs(summ.crs).iterrows():
        gpd.GeoSeries([r.geometry], crs=summ.crs).boundary.plot(ax=ax2, color=INK if r.pilot == pilot else "#9AA5B1", lw=1.2)
    ax2.set_axis_off()
    fig.text(x0, 0.425, "Where the city's combined sewers are", fontsize=11, fontweight="bold", va="bottom")
    sm = plt.cm.ScalarMappable(cmap="Purples", norm=plt.Normalize(0, 100))
    cax = fig.add_axes([x0 + 0.19, 0.33, 0.12, 0.009])
    cb_ = fig.colorbar(sm, cax=cax, orientation="horizontal"); cb_.set_ticks([0, 50, 100]); cb_.set_ticklabels(["0%", "50%", "100%"]); cb_.ax.tick_params(labelsize=7, length=0)
    cb_.outline.set_visible(False)
    fig.text(x0 + 0.19, 0.365, "Share of pipe length that is\ncombined sewer, by neighbourhood", fontsize=8.5, color=MUTED, va="bottom")
    fig.text(x0 + 0.19, 0.285, "Black box: this map area\nGrey box: Terwillegar Towne pilot", fontsize=8, color=MUTED, va="top")

    # Notes
    yrs = p.year_built.dropna()
    notes = [
        f"Pipes in this map area were mostly built {int(yrs.quantile(.25))}–{int(yrs.quantile(.75))} (middle half).",
        "Issues mean \"needs review\", not \"confirmed error\": the open data",
        "has no diameter, material, invert or flow direction.",
    ]
    for i, t in enumerate(notes):
        fig.text(x0, 0.17 - i * 0.018, t, fontsize=8.5, color=MUTED)
    fig.text(x0, 0.095, "Data: City of Edmonton Open Data (drainage network, 0.5 m contours 2019,\nneighbourhood boundaries 2019), retrieved 2026-11-14.\nNAD83 / Alberta 3TM 114°W (EPSG:3776).", fontsize=7.5, color=MUTED, va="top")
    fig.text(x0, 0.045, "Map: Jieni Zhao, November 2026. Independent portfolio work,\nnot a City of Edmonton or EPCOR product.", fontsize=7.5, color=MUTED, va="top")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    tag = pilot.lower().replace(" ", "_")
    fig.savefig(OUTDIR / f"{tag}_drainage_qa_A3.pdf")
    fig.savefig(OUTDIR / f"{tag}_drainage_qa_A3.png", dpi=150)
    fig.savefig(ROOT / "docs" / "img" / f"c6_{tag}_map.png", dpi=110)
    print("saved", tag, "| issues in view:", len(qa))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "Ottewell")
