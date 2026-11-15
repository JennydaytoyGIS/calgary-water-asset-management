"""C9 (B): What explains where people report ponding? An explainable model of 311 reports by neighbourhood.

Target: 311 "Ponding" requests (roads, alleys, sidewalks) in the rain season (May to September,
2023 to 2026), per neighbourhood, per km2.
Factors:
  terrain   mean slope, low-lying index, depression share (c8_terrain_city.py)
  drainage  catch basins per km2, catch basins per km of storm and combined pipe, storm and combined
            pipe density, combined sewer share, median construction year
  people    population density (2021 census), kept separate to test reporting bias
Models:
  1. Negative binomial regression (counts, offset = log area) as an interpretable baseline.
  2. XGBoost on log(1 + reports per km2) with spatial block cross-validation (8 blocks from k-means
     on neighbourhood centroids), compared across three factor sets (ablation):
     terrain only -> + drainage -> + population.
  3. SHAP values from the full model: global importance and the top drivers of each neighbourhood.
  4. Moran's I of the model residuals (queen contiguity, 999 permutations).
Outputs: outputs/c9_*.csv, docs/img/c9_*.png, layer nb_model in data/clean/edmonton_bluespots.gpkg
"""
import json, pathlib, shutil, tempfile
import numpy as np, pandas as pd, geopandas as gpd
import statsmodels.api as sm
import xgboost as xgb, shap
from sklearn.cluster import KMeans
from sklearn.model_selection import GroupKFold
from sklearn.metrics import r2_score
from scipy.stats import spearmanr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[1]
G = ROOT / "data" / "clean" / "edmonton_drainage.gpkg"
OUT_GPKG = ROOT / "data" / "clean" / "edmonton_bluespots.gpkg"
IMG, OUT = ROOT / "docs" / "img", ROOT / "outputs"
SEED = 42
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
LABELS = {"mean_slope_deg": "Mean slope", "low_lying_m": "Low-lying index", "depression_share": "Depression share",
          "cb_per_km2": "Catch basins per km²", "cb_per_km_sc_pipe": "Catch basins per km of storm/combined pipe",
          "sc_pipe_km_per_km2": "Storm and combined pipe density", "combined_share": "Combined sewer share",
          "median_year": "Median year built", "pop_density": "Population density"}
TERRAIN = ["mean_slope_deg", "low_lying_m", "depression_share"]
DRAIN = ["cb_per_km2", "cb_per_km_sc_pipe", "sc_pipe_km_per_km2", "combined_share", "median_year"]
PEOPLE = ["pop_density"]


