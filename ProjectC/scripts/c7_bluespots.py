"""C7 (A): Where would surface water pond in Ottewell when the sewers are full? ("bluespot" screening)

1. DEM: 1 m grid interpolated from the City's 0.5 m contours (2019). Building footprints are not raised:
   a 3 m raise was tested and dropped, because at 1 m resolution it closes side-yard gaps and traps backyards.
2. Depressions: fill the DEM (morphological reconstruction, equivalent to priority-flood filling);
   depth = filled - original. A bluespot is a connected area deeper than MIN_DEPTH and larger than MIN_AREA.
3. Metrics per bluespot: area, max and mean depth, storage volume.
4. Drainage coverage: distance from the deepest point to the nearest catch basin (Covered <= 15 m,
   Partial <= 40 m, Uncovered > 40 m), catch basins per 1,000 m3 of storage, nearest storm or combined pipe.
5. Exposure: buildings touching the bluespot.
6. Priority: large storage, poor inlet coverage and buildings exposed.
This is a screening that assumes the pipes are already full; it does not replace a hydraulic model.

Outputs: data/clean/edmonton_bluespots.gpkg (bluespots_ottewell, priority_assets_ottewell),
         outputs/dem_ottewell_1m.tif, outputs/bluespots_ottewell.csv
"""
import pathlib, shutil, tempfile
import numpy as np, pandas as pd, geopandas as gpd
import rasterio
from rasterio.transform import from_origin
from rasterio import features
from scipy.interpolate import LinearNDInterpolator
from scipy import ndimage
from skimage.morphology import reconstruction
from shapely.geometry import shape, Point

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "clean" / "edmonton_drainage.gpkg"
OUT_GPKG = ROOT / "data" / "clean" / "edmonton_bluespots.gpkg"
PILOT = "Ottewell"
RES = 1.0
BUILDING_RAISE = 0.0   # tested 3 m: at 1 m resolution it closes the gaps between houses and traps water in back yards
MIN_DEPTH, MIN_AREA = 0.15, 50.0      # m, m2
MAX_STREET_DEPTH = 3.0                 # deeper "depressions" are ravine channels cut by road embankments (culverts not in the DEM)
NEAR_CB = 5.0                          # catch basins inside or within 5 m are counted for inlet density
CRS = 3776


def build_dem(area, cont, bld):
    xmin, ymin, xmax, ymax = area.total_bounds
    pts = cont.geometry.segmentize(2.0).get_coordinates(index_parts=False)
    pts["z"] = cont.elevation.reindex(pts.index).values
    pts = pts.drop_duplicates(["x", "y"])
    nx, ny = int((xmax - xmin) / RES), int((ymax - ymin) / RES)
    gx = xmin + (np.arange(nx) + 0.5) * RES
    gy = ymax - (np.arange(ny) + 0.5) * RES
    X, Y = np.meshgrid(gx, gy)
    dem = LinearNDInterpolator(pts[["x", "y"]].values, pts["z"].values)(X, Y).astype("float32")
    transform = from_origin(xmin, ymax, RES, RES)
    bmask = features.rasterize(((g, 1) for g in bld.geometry), out_shape=dem.shape, transform=transform, fill=0).astype(bool)
    dem_b = dem.copy(); dem_b[bmask] += BUILDING_RAISE
    return dem, dem_b, transform, bmask


def fill(dem):
    # cells outside the contour coverage act as outlets (water can leave the area there)
    valid = np.isfinite(dem)
    d = np.where(valid, dem, np.nanmin(dem) - 10).astype("float64")
    seed = np.full_like(d, d.max())
    seed[0, :], seed[-1, :], seed[:, 0], seed[:, -1] = d[0, :], d[-1, :], d[:, 0], d[:, -1]
    seed[~valid] = d[~valid]
    filled = reconstruction(seed, d, method="erosion")
    filled[~valid] = np.nan
    return filled


