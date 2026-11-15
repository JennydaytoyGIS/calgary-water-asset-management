"""C10: A3 map. Ottewell bluespots by priority, with drainage inlets, and the citywide model in an inset.
Output: outputs/maps/ottewell_bluespots_A3.pdf/.png, docs/img/c10_ottewell_bluespots.png
"""
import pathlib
import numpy as np, pandas as pd, geopandas as gpd, rasterio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from matplotlib.colors import LightSource, ListedColormap, BoundaryNorm

ROOT = pathlib.Path(__file__).resolve().parents[1]
G = ROOT / "data" / "clean" / "edmonton_drainage.gpkg"
B = ROOT / "data" / "clean" / "edmonton_bluespots.gpkg"
INK, MUTED = "#1F2933", "#616E7C"
PRI = {"High": "#C0392B", "Medium": "#E69F00", "Low": "#9AA5B1"}
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK})


def main():
    r = rasterio.open(ROOT / "outputs" / "dem_ottewell_1m.tif")
    dem, dep = r.read(1), r.read(2)
    ext = [r.bounds.left, r.bounds.right, r.bounds.bottom, r.bounds.top]
    bs = gpd.read_file(B, layer="bluespots_ottewell")
    nbm = gpd.read_file(B, layer="nb_model")
    nb = gpd.read_file(G, layer="neighbourhoods_2019")
    hood = nb[nb.neighbourhood_name == "Ottewell"]
    bb = tuple(r.bounds)
    cb = gpd.read_file(G, layer="catch_basins", bbox=bb)
    pipes = gpd.read_file(G, layer="pipes", bbox=bb)
    swm = gpd.read_file(G, layer="swm_facilities", bbox=bb)

    fig = plt.figure(figsize=(16.54, 11.69)); fig.patch.set_facecolor("white")
    h = 0.84; w = h * 11.69 * (ext[1] - ext[0]) / (ext[3] - ext[2]) / 16.54
    ax = fig.add_axes([0.025, 0.035, w, h])
    hs = LightSource(azdeg=315, altdeg=45).hillshade(np.nan_to_num(dem, nan=np.nanmean(dem)), vert_exag=4, dx=1, dy=1)
    ax.imshow(hs, extent=ext, cmap="Greys_r", alpha=0.35, zorder=0)
    d = np.where(dep > 0.05, dep, np.nan)
    cmap = ListedColormap(["#DCEBF7", "#9ECAE1", "#4292C6", "#08519C"]); norm = BoundaryNorm([0.05, 0.25, 0.5, 1.0, 50], cmap.N)
    ax.imshow(d, extent=ext, cmap=cmap, norm=norm, zorder=1, interpolation="nearest")
    swm.boundary.plot(ax=ax, color="#4292C6", lw=0.6, zorder=2)
    nb.boundary.plot(ax=ax, color="#B8BEC6", lw=0.6, linestyle="--", zorder=2)
    hood.boundary.plot(ax=ax, color=INK, lw=1.4, zorder=3)
    pipes[pipes.system == "COMBINED"].plot(ax=ax, color="#7B5EA7", lw=0.5, alpha=0.7, zorder=3)
    pipes[pipes.system == "STORM"].plot(ax=ax, color="#2C7FB8", lw=0.5, alpha=0.7, zorder=3)
    cb.plot(ax=ax, color=INK, markersize=1.5, zorder=4)
    for k in ["Low", "Medium", "High"]:
        sel = bs[(bs.priority == k) & (~bs.terrain_feature)]
        sel.boundary.plot(ax=ax, color=PRI[k], lw=1.6 if k != "Low" else 0.6, zorder=5)
    bs[bs.terrain_feature].boundary.plot(ax=ax, color="#2F855A", lw=0.8, linestyle=":", zorder=5)
    top = bs[bs.priority == "High"].sort_values("volume_m3", ascending=False).head(8)
    for _, b in top.iterrows():
        c = b.geometry.representative_point()
        ax.annotate(b.bluespot_id.replace("BS-", ""), (c.x, c.y), xytext=(6, 6), textcoords="offset points", fontsize=8, fontweight="bold", color=PRI["High"],
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85), zorder=6)
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3]); ax.set_axis_off()
    ax.add_patch(Rectangle((0, 0), 1, 1, transform=ax.transAxes, fill=False, edgecolor="#9AA5B1", lw=0.8, zorder=30))
    x0b, y0b = ext[0] + 60, ext[2] + 60
    for i in range(2):
        ax.add_patch(Rectangle((x0b + i * 250, y0b), 250, 12, facecolor=INK if i == 0 else "white", edgecolor=INK, lw=0.6, zorder=20))
    for t, lab in [(0, "0"), (250, "250"), (500, "500 m")]:
        ax.text(x0b + t, y0b + 25, lab, ha="center", fontsize=7, zorder=20)
    ax.annotate("N", xy=(0.95, 0.93), xytext=(0.95, 0.86), xycoords="axes fraction", ha="center", fontsize=10, fontweight="bold", arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.2))

    fig.text(0.025, 0.955, "Ottewell: where water ponds when the sewers are full", fontsize=22, fontweight="bold")
    fig.text(0.025, 0.925, "Depressions in a 1 m surface from the City's 0.5 m contours, ranked by storage, catch basin coverage and buildings exposed",
             fontsize=11.5, color=MUTED)
    x0 = 0.025 + w + 0.035; xr = 0.975; y = 0.86
    fig.text(x0, y, "Ponding depth (filled surface)", fontsize=11, fontweight="bold"); y -= 0.025
    for c, lab in zip(cmap.colors, ["0.05–0.25 m", "0.25–0.5 m", "0.5–1 m", "over 1 m"]):
        fig.patches.append(Rectangle((x0, y - 0.006), 0.02, 0.012, transform=fig.transFigure, facecolor=c, edgecolor="none"))
        fig.text(x0 + 0.028, y, lab, va="center", fontsize=9.5); y -= 0.02
    y -= 0.01
    fig.text(x0, y, "Bluespot priority", fontsize=11, fontweight="bold"); y -= 0.025
    nonterr = bs[~bs.terrain_feature]
    for k, desc in [("High", "large storage, inlet over 15 m away, buildings exposed"), ("Medium", "medium storage with a coverage gap or buildings"), ("Low", "small or well served")]:
        fig.lines.append(Line2D([x0, x0 + 0.02], [y, y], color=PRI[k], lw=2.4, transform=fig.transFigure))
        fig.text(x0 + 0.028, y, f"{k}", va="center", fontsize=9.5, fontweight="bold")
        fig.text(xr, y, f"{(nonterr.priority == k).sum()}", va="center", ha="right", fontsize=9.5)
        fig.text(x0 + 0.028, y - 0.016, desc, va="center", fontsize=8, color=MUTED); y -= 0.038
    fig.lines.append(Line2D([x0, x0 + 0.02], [y, y], color="#2F855A", lw=1.2, ls=":", transform=fig.transFigure))
    fig.text(x0 + 0.028, y, "Ravine head closed by road fill in the surface (excluded)", va="center", fontsize=8.5, color=MUTED); y -= 0.022
    for lab, kw in [("Catch basin", dict(marker="o", color=INK, markersize=2.5, ls="")), ("Storm pipe", dict(color="#2C7FB8", lw=1.5)), ("Combined pipe", dict(color="#7B5EA7", lw=1.5))]:
        fig.lines.append(Line2D([x0, x0 + 0.02] if "pipe" in lab else [x0 + 0.01], [y, y] if "pipe" in lab else [y], transform=fig.transFigure, **kw))
        fig.text(x0 + 0.028, y, lab, va="center", fontsize=9); y -= 0.02

    y -= 0.012
    fig.text(x0, y, "Top high-priority bluespots", fontsize=11, fontweight="bold"); y -= 0.022
    fig.text(x0, y, "ID      storage m³   max depth   nearest inlet   buildings", fontsize=8, color=MUTED, family="DejaVu Sans Mono"); y -= 0.018
    for _, b in top.iterrows():
        fig.text(x0, y, f"{b.bluespot_id[3:]:<6}{int(b.volume_m3):>9,}{b.max_depth_m:>10.2f} m{b.dist_cb_m:>11.0f} m{int(b.buildings_touching):>10}", fontsize=8, family="DejaVu Sans Mono"); y -= 0.016

    ax2 = fig.add_axes([x0, 0.10, 0.14, 0.17])
    nb.plot(ax=ax2, color="#F1F3F5", edgecolor="white", lw=0.2)
    nbm.plot(ax=ax2, column="rate_per_km2", cmap="Blues", scheme="Quantiles", k=5, edgecolor="white", lw=0.2)
    hood.boundary.plot(ax=ax2, color="#C0392B", lw=1.2); ax2.set_axis_off()
    fig.text(x0, 0.285, "Citywide: rain-season 311 ponding\nreports per km² (2023–2026)", fontsize=9, fontweight="bold", va="bottom")
    fig.text(x0 + 0.15, 0.25, "Darker = more reports\nRed outline: Ottewell\n\nA model of these reports\nexplains 25% of the variation\nwith terrain and drainage\nfactors (terrain alone: none).", fontsize=7.8, color=MUTED, va="top")
    fig.text(x0, 0.06, "Screening assumes the sewers are full; it does not replace a hydraulic model. Contours 2019; drainage network and 311 data\nfrom City of Edmonton Open Data, retrieved 2026-11-14/15. NAD83 / Alberta 3TM 114°W. Map: Jieni Zhao, November 2026.\nIndependent portfolio work, not a City of Edmonton or EPCOR product.", fontsize=7, color=MUTED, va="top")
    out = ROOT / "outputs" / "maps"; out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / "ottewell_bluespots_A3.pdf"); fig.savefig(out / "ottewell_bluespots_A3.png", dpi=150)
    fig.savefig(ROOT / "docs" / "img" / "c10_ottewell_bluespots.png", dpi=110)
    print("saved")

if __name__ == "__main__":
    main()
