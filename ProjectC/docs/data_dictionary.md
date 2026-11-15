# Data dictionary (standardized layers, C2)

GeoPackage `data/clean/edmonton_drainage.gpkg`, coordinate system **NAD83 / Alberta 3TM ref. merid. 114 W (EPSG:3776)**, units metres.

## Common fields (all asset layers)
| Field | Type | Description |
|---|---|---|
| `asset_id` | text | Stable ID created in this project (`PIPE-`, `MH-`, `CB-`, `CBL-`, `OUT-`, `PS-`, `SWM-` + 6 digits). The open data has no asset ID. IDs are assigned by system and location, so they repeat on re-runs of the same data. |
| `system` | text | STORM, SANITARY, COMBINED or FOUNDATION DRAIN (source field `type`, trimmed, upper case) |
| `year_raw` | integer | Construction year as published |
| `year_flag` | text | `valid`, `placeholder_0`, `placeholder_9999`, `missing`, `out_of_range` (before 1900 or after 2026) |
| `year_built` | integer | `year_raw` when the flag is `valid`, otherwise empty |
| `neighbourhood_name` | text | As published; when empty, filled from the 2019 neighbourhood polygons |
| `nb_source` | text | `source` or `filled_2019_boundaries` |
| `road_name` | text | As published |
| `ward_name`, `neighbourhood_id` | text | As published |
| `pilot` | text | `Ottewell`, `Terwillegar Towne`, or empty (outside the pilot areas) |

## Layer-specific fields
| Layer | Field | Description |
|---|---|---|
| pipes, cb_leads | `length_m` | 2D length in metres |
| pipes, cb_leads | `n_parts` | Number of parts in the source geometry (all pipes were single part and were converted to LineString) |
| manholes, catch_basins | `rim_elev` | Rim elevation in metres, as published |
| manholes, catch_basins | `rim_flag` | `valid`, `missing`, `zero_or_near_zero` (below 1 m) |
| contours_pilot | `elevation` | Contour elevation in metres (0.5 m interval, 2019) |
| pilot_areas | `pilot` | Pilot name |

## QA layers (`data/clean/edmonton_drainage_qa.gpkg`)
| Layer | Field | Description |
|---|---|---|
| qa_issues | `issue_id` | `QA-` + 6 digits, ordered by rule and asset |
| qa_issues | `rule`, `rule_name`, `severity` | See `docs/qa_rules.md` |
| qa_issues | `asset_id`, `asset_class`, `system` | The asset the issue belongs to |
| qa_issues | `detail`, `value` | Plain-language description and the measured value (distance, elevation difference, length or group size) |
| qa_issues | `review_status`, `review_note` | Filled in by reviewers in the web app; starts as `Not reviewed` |
| qa_issues | `run_date` | Date of the QA run |
| pipes_network | `component`, `component_pipes`, `component_terminal` | Connected group the pipe belongs to, its size, and whether it reaches an outfall, pump station or pond |
| neighbourhood_summary | `pipe_km`, `combined_km`, `combined_share`, `median_year`, `issues_med_high`, `issues_all`, `issues_per_km` | Per 2019 neighbourhood polygon (C4) |
