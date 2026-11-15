"""C2: Standardize the raw Edmonton drainage layers into one documented data model.

- Projects everything to NAD83 / Alberta 3TM 114W (EPSG:3776), so distances are in metres.
- Gives every asset a stable ID (the open data has no asset ID).
- Turns placeholder construction years (0, 9999) into nulls and keeps a flag.
- Fills missing neighbourhood names from the 2019 neighbourhood boundaries and records the source.
- Tags features inside the two pilot areas.

Output: data/clean/edmonton_drainage.gpkg (see docs/data_dictionary.md)
Usage:  python scripts/c2_standardize.py
"""
import pathlib
import shutil
import tempfile
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box, LineString

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, CLEAN = ROOT / "data" / "raw", ROOT / "data" / "clean"
FINAL = CLEAN / "edmonton_drainage.gpkg"
# SQLite can fail on synced or network folders, so the GeoPackage is built in a
# temporary folder and copied into data/clean at the end.
OUT = pathlib.Path(tempfile.mkdtemp()) / "edmonton_drainage.gpkg"
CRS = 3776

ASSETS = {  # layer name: (raw file, ID prefix)
    "pipes": ("edm_drainage_pipes", "PIPE"),
    "manholes": ("edm_drainage_manholes", "MH"),
    "catch_basins": ("edm_drainage_catch_basins", "CB"),
    "cb_leads": ("edm_drainage_cb_leads", "CBL"),
    "outfalls": ("edm_drainage_outfalls", "OUT"),
    "pump_stations": ("edm_drainage_pump_stations", "PS"),
    "swm_facilities": ("edm_drainage_swm_facilities", "SWM"),
}
PILOTS = {  # (north, west, south, east) in WGS84, same boxes as c1_fetch.py
    "Ottewell": (53.543676, -113.446940, 53.518894, -113.414549),
    "Terwillegar Towne": (53.460054, -113.594095, 53.441287, -113.561513),
}


def read(name):
    return gpd.read_file(RAW / f"{name}.geojson").to_crs(CRS)


def pilot_areas():
    rows = [{"pilot": k, "geometry": box(w, s, e, n)} for k, (n, w, s, e) in PILOTS.items()]
    return gpd.GeoDataFrame(rows, crs=4326).to_crs(CRS)


def year_fields(df):
    y = pd.to_numeric(df["year_const"], errors="coerce")
    flag = np.select([y.isna(), y == 0, y == 9999, (y < 1900) | (y > 2026)],
                     ["missing", "placeholder_0", "placeholder_9999", "out_of_range"], "valid")
    df["year_raw"] = y.astype("Int64")
    df["year_flag"] = flag
    df["year_built"] = y.where(flag == "valid").astype("Int64")
    return df.drop(columns=["year_const"])


def single_part(geom):
    if geom is not None and geom.geom_type == "MultiLineString" and len(geom.geoms) == 1:
        return LineString(geom.geoms[0])
    return geom


def stable_ids(df, prefix):
    pt = df.geometry.representative_point()
    order = pd.DataFrame({"s": df["system"].fillna(""), "x": pt.x.round(2), "y": pt.y.round(2)}).sort_values(["s", "x", "y"]).index
    ids = pd.Series(index=order, data=[f"{prefix}-{i:06d}" for i in range(1, len(df) + 1)])
    df.insert(0, "asset_id", ids.reindex(df.index).values)
    return df


def fill_neighbourhood(df, nb):
    df["nb_source"] = np.where(df["neighbourhood_name"].isna(), None, "source")
    miss = df["neighbourhood_name"].isna()
    if miss.any():
        pts = gpd.GeoDataFrame(geometry=df.loc[miss].geometry.representative_point(), crs=CRS)
        hit = gpd.sjoin(pts, nb[["descriptiv", "geometry"]], how="left", predicate="within")
        hit = hit[~hit.index.duplicated()]
        df.loc[miss, "neighbourhood_name"] = hit["descriptiv"]
        df.loc[miss & df["neighbourhood_name"].notna(), "nb_source"] = "filled_2019_boundaries"
    return df


def tag_pilot(df, pilots):
    pts = gpd.GeoDataFrame(geometry=df.geometry.representative_point(), crs=CRS)
    hit = gpd.sjoin(pts, pilots, how="left", predicate="within")
    hit = hit[~hit.index.duplicated()]
    df["pilot"] = hit["pilot"]
    return df


def main():
    CLEAN.mkdir(parents=True, exist_ok=True)
    nb = read("edm_neighbourhoods_2019")
    pilots = pilot_areas()
    for layer, (raw, prefix) in ASSETS.items():
        df = read(raw)
        df = df.rename(columns={"type": "system"})
        df["system"] = df["system"].str.strip().str.upper()
        df = year_fields(df)
        if "rim_elev" in df:
            r = pd.to_numeric(df["rim_elev"], errors="coerce")
            df["rim_elev"] = r
            df["rim_flag"] = np.select([r.isna(), r < 1], ["missing", "zero_or_near_zero"], "valid")
        if df.geom_type.str.contains("Line").any():
            df["n_parts"] = df.geometry.apply(lambda g: len(g.geoms) if g.geom_type.startswith("Multi") else 1)
            df["geometry"] = df.geometry.apply(single_part)
            df["length_m"] = df.length.round(2)
        df = fill_neighbourhood(df, nb)
        df = tag_pilot(df, pilots)
        df = df.drop(columns=["latitude", "longitude"], errors="ignore")
        df = stable_ids(df, prefix)
        df.to_file(OUT, layer=layer, driver="GPKG")
        print(f"{layer}: {len(df)} | systems {df['system'].value_counts().to_dict()} | year flags {df['year_flag'].value_counts().to_dict()}"
              + (f" | rim flags {df['rim_flag'].value_counts().to_dict()}" if "rim_flag" in df else "")
              + f" | nb filled {(df['nb_source'] == 'filled_2019_boundaries').sum()}, still missing {df['neighbourhood_name'].isna().sum()}"
              + f" | pilot {df['pilot'].value_counts().to_dict()}")
    nb.rename(columns={"neighbourh": "nb_number", "descriptiv": "neighbourhood_name", "descriptio": "description"}).to_file(OUT, layer="neighbourhoods_2019", driver="GPKG")
    pilots.to_file(OUT, layer="pilot_areas", driver="GPKG")
    cont = []
    for k, f in [("Ottewell", "edm_contours_ottewell"), ("Terwillegar Towne", "edm_contours_terwillegar_towne")]:
        c = read(f)
        c["pilot"] = k
        c["elevation"] = pd.to_numeric(c["elevation"], errors="coerce")
        cont.append(c)
    cont = pd.concat(cont, ignore_index=True)
    cont.to_file(OUT, layer="contours_pilot", driver="GPKG")
    print(f"contours_pilot: {len(cont)} | elevation range {cont['elevation'].min()}–{cont['elevation'].max()}")
    shutil.copyfile(OUT, FINAL)
    print(f"written: {FINAL}")


if __name__ == "__main__":
    main()
