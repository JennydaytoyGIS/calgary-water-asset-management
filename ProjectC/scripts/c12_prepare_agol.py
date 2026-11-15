"""C12: Package the ponding screening layers for ArcGIS Online (zipped file geodatabase).
Layers: bluespots_ottewell, priority_catch_basins, priority_pipes, nb_model, ottewell_boundary
Output: outputs/agol/ponding_screening_agol.gdb.zip
"""
import pathlib, shutil, tempfile
import geopandas as gpd
ROOT = pathlib.Path(__file__).resolve().parents[1]
B = ROOT / "data" / "clean" / "edmonton_bluespots.gpkg"; G = ROOT / "data" / "clean" / "edmonton_drainage.gpkg"

def main():
    work = pathlib.Path(tempfile.mkdtemp()); gdb = work / "ponding_screening.gdb"
    nb = gpd.read_file(G, layer="neighbourhoods_2019")
    layers = {
        "bluespots_ottewell": gpd.read_file(B, layer="bluespots_ottewell"),
        "priority_catch_basins": (pa := gpd.read_file(B, layer="priority_assets_ottewell"))[lambda d: d.asset_type == "catch basin"],
        "priority_pipes": pa[pa.asset_type == "pipe"],
        "nb_model": gpd.read_file(B, layer="nb_model"),
        "ottewell_boundary": nb[nb.neighbourhood_name == "Ottewell"][["neighbourhood_name", "geometry"]],
    }
    for name, df in layers.items():
        df = df.copy()
        for c in df.columns:
            if str(df[c].dtype) == "bool": df[c] = df[c].astype(int)
            if str(df[c].dtype) in ("int64", "Int64"): df[c] = df[c].astype("Int32")
        df.to_crs(4326).to_file(gdb, layer=name, driver="OpenFileGDB"); print(name, len(df))
    (ROOT / "outputs" / "agol").mkdir(parents=True, exist_ok=True)
    z = shutil.make_archive(str(work / "ponding_screening_agol.gdb"), "zip", root_dir=work, base_dir="ponding_screening.gdb")
    shutil.copyfile(z, ROOT / "outputs" / "agol" / "ponding_screening_agol.gdb.zip")
    print("MB", round((ROOT / "outputs" / "agol" / "ponding_screening_agol.gdb.zip").stat().st_size / 1e6, 2))

if __name__ == "__main__":
    main()
