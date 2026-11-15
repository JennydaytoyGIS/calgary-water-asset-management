# SOP: re-running the Project C workflow

Run from the `ProjectC` folder with Python 3.10+ and: `geopandas`, `networkx`, `scipy`, `matplotlib`, `mapclassify`, `ezdxf`, `requests`.

| Step | Command | Output | Check before moving on |
|---|---|---|---|
| 1. Download | `python scripts/c1_fetch.py` | `data/raw/*.geojson` | Record counts match the open data portal; note the retrieval date in `data/README.md` |
| 2. Standardize | `python scripts/c2_standardize.py` | `data/clean/edmonton_drainage.gpkg` | Printed system counts and year flags look plausible |
| 3. QA | `python scripts/c3_qc_rules.py` | `data/clean/edmonton_drainage_qa.gpkg`, `outputs/qa_*.csv` | Compare issue counts with the last report; a large change usually means the source changed |
| 4. Analysis | `python scripts/c4_analysis.py` | `docs/img/c4_*.png`, `outputs/c4_*.csv` | Charts render; totals by system match step 2 |
| 5. CAD export | `python scripts/c5_export_dxf.py Ottewell` | `cad/*.dxf`, `cad/*_readback.md` | Read-back says "all counts match" |
| 6. Publish | upload `outputs/agol/edmonton_drainage_agol.gpkg` to ArcGIS Online, overwrite the hosted layer | hosted feature layer | Review statuses already entered in the web app are exported first so they are not lost |

## Notes
- GeoPackages are built in a temporary folder and copied into `data/clean`, because SQLite can fail on synced or network folders.
- Thresholds are set at the top of `c3_qc_rules.py`. Record any change in `docs/decisions.md`.
- Before overwriting the hosted layer, export the `qa_issues` table with its review statuses and join them back by `issue_id` after the new run. Issue IDs follow rule and asset order, so a review should be joined on `rule` + `asset_id` if the data changed.