def main():
    work = pathlib.Path(tempfile.mkdtemp())
    area = gpd.read_file(SRC, layer="pilot_areas").query("pilot == @PILOT")
    cont = gpd.read_file(SRC, layer="contours_pilot").query("pilot == @PILOT")
    bld = gpd.read_file(ROOT / "data" / "raw" / "edm_buildings_ottewell.geojson").to_crs(CRS)
    bld = bld[bld.intersects(area.geometry.iloc[0])]
    dem, dem_b, transform, bmask = build_dem(area, cont, bld)
    filled = fill(dem_b)
    depth = (filled - dem_b).astype("float32")
    depth[bmask] = 0
    with rasterio.open(work / "dem.tif", "w", driver="GTiff", height=dem.shape[0], width=dem.shape[1], count=2,
                       dtype="float32", crs=f"EPSG:{CRS}", transform=transform, nodata=np.nan, compress="deflate") as r:
        r.write(dem, 1); r.write(depth, 2)
        r.set_band_description(1, "ground elevation (m)"); r.set_band_description(2, "depression depth (m)")
    shutil.copyfile(work / "dem.tif", ROOT / "outputs" / "dem_ottewell_1m.tif")

    lab, n = ndimage.label(depth > 0.02)
    idx = np.arange(1, n + 1)
    maxd = ndimage.maximum(depth, lab, idx)
    area_m2 = ndimage.sum(np.ones_like(depth), lab, idx) * RES * RES
    keep = idx[(maxd >= MIN_DEPTH) & (area_m2 >= MIN_AREA)]
    lab2 = np.where(np.isin(lab, keep), lab, 0).astype("int32")
    rows = []
    for geom, val in features.shapes(lab2, mask=lab2 > 0, transform=transform):
        rows.append({"lab": int(val), "geometry": shape(geom)})
    bs = gpd.GeoDataFrame(rows, crs=CRS).dissolve("lab").reset_index()
    vol = ndimage.sum(depth, lab2, bs.lab) * RES * RES
    mx = ndimage.maximum(depth, lab2, bs.lab)
    pos = ndimage.maximum_position(depth, lab2, bs.lab)
    bs["area_m2"] = bs.geometry.area.round(0)
    bs["max_depth_m"] = np.round(mx, 2)
    bs["volume_m3"] = np.round(vol, 0)
    bs["mean_depth_m"] = (bs.volume_m3 / bs.area_m2).round(2)
    deep = [Point(transform * (c + 0.5, r + 0.5)) for r, c in pos]
    deep = gpd.GeoSeries(deep, crs=CRS)

    cb = gpd.read_file(SRC, layer="catch_basins", bbox=tuple(area.total_bounds))
    pipes = gpd.read_file(SRC, layer="pipes", bbox=tuple(area.total_bounds))
    sc = pipes[pipes.system.isin(["STORM", "COMBINED"])]
    swm = gpd.read_file(SRC, layer="swm_facilities", bbox=tuple(area.total_bounds))
    bs["cb_inside_or_5m"] = [int(cb.intersects(g.buffer(NEAR_CB)).sum()) for g in bs.geometry]
    bs["dist_cb_m"] = [round(cb.distance(p).min(), 1) for p in deep]
    bs["dist_storm_comb_pipe_m"] = [round(sc.distance(p).min(), 1) for p in deep]
    bs["buildings_touching"] = [int(bld.intersects(g.buffer(1.0)).sum()) for g in bs.geometry]
    bs["in_swm_pond"] = [bool(swm.intersects(g).any()) for g in bs.geometry]
    bs["terrain_feature"] = bs.max_depth_m > MAX_STREET_DEPTH
    # coverage is judged at the deepest point, where water collects first
    bs["coverage"] = np.select([bs.dist_cb_m <= 15, bs.dist_cb_m <= 40], ["Covered", "Partial"], "Uncovered")
    bs["cb_per_1000m3"] = (bs.cb_inside_or_5m / (bs.volume_m3 / 1000)).round(2)
    vq = bs.volume_m3.rank(pct=True)
    bs["priority"] = np.select(
        [(~bs.in_swm_pond) & (~bs.terrain_feature) & (vq >= 0.75) & (bs.coverage != "Covered") & (bs.buildings_touching > 0),
         (~bs.in_swm_pond) & (~bs.terrain_feature) & (vq >= 0.5) & ((bs.coverage != "Covered") | (bs.buildings_touching > 0))],
        ["High", "Medium"], "Low")
    bs = bs.sort_values("volume_m3", ascending=False).reset_index(drop=True)
    bs.insert(0, "bluespot_id", [f"BS-{i:04d}" for i in range(1, len(bs) + 1)])
    bs = bs.drop(columns="lab")
    bs["pilot"] = PILOT

    # assets around high and medium priority bluespots (for maintenance and design)
    pr = bs[bs.priority.isin(["High", "Medium"])]
    assets = []
    for _, b in pr.iterrows():
        zone = b.geometry.buffer(30)
        for lay, d in (("catch basin", cb), ("pipe", pipes)):
            near = d[d.intersects(zone)]
            for _, a in near.iterrows():
                assets.append({"bluespot_id": b.bluespot_id, "priority": b.priority, "asset_type": lay, "asset_id": a.asset_id,
                               "system": a.system, "year_built": a.year_built, "dist_m": round(a.geometry.distance(b.geometry), 1), "geometry": a.geometry})
    assets = gpd.GeoDataFrame(assets, crs=CRS)

    tmp = work / "bs.gpkg"
    bs.to_file(tmp, layer="bluespots_ottewell", driver="GPKG")
    if len(assets):
        assets.to_file(tmp, layer="priority_assets_ottewell", driver="GPKG")
    shutil.copyfile(tmp, OUT_GPKG)
    bs.drop(columns="geometry").to_csv(ROOT / "outputs" / "bluespots_ottewell.csv", index=False)
    print("DEM", dem.shape, "elev", np.nanmin(dem).round(1), np.nanmax(dem).round(1), "| buildings", len(bld))
    print("bluespots", len(bs), "| total volume m3", int(bs.volume_m3.sum()), "| coverage", bs.coverage.value_counts().to_dict(), "| priority", bs.priority.value_counts().to_dict())
    print(bs.head(12)[["bluespot_id", "area_m2", "max_depth_m", "volume_m3", "coverage", "dist_cb_m", "buildings_touching", "in_swm_pond", "terrain_feature", "priority"]].to_string(index=False))
    print("assets near priority bluespots:", len(assets), assets.groupby("asset_type").asset_id.nunique().to_dict() if len(assets) else {})


if __name__ == "__main__":
    main()