def build():
    nb = gpd.read_file(G, layer="neighbourhoods_2019")
    nb["area_km2"] = nb.area / 1e6
    rows = pd.DataFrame(json.load(open(ROOT / "data" / "raw" / "edm_311_ponding.json"))["rows"])
    rows["month_number"] = rows.month_number.astype(int)
    p = rows[rows.service_description.str.startswith("Ponding") & rows.month_number.between(5, 9)].copy()
    p["nb_number"] = p.neighbourhood_id.astype(str).str.strip()
    cnt = p.groupby("nb_number").size().rename("reports")
    unmatched = p[~p.nb_number.isin(nb.nb_number.astype(str))]
    nb["nb_number"] = nb.nb_number.astype(str)
    nb = nb.merge(cnt, left_on="nb_number", right_index=True, how="left").fillna({"reports": 0})

    pipes = gpd.read_file(G, layer="pipes"); cb = gpd.read_file(G, layer="catch_basins")
    poly = nb[["nb_number", "geometry"]]
    def assign(df, line):
        pt = gpd.GeoDataFrame(df.drop(columns="geometry"), geometry=df.geometry.interpolate(0.5, normalized=True) if line else df.geometry, crs=df.crs)
        j = gpd.sjoin(pt, poly, predicate="within", how="left"); return j[~j.index.duplicated()]
    pj, cj = assign(pipes, True), assign(cb, False)
    pj["km"] = pj.length_m / 1000
    sc = pj[pj.system.isin(["STORM", "COMBINED"])]
    f = pd.DataFrame({
        "pipe_km": pj.groupby("nb_number").km.sum(),
        "sc_km": sc.groupby("nb_number").km.sum(),
        "comb_km": pj[pj.system == "COMBINED"].groupby("nb_number").km.sum(),
        "cb_n": cj.groupby("nb_number").size(),
        "median_year": pj.groupby("nb_number").year_built.median(),
    }).fillna({"sc_km": 0, "comb_km": 0, "cb_n": 0})
    nb = nb.merge(f, left_on="nb_number", right_index=True, how="left")
    terr = pd.read_csv(OUT / "c8_terrain_by_neighbourhood.csv", dtype={"nb_number": str})
    nb = nb.merge(terr[["nb_number"] + TERRAIN], on="nb_number", how="left")
    pop = pd.DataFrame(json.load(open(ROOT / "data" / "raw" / "edm_census2021_population.json"))["rows"])
    pop["nb_number"] = pop.neighbourhood_number.astype(str); pop["population"] = pd.to_numeric(pop.total_population, errors="coerce")
    nb = nb.merge(pop[["nb_number", "population"]], on="nb_number", how="left")
    nb["cb_per_km2"] = nb.cb_n / nb.area_km2
    nb["cb_per_km_sc_pipe"] = nb.cb_n / nb.sc_km.replace(0, np.nan)
    nb["sc_pipe_km_per_km2"] = nb.sc_km / nb.area_km2
    nb["combined_share"] = nb.comb_km / nb.pipe_km
    nb["pop_density"] = nb.population / nb.area_km2
    nb["rate_per_km2"] = nb.reports / nb.area_km2
    # keep built-up neighbourhoods with a piped drainage network and census population
    use = nb[(nb.pipe_km >= 2) & (nb.population >= 100) & nb[TERRAIN + DRAIN + PEOPLE].notna().all(axis=1)].copy()
    print(f"ponding reports May–Sep: {len(p)} | not matched to 2019 neighbourhoods: {len(unmatched)} | neighbourhoods modelled: {len(use)} of {len(nb)}")
    return nb, use


def nb_regression(use):
    X = use[TERRAIN + DRAIN + PEOPLE]; Xs = (X - X.mean()) / X.std()
    m = sm.GLM(use.reports, sm.add_constant(Xs), family=sm.families.NegativeBinomial(alpha=1.0), offset=np.log(use.area_km2)).fit()
    t = pd.DataFrame({"irr_per_sd": np.exp(m.params), "p_value": m.pvalues}).drop("const").round(3)
    t.index = [LABELS[i] for i in t.index]
    return t, m


def cv_xgb(use, cols, groups):
    y = np.log1p(use.rate_per_km2.values); X = use[cols].values
    pred = np.zeros_like(y)
    for tr, te in GroupKFold(n_splits=8).split(X, y, groups):
        mdl = xgb.XGBRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, random_state=SEED)
        mdl.fit(X[tr], y[tr]); pred[te] = mdl.predict(X[te])
    return r2_score(y, pred), spearmanr(y, pred).correlation, pred


def morans_i(gdf, v, perms=999):
    w = gpd.sjoin(gdf[["geometry"]].reset_index(), gdf[["geometry"]].reset_index(), predicate="touches")
    w = w[w["index_left"] != w["index_right"]]
    pos = {k: i for i, k in enumerate(gdf.index)}
    i_, j_ = w["index_left"].map(pos).values, w["index_right"].map(pos).values
    deg = np.bincount(i_, minlength=len(gdf)).astype(float)
    z = v - v.mean()
    def I(zz):
        lag = np.bincount(i_, weights=zz[j_] / deg[i_], minlength=len(zz))
        return len(zz) / len(zz) * (zz * lag).sum() / (zz ** 2).sum()
    obs = I(z); rng = np.random.default_rng(SEED)
    sims = np.array([I(rng.permutation(z)) for _ in range(perms)])
    return obs, (np.sum(sims >= obs) + 1) / (perms + 1)


