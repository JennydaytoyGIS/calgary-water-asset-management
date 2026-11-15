"""C4: Describe how Edmonton's drainage network is built and where its data needs attention.

- Network composition: length by system type, citywide and by neighbourhood (combined sewer share).
- Construction period: length by decade and system; share of pipes 60 years or older.
- Data completeness: medium and high severity QA issues per km of pipe, by neighbourhood.

Outputs: docs/img/c4_*.png, outputs/c4_*.csv, layer neighbourhood_summary in
         data/clean/edmonton_drainage_qa.gpkg (used by the dashboard and the map).
Usage:   python scripts/c4_analysis.py   (run after c3_qc_rules.py)
"""
import pathlib
import shutil
import tempfile
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "clean" / "edmonton_drainage.gpkg"
QA = ROOT / "data" / "clean" / "edmonton_drainage_qa.gpkg"
IMG, OUT = ROOT / "docs" / "img", ROOT / "outputs"
YEAR_NOW, OLD = 2026, 60
COLORS = {"STORM": "#2C7FB8", "SANITARY": "#D95F0E", "COMBINED": "#756BB1", "FOUNDATION DRAIN": "#9E9E9E"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def main():
    work = pathlib.Path(tempfile.mkdtemp())
    shutil.copyfile(QA, work / "qa.gpkg")
    p = gpd.read_file(work / "qa.gpkg", layer="pipes_network")
    qa = gpd.read_file(work / "qa.gpkg", layer="qa_issues")
    nb = gpd.read_file(SRC, layer="neighbourhoods_2019")
    IMG.mkdir(parents=True, exist_ok=True); OUT.mkdir(exist_ok=True)
    p["km"] = p.length_m / 1000

    # 1. Composition
    comp = p.groupby("system").km.sum().sort_values(ascending=False)
    comp.round(1).to_csv(OUT / "c4_length_by_system.csv")
    fig, ax = plt.subplots(figsize=(6, 2.6))
    ax.barh(comp.index[::-1], comp.values[::-1], color=[COLORS[s] for s in comp.index[::-1]])
    for y, v in enumerate(comp.values[::-1]):
        ax.text(v + 40, y, f"{v:,.0f} km", va="center")
    ax.set_xlabel("Pipe length (km)"); ax.set_title("Edmonton drainage pipes by system", loc="left", fontweight="bold")
    fig.tight_layout(); fig.savefig(IMG / "c4_length_by_system.png", dpi=200); plt.close(fig)

    # 2. Construction period
    v = p[p.year_built.notna()].copy()
    v["decade"] = (v.year_built // 10 * 10).astype(int)
    dec = v.pivot_table(index="decade", columns="system", values="km", aggfunc="sum", fill_value=0)
    dec = dec[[c for c in COLORS if c in dec]]
    dec.round(2).to_csv(OUT / "c4_length_by_decade.csv")
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    bottom = None
    for s in dec.columns:
        ax.bar(dec.index, dec[s], width=8, bottom=bottom, color=COLORS[s], label=s.title())
        bottom = dec[s] if bottom is None else bottom + dec[s]
    top = dec.sum(axis=1).max()
    ax.set_ylim(0, top * 1.22)
    ax.axvline(YEAR_NOW - OLD - 5, color="#444", ls="--", lw=0.8)
    ax.text(YEAR_NOW - OLD - 6, top * 0.98, f"\u2190 {OLD}+ years old", fontsize=8, color="#444", ha="right")
    ax.set_xlabel("Decade built"); ax.set_ylabel("Pipe length (km)")
    ax.set_title("When the network was built", loc="left", fontweight="bold")
    ax.legend(frameon=False, ncol=4, fontsize=8, loc="upper right", bbox_to_anchor=(1, 1.02))
    fig.tight_layout(); fig.savefig(IMG / "c4_length_by_decade.png", dpi=200); plt.close(fig)
    old = v[v.year_built <= YEAR_NOW - OLD].groupby("system").km.sum().div(v.groupby("system").km.sum()).fillna(0)
    old.round(3).to_csv(OUT / "c4_share_60plus_by_system.csv")

    # 3. By neighbourhood: combined share, age, issues per km.
    # Pipes and issues are assigned to the 2019 neighbourhood polygons by location, because
    # the names in the asset data include neighbourhoods created or renamed after 2019.
    key = "nb2019"
    poly = nb[["neighbourhood_name", "geometry"]].rename(columns={"neighbourhood_name": key})
    def assign(df):
        pts = gpd.GeoDataFrame(geometry=df.geometry.interpolate(0.5, normalized=True) if df.geom_type.iloc[0].endswith("LineString") else df.geometry, crs=df.crs)
        j = gpd.sjoin(pts, poly, how="left", predicate="within")
        return j[~j.index.duplicated()][key]
    p[key] = assign(p)
    qa[key] = assign(qa)
    g = p.groupby(key)
    summ = pd.DataFrame({
        "pipe_km": g.km.sum(),
        "combined_km": p[p.system == "COMBINED"].groupby(key).km.sum(),
        "median_year": g.year_built.median(),
    }).fillna({"combined_km": 0})
    summ["combined_share"] = summ.combined_km / summ.pipe_km
    serious = qa[qa.severity.isin(["High", "Medium"])]
    summ["issues_med_high"] = serious.groupby(key).size()
    summ["issues_all"] = qa.groupby(key).size()
    summ = summ.fillna({"issues_med_high": 0, "issues_all": 0})
    summ["issues_per_km"] = summ.issues_med_high / summ.pipe_km
    summ = summ.round(3).reset_index()
    summ.to_csv(OUT / "c4_neighbourhood_summary.csv", index=False)

    nbs = nb.merge(summ, how="left", left_on="neighbourhood_name", right_on=key).drop(columns=key)
    nbs.to_file(work / "qa.gpkg", layer="neighbourhood_summary", driver="GPKG")
    shutil.copyfile(work / "qa.gpkg", QA)

    fig, axs = plt.subplots(1, 2, figsize=(11, 5.6))
    specs = [(axs[0], "combined_share", "Purples", "Share of pipe length that is combined sewer",
              [0, 0.25, 0.5, 0.75, 1.0], ["None", "Up to 25%", "25–50%", "50–75%", "75–100%"]),
             (axs[1], "issues_per_km", "OrRd", "Medium and high QA issues per km of pipe",
              [0.5, 1, 2, 100], ["Under 0.5", "0.5–1", "1–2", "2 or more"])]
    for ax, col, cmap, title, bins, labels in specs:
        nbs.plot(ax=ax, color="#f2f2f2", edgecolor="white", lw=0.3)
        d = nbs[nbs.pipe_km >= 1]
        if col == "combined_share":
            d = d[d[col] > 0]  # neighbourhoods without combined sewers stay light grey
            bins, labels = bins[1:], labels[1:]
            cmap = ListedColormap(["#DADAEB", "#BCBDDC", "#807DBA", "#4A1486"])
        d.plot(ax=ax, column=col, cmap=cmap, scheme="UserDefined", classification_kwds={"bins": bins}, legend=True,
               edgecolor="white", lw=0.3, legend_kwds={"loc": "lower left", "fontsize": 7.5, "frameon": False, "labels": labels})
        ax.set_title(title, loc="left", fontweight="bold", fontsize=10); ax.set_axis_off()
    fig.text(0.01, 0.01, "Grey: no combined sewer (left) or less than 1 km of pipe. Data: City of Edmonton Open Data, retrieved 2026-11-14.", fontsize=7, color="#555")
    fig.tight_layout(); fig.savefig(IMG / "c4_neighbourhood_maps.png", dpi=200); plt.close(fig)

    print("km by system:", comp.round(1).to_dict(), "| total", round(comp.sum(), 1))
    print("share 60+ years by system:", old.round(3).to_dict())
    print("pipes with valid year:", len(v), "of", len(p))
    print("top combined share:\n", summ.sort_values("combined_share", ascending=False).head(8)[[key, "pipe_km", "combined_share", "median_year"]].to_string(index=False))
    print("top issues/km (>=5 km pipe):\n", summ[summ.pipe_km >= 5].sort_values("issues_per_km", ascending=False).head(8)[[key, "pipe_km", "issues_med_high", "issues_per_km"]].to_string(index=False))
    print("neighbourhoods with combined pipes:", (summ.combined_km > 0).sum(), "| pipes outside 2019 polygons:", p[key].isna().sum())


if __name__ == "__main__":
    main()
