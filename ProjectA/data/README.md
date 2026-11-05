# Project A: Data Inventory

Retrieved on **2026-11-04**. Nothing in `raw/` is ever edited; every later step reads from it, or from the API, and writes to a new place.

## Folder layout
```
data/
├── raw/
│   ├── opendata_calgary/   # full CSV exports from Open Calgary; geometry is stored as WKT in EPSG:4326
│   ├── osm/                # OpenStreetMap extract (care facilities, hospitals)
│   └── legacy_588/         # community age-vulnerability layer from the original GEOG 588 water-main project
├── interim/                # the same raw data, converted to one GeoPackage with no other changes (EPSG:4326)
└── processed/              # cleaned, projected, joined and scored outputs, written by FME, QGIS or pandas
../refs/                    # benchmark reports and literature used for parameters
```

## Sources
| File | Dataset (Open Calgary ID) | Rows | Use |
|---|---|---|---|
| Public_Water_Main.csv | Public Water Main (`w6h9-w33i`) | 60,740 | Asset register: material, diameter, install year, length, pressure zone, `globalid` |
| Water_Main_Breaks.csv | Water Main Breaks (`dpcu-jr23`) | 37,558 | Failure history, 1956-01-01 to 2026-08-23 → LoF |
| Community_District_Boundaries.csv | Community District Boundaries (`surr-xmvs`) | 313 | Reporting units |
| Census_by_Community_2019.csv | Census by Community 2019 (`rkfr-buzb`) | 306 | Population and age structure → vulnerability (CoF) |
| Schools.csv | Schools (`fd9t-tdn2`) | 506 | Critical facilities (CoF) |
| Fire_Stations.csv | Fire Stations (`cqsb-2hhg`) | 43 | Critical facilities (CoF) |
| Community_Services.csv | Community Services (`x34e-bcjz`) | 213 | Hospitals, PHS clinics and similar sites (CoF) |
| Hydrology.csv | Hydrology (`47bt-eefd`) | 4,702 | Rivers and water bodies → proximity (CoF) |
| Street_Centreline.csv | Street Centreline (`4dx8-rtm5`) | 120,614 | Road class (`ctp_class`) → traffic impact (CoF) |
| osm/OSM_CoF_facilities_Calgary.geojson | OpenStreetMap via the Overpass API | 57 | Nursing homes, assisted living, hospitals (CoF). © OpenStreetMap contributors, ODbL |
| legacy_588/community_age_vulnerability_2019.gpkg | Own GEOG 588 project (built from Census by Community 2019) | 306 | `Age_Vuln_Pct`. Check how it was defined before reusing it. |

Licence: Open Government Licence – City of Calgary. OSM data is under the ODbL.

## How to refresh
- **Full table.** Use `https://data.calgary.ca/api/views/<ID>/rows.csv?accessType=DOWNLOAD`. It returns every row, with no row limit.
- **Filtered or paged data.** Use the SODA API: `https://data.calgary.ca/resource/<ID>.json?$limit=50000&$offset=0&$order=:id`. Add `$where=` or `within_box(...)` to filter. This is what the FME pipeline (step A1) will call.
- **Column definitions.** These come from `https://data.calgary.ca/api/views/<ID>.json`, under `columns`.

## Data checks (2026-11-04)
**Water mains**
- **Length.** The 60,740 segments total 5,418.8 km.
- **Status.** 60,356 ACTIVE, 382 INACTIVE, 2 PLANNED.
- **Material codes are not decoded yet.** By count: PVC 33,654, CI 7,806, YDI 5,683, PDI 3,979, ST 2,290, PVCG 1,835, CON 1,391, DI 1,055, AC 628, PE 550, CU 526, YUDI 332, and others. Meanings such as YDI, PDI and YUDI need to be confirmed against City metadata.
- **Year.** Ranges from 1900 to 2033. 2 records are later than 2026, and 1900 may be a placeholder value (to check).
- **Diameter.** 14 records have a diameter ≤ 0.
- **Pressure zone.** `P_ZONE` is empty for 1,466 records.
- **Duplicates.** No duplicate `GLOBALID` values.

**Breaks**
- **Status.** 15,303 ACTIVE and 22,255 RETIRED. Most breaks happened on mains that have since been replaced, so they are no longer in the asset register (survivorship bias).
- **Break type codes are not decoded yet.** The codes include A, G, D, CG, AC, E and others.
- **Recent history.** 2,243 breaks since 2016-01-01.

**Linking the two tables.** There is no shared key between mains and breaks, so they have to be joined spatially (step A1 ③).
