"""C6: Package the layers for ArcGIS Online as a zipped file geodatabase (kept under 10 MB).

Layers:
  qa_issues               all QA issues (citywide), with review fields
  neighbourhood_summary   per-neighbourhood metrics from C4 (citywide)
  pipes_pilot             pipes in the two pilot areas, with connectivity fields
  manholes_pilot, catch_basins_pilot
  outfalls, pump_stations, swm_facilities, pilot_areas
  pipes_citywide          all pipes with system and year only (map context)
Output: outputs/agol/edmonton_drainage_agol.gdb.zip
"""
import pathlib
import shutil
import tempfile
import geopandas as gpd

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "clean" / "edmonton_drainage.gpkg"
QA = ROOT / "data" / "clean" / "edmonton_drainage_qa.gpkg"
OUT = ROOT / "outputs" / "agol"


def main():
    work = pathlib.Path(tempfile.mkdtemp())
    gdb = work / "edmonton_drainage.gdb"
    layers = {
        "qa_issues": gpd.read_file(QA, layer="qa_issues").drop(columns=["run_date"]),
        "neighbourhood_summary": gpd.read_file(QA, layer="neighbourhood_summary"),
        "pipes_pilot": gpd.read_file(QA, layer="pipes_network").query("pilot.notna()", engine="python")[
            ["asset_id", "system", "year_built", "year_flag", "length_m", "neighbourhood_name", "road_name", "pilot", "component", "component_pipes", "component_terminal", "geometry"]],
        "manholes_pilot": gpd.read_file(SRC, layer="manholes").query("pilot.notna()", engine="python")[
            ["asset_id", "system", "year_built", "year_flag", "rim_elev", "rim_flag", "neighbourhood_name", "road_name", "pilot", "geometry"]],
        "catch_basins_pilot": gpd.read_file(SRC, layer="catch_basins").query("pilot.notna()", engine="python")[
            ["asset_id", "system", "year_built", "rim_elev", "rim_flag", "pilot", "geometry"]],
        "outfalls": gpd.read_file(SRC, layer="outfalls")[["asset_id", "system", "year_built", "neighbourhood_name", "geometry"]],
        "pump_stations": gpd.read_file(SRC, layer="pump_stations")[["asset_id", "system", "year_built", "neighbourhood_name", "geometry"]],
        "swm_facilities": gpd.read_file(SRC, layer="swm_facilities")[["asset_id", "system", "year_built", "neighbourhood_name", "geometry"]],
        "pilot_areas": gpd.read_file(SRC, layer="pilot_areas"),
        "pipes_citywide": gpd.read_file(SRC, layer="pipes")[["asset_id", "system", "year_built", "geometry"]],
    }
    for name, df in layers.items():
        df["component_terminal"] = df["component_terminal"].astype(int) if "component_terminal" in df else None
        df = df.drop(columns=[c for c in df.columns if df[c].isna().all() and c != "geometry"])
        for c in df.columns:
            if str(df[c].dtype) in ("int64", "Int64"):
                df[c] = df[c].astype("Int32")
        df.to_crs(4326).to_file(gdb, layer=name, driver="OpenFileGDB")
        print(f"{name}: {len(df)}")
    OUT.mkdir(parents=True, exist_ok=True)
    z = shutil.make_archive(str(work / "edmonton_drainage_agol.gdb"), "zip", root_dir=work, base_dir="edmonton_drainage.gdb")
    shutil.copyfile(z, OUT / "edmonton_drainage_agol.gdb.zip")
    print("size MB", round((OUT / "edmonton_drainage_agol.gdb.zip").stat().st_size / 1e6, 2))


if __name__ == "__main__":
    main()