def main():
    nb, use = build()
    tab, m = nb_regression(use)
    tab.to_csv(OUT / "c9_negbin_irr.csv")
    cent = np.c_[use.geometry.centroid.x, use.geometry.centroid.y]
    groups = KMeans(n_clusters=8, random_state=SEED, n_init=10).fit_predict(cent)
    abl = []
    for name, cols in [("Terrain only", TERRAIN), ("Terrain + drainage", TERRAIN + DRAIN), ("Terrain + drainage + population", TERRAIN + DRAIN + PEOPLE)]:
        r2, rho, pred = cv_xgb(use, cols, groups)
        abl.append({"factor_set": name, "cv_r2": round(r2, 3), "cv_spearman": round(rho, 3)})
        if name.endswith("population"):
            use["pred_log_rate"] = pred
    abl = pd.DataFrame(abl); abl.to_csv(OUT / "c9_ablation.csv", index=False)

    full = TERRAIN + DRAIN + PEOPLE
    mdl = xgb.XGBRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, random_state=SEED)
    y = np.log1p(use.rate_per_km2.values); mdl.fit(use[full].values, y)
    # SHAP values from XGBoost's built-in TreeSHAP (pred_contribs); the last column is the base value
    sv = mdl.get_booster().predict(xgb.DMatrix(use[full].values), pred_contribs=True)[:, :-1]
    imp = pd.Series(np.abs(sv).mean(0), index=[LABELS[c] for c in full]).sort_values()
    imp.round(4).to_csv(OUT / "c9_shap_importance.csv")
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    cat = ["#2C7FB8" if LABELS[c] in [LABELS[d] for d in DRAIN] else "#8C6D31" if LABELS[c] in [LABELS[t] for t in TERRAIN] else "#9E9E9E" for c in full]
    colmap = dict(zip([LABELS[c] for c in full], cat))
    ax.barh(imp.index, imp.values, color=[colmap[i] for i in imp.index])
    ax.set_xlabel("Mean |SHAP value| (effect on log reports per km²)")
    ax.set_title("What explains rain-season ponding reports", loc="left", fontweight="bold")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color="#8C6D31", label="Terrain"), Patch(color="#2C7FB8", label="Drainage"), Patch(color="#9E9E9E", label="Population (reporting)")], frameon=False, fontsize=8, loc="lower right")
    fig.tight_layout(); fig.savefig(IMG / "c9_shap_importance.png", dpi=200); plt.close(fig)
    shap.summary_plot(sv, use[full], feature_names=[LABELS[c] for c in full], show=False, plot_size=(7, 4))
    plt.tight_layout(); plt.savefig(IMG / "c9_shap_beeswarm.png", dpi=200); plt.close()

    # top drivers per neighbourhood (positive SHAP = pushes reports up)
    names = np.array([LABELS[c] for c in full])
    use["driver_1"], use["driver_2"], use["driver_3"] = [[names[np.argsort(-r)][k] if np.sort(-r)[k] < 0 else "" for r in sv] for k in range(3)]
    use["residual"] = y - use.pred_log_rate
    I, pval = morans_i(use, use.residual.values)
    use["obs_rank"] = use.rate_per_km2.rank(ascending=False).astype(int)
    use["pred_rank"] = use.pred_log_rate.rank(ascending=False).astype(int)
    keep = ["nb_number", "neighbourhood_name", "reports", "area_km2", "rate_per_km2", "pred_log_rate", "residual", "obs_rank", "pred_rank",
            "driver_1", "driver_2", "driver_3"] + full
    out = use[keep + ["geometry"]].copy()
    work = pathlib.Path(tempfile.mkdtemp()); shutil.copyfile(OUT_GPKG, work / "b.gpkg")
    out.to_file(work / "b.gpkg", layer="nb_model", driver="GPKG"); shutil.copyfile(work / "b.gpkg", OUT_GPKG)
    out.drop(columns="geometry").to_csv(OUT / "c9_neighbourhood_model.csv", index=False)

    print("\nNegative binomial (IRR per 1 SD):\n", tab.to_string())
    print("\nAblation (spatial block CV):\n", abl.to_string(index=False))
    print("\nSHAP importance:\n", imp.sort_values(ascending=False).round(4).to_string())
    print(f"\nResidual Moran's I = {I:.3f}, p = {pval:.3f}")
    for n in ["Ottewell", "Lauderdale", "Terwillegar Towne"]:
        r = use[use.neighbourhood_name.str.lower() == n.lower()]
        if len(r):
            r = r.iloc[0]; print(f"{n}: reports {int(r.reports)}, rate {r.rate_per_km2:.1f}/km2, observed rank {r.obs_rank}/{len(use)}, predicted rank {r.pred_rank}, drivers: {r.driver_1}; {r.driver_2}; {r.driver_3}")


if __name__ == "__main__":
    main()
