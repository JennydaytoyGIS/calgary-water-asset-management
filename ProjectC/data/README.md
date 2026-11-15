# Data inventory (C1)

All layers come from **City of Edmonton Open Data** (Open Government Licence – City of Edmonton), retrieved **2026-11-14** through the Socrata (SODA) API. Raw and processed files are not stored in this repository; run `python scripts/c1_fetch.py` to download them again into `data/raw/`.

| Layer | Dataset ID | Records | Geometry | Fields used | Notes |
|---|---|---|---|---|---|
| Drainage pipe segments | `bh8y-pn5j` | 134,767 | line | type, year_const, neighbourhood_name, road_name | storm 73,292; sanitary 46,494; combined 13,299; foundation drain 1,682 |
| Drainage manholes | `6waz-yxqq` | 107,739 | point | type, year_const, rim_elev | 1,423 without rim elevation |
| Catch basins | `5xxs-hqn7` | 65,928 | point | type, year_const, rim_elev | |
| Catch basin leads | `jufi-ds3w` | 69,133 | line | type, year_const | |
| Outfalls | `gpxt-s37s` | 262 | point | type, year_const | discharge to creeks and the river |
| Pump stations | `yhez-gf32` | 109 | point | type, year_const | |
| Stormwater management facilities | `72ee-mmkx` | 372 | polygon | type, year_const | ponds |
| Neighbourhood boundaries 2019 | `xu6q-xcmj` | 399 | polygon | name | newest polygon version published |
| Contour lines (0.5 m) | `n6cj-24tp` | 5,017 in pilot areas | line | elevation | 2019; pulled only for the two pilot areas |

**Pilot areas** (WGS84 boxes = neighbourhood extent plus about 280 m):
- Ottewell: N 53.543676, W -113.446940, S 53.518894, E -113.414549
- Terwillegar Towne: N 53.460054, W -113.594095, S 53.441287, E -113.561513

## What the open data does not contain
No pipe diameter, material, invert or depth, slope, flow direction, condition, or a unique asset ID. These limits shape what this project can and cannot check; see `docs/data_gap_report.md`.

## Processed files (not in the repository)
- `data/clean/edmonton_drainage.gpkg`: standardized layers (C2), EPSG:3776
- `data/clean/edmonton_drainage_qa.gpkg`: `qa_issues`, `pipes_network`, `neighbourhood_summary` (C3, C4)

## Added for the ponding screening (A) and model (B), retrieved 2026-11-15

| Layer | Dataset ID | Records | Geometry | Fields used | Notes |
|---|---|---|---|---|---|
| 311 Requests | `q7ua-agfg` | 5,489 "Ponding" requests, 2023–2026 | none (neighbourhood only) | date_created, service_description, neighbourhood_id | Residential road, alley and sidewalk ponding. Located only by neighbourhood. The model uses May–September (2,361); March snowmelt peaks are left out |
| 2021 Federal Census: Population | `eg3i-f4bj` | 278 neighbourhoods | none | neighbourhood_number, total_population | Population density, to test whether reports follow people rather than water |
| Building Footprint | `6n9r-ddf8` | 8,613 in the Ottewell box | polygon | geometry | Roof-lines as of May 2017 |
| Contour Lines (0.5 m) | `n6cj-24tp` | 72,190 lines citywide | line | elevation | Only every 2.5 m pulled citywide, for the 20 m terrain surface (c8); the 0.5 m lines are used in Ottewell (c7) |

**Not in the open data:** impervious surface, pipe capacity, and rainfall by area. Spot elevations exist but only mark hilltops and pits, so they were not used.

## Further processed files (not in the repository)
- `data/clean/edmonton_bluespots.gpkg`: `bluespots_ottewell`, `priority_assets_ottewell` (c7)
- `outputs/dem_ottewell_1m.tif`: 1 m surface for Ottewell (c7)
- `outputs/c8_terrain_by_neighbourhood.csv`, `outputs/c9_*.csv`: terrain factors and model results
- `outputs/agol/ponding_screening_agol.gdb.zip`: layers published to ArcGIS Online (c12)

