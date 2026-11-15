"""C8a: Citywide 20 m terrain surface from the City's contours (2.5 m interval), and per-neighbourhood
terrain factors for the ponding model: mean slope, low-lying index and depression share.

Low-lying index = neighbourhood mean elevation minus mean elevation within 2 km around it (negative = lower than surroundings).
Depression share = share of the neighbourhood's area inside closed depressions deeper than 0.5 m on the filled 20 m surface.
Output: outputs/c8_terrain_by_neighbourhood.csv
"""
import pathlib
import numpy as np, pandas as pd, geopandas as gpd
from rasterio.transform import from_origin
from rasterio import features
from scipy.interpolate import LinearNDInterpolator
from scipy import ndimage
from skimage.morphology import reconstruction

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES, CRS = 20.0, 3776

def main():
    nb = gpd.read_file(ROOT / "data" / "clean" / "edmonton_drainage.gpkg", layer="neighbourhoods_2019")
    # 4.6 million contour vertices: read with pyogrio, project, and average them into 20 m cells
    # before interpolating, so the triangulation fits in memory
    import pyogrio, shapely
    from pyproj import Transformer
    cont = pyogrio.read_dataframe(ROOT / "data" / "raw" / "edm_contours_2p5m_citywide.geojson", columns=["elevation"])
    z_line = pd.to_numeric(cont["elevation"], errors="coerce").values
    xy, ix = shapely.get_coordinates(cont.geometry.values, return_index=True)
    x, y = Transformer.from_crs(4326, CRS, always_xy=True).transform(xy[:, 0], xy[:, 1])
    xmin, ymin, xmax, ymax = nb.total_bounds
    cx = ((x - xmin) // RES).astype(np.int64); cy = ((y - ymin) // RES).astype(np.int64)
    pts = pd.DataFrame({"cx": cx, "cy": cy, "z": z_line[ix]}).groupby(["cx", "cy"], as_index=False).z.mean()
    pts["x"] = xmin + (pts.cx + 0.5) * RES; pts["y"] = ymin + (pts.cy + 0.5) * RES
    del cont, xy, ix, x, y
    nx, ny = int((xmax - xmin) / RES) + 1, int((ymax - ymin) / RES) + 1
    gx = xmin + (np.arange(nx) + 0.5) * RES; gy = ymax - (np.arange(ny) + 0.5) * RES
    X, Y = np.meshgrid(gx, gy)
    dem = LinearNDInterpolator(pts[["x", "y"]].values, pts["z"].values)(X, Y).astype("float32")
    tr = from_origin(xmin, ymax, RES, RES)
    gyy, gxx = np.gradient(np.where(np.isfinite(dem), dem, np.nan), RES)
    slope = np.degrees(np.arctan(np.hypot(gxx, gyy)))
    valid = np.isfinite(dem)
    d = np.where(valid, dem, np.nanmin(dem) - 10).astype("float64")
    seed = np.full_like(d, d.max()); seed[0, :], seed[-1, :], seed[:, 0], seed[:, -1] = d[0, :], d[-1, :], d[:, 0], d[:, -1]
    seed[~valid] = d[~valid]
    depth = reconstruction(seed, d, method="erosion") - d
    depth[~valid] = np.nan
    lab = features.rasterize(((g, i + 1) for i, g in enumerate(nb.geometry)), out_shape=dem.shape, transform=tr, fill=0)
    idx = np.arange(1, len(nb) + 1)
    mean_el = ndimage.mean(np.nan_to_num(dem, nan=np.nanmean(dem)), lab, idx)
    mean_sl = ndimage.mean(np.nan_to_num(slope, nan=0), lab, idx)
    dep_sh = ndimage.mean((np.nan_to_num(depth) > 0.5).astype(float), lab, idx)
    # mean elevation within 2 km (box filter) for the low-lying index
    k = int(4000 / RES) | 1
    filled_dem = np.where(valid, dem, np.nanmean(dem))
    ring = ndimage.uniform_filter(filled_dem, size=k)
    ring_mean = ndimage.mean(ring, lab, idx)
    out = pd.DataFrame({"nb_number": nb.nb_number.values, "neighbourhood_name": nb.neighbourhood_name.values,
                        "mean_elev_m": np.round(mean_el, 2), "mean_slope_deg": np.round(mean_sl, 3),
                        "low_lying_m": np.round(mean_el - ring_mean, 2), "depression_share": np.round(dep_sh, 4)})
    out.to_csv(ROOT / "outputs" / "c8_terrain_by_neighbourhood.csv", index=False)
    print("DEM", dem.shape, "points", len(pts), "| elev", np.nanmin(dem).round(1), np.nanmax(dem).round(1))
    print(out.describe().round(3).to_string())

if __name__ == "__main__":
    main()
