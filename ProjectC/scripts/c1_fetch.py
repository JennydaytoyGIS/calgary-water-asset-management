"""C1: Download the City of Edmonton drainage network from its open data (SODA) API.

Writes one GeoJSON per layer to data/raw/. Re-running replaces the files.
The copies used in this project were retrieved on 2026-11-14 through the same
endpoints (see data/README.md).

Usage:  python scripts/c1_fetch.py
"""
import json
import pathlib
import requests

BASE = "https://data.edmonton.ca/resource/{id}.geojson"
RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
PAGE = 50000

LAYERS = {
    "edm_drainage_pipes": "bh8y-pn5j",
    "edm_drainage_manholes": "6waz-yxqq",
    "edm_drainage_catch_basins": "5xxs-hqn7",
    "edm_drainage_cb_leads": "jufi-ds3w",
    "edm_drainage_outfalls": "gpxt-s37s",
    "edm_drainage_pump_stations": "yhez-gf32",
    "edm_drainage_swm_facilities": "72ee-mmkx",
    "edm_neighbourhoods_2019": "xu6q-xcmj",
}

# Contours (0.5 m) are large, so only the two pilot neighbourhoods are pulled,
# with a margin of about 280 m: (north, west, south, east) in WGS84.
CONTOURS_ID = "n6cj-24tp"
PILOT_BOXES = {
    "edm_contours_ottewell": (53.543676, -113.446940, 53.518894, -113.414549),
    "edm_contours_terwillegar_towne": (53.460054, -113.594095, 53.441287, -113.561513),
}


def fetch(dataset_id, where=None):
    features, offset = [], 0
    while True:
        params = {"$limit": PAGE, "$offset": offset, "$order": ":id"}
        if where:
            params["$where"] = where
        r = requests.get(BASE.format(id=dataset_id), params=params, timeout=120)
        r.raise_for_status()
        batch = r.json()["features"]
        features.extend(batch)
        if len(batch) < PAGE:
            return {"type": "FeatureCollection", "features": features}
        offset += PAGE


def save(name, fc):
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / f"{name}.geojson").write_text(json.dumps(fc))
    print(f"{name}: {len(fc['features'])} features")


if __name__ == "__main__":
    for name, dataset_id in LAYERS.items():
        save(name, fetch(dataset_id))
    for name, (n, w, s, e) in PILOT_BOXES.items():
        save(name, fetch(CONTOURS_ID, f"within_box(the_geom, {n}, {w}, {s}, {e})"))
