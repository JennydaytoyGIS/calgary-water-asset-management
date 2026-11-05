# Data Dictionary: Project B

Field lists were read from the live hosted layers on 2026-11-02.

Dates are stored in UTC. Local time is Alberta Time (UTC-6): Alberta stopped changing clocks on 2026-11-01.

Every hosted layer also has system fields:
- object ID and `GlobalID`
- editor tracking: `CreationDate`, `Creator`, `EditDate`, `Editor`

They are not repeated in the tables below. Allowed values (coded-value domains) are listed where the layer enforces them.

## AM_Hydrants (asset register)
- One point per hydrant: 114 features. Coordinate system: Web Mercator (WKID 102100).
- Editing: update attributes only. Photo attachments are on.

| Field | Type | Source | Description / allowed values |
|---|---|---|---|
| `asset_id` | String | Derived | Readable ID `HYD-<MON/PKD/POI>-NNN`, numbered north to south within each community |
| `city_globalid` | String | City | `globalid` from the City dataset, renamed to avoid clashing with the ArcGIS `GlobalID` field |
| `community` | String | City (boundaries) | Montgomery, Parkdale or Point McKay, found by point-in-polygon |
| `comm_code` | String | City (boundaries) | Community code |
| `owner` | String | City | Owner as published by the City |
| `status` | String | City | Status as published by the City |
| `rotation` | Double | City | Symbol rotation as published by the City |
| `longitude`, `latitude` | Double | City | WGS84 coordinates |
| `breaks_200m_since2016` | Integer | Derived | Water-main breaks within 200 m since 2016-01-01 (Water Main Breaks dataset) |
| `nearest_break_m` | Integer | Derived | Distance to the nearest break since 2016, in metres |
| `inspect_priority` | String | Derived | `High` (3 or more breaks), `Medium` (1–2), `Low` (0) |
| `insp_status` | String | Workflow | `Not inspected`, `Assigned`, `Inspected - OK`, `Inspected - Defect`, `Inaccessible` |
| `last_inspect_date` | Date | QC write-back | Date of the latest inspection that passed QC |
| `last_condition` | Integer | QC write-back | `1`–`5` (see the SOP condition scale); blank if not inspected or inaccessible |
| `last_insp_origin` | String | QC write-back | `Field test` or `Simulated` |
| `data_source` | String | Derived | Citation of the source dataset |

## AM Hydrant Visual Inspection (Survey123 layer)
- One point per inspection visit. Coordinate system: WGS84 (WKID 4326).
- Attachments are on (defect photos).
- Two views exist: `_form` for submitting and `_results` for viewing.

| Field | Type | Question / description | Allowed values |
|---|---|---|---|
| `asset_id` | String | Asset ID, pre-filled from the task pop-up | – |
| `task_id` | String | Task ID: the GlobalID of the Field Maps task | – |
| `inspect_date` | Date | Inspection date | – |
| `accessible` | String | Is the hydrant accessible? | `Yes`, `No` |
| `access_issue` | String | Reason not accessible | `Vehicle parked`, `Snow or ice`, `Vegetation`, `Fence or structure`, `Construction`, `other` |
| `access_other` | String | Other – reason not accessible | free text |
| `obstructions` | String | Obstructions around the hydrant | multiple choice, stored comma-separated (e.g. `None`, `Vegetation`) |
| `obstr_other` | String | Other – obstructions | free text |
| `paint` | String | Paint and markings | `Good`, `Faded`, `Peeling or rust`, `Missing` |
| `damage` | String | Leaning or damage | `None`, `Slight lean`, `Visible damage` |
| `caps` | String | Caps and outlet covers | `All present`, `One or more missing`, `Cannot tell` |
| `leakage` | String | Signs of leakage | `None`, `Pooling water`, `Ice build-up`, `Wet ground at base` |
| `cond_rating` | String | Overall condition (named `cond_rating` because `condition` is a reserved word) | `1`–`5` |
| `defect_found` | String | Defect found? | `Yes`, `No` |
| `defect_type` | String | Defect type | multiple choice, stored comma-separated: `Damaged`, `Leaking`, `Missing_caps`, `Obstructed`, `Paint_markings`, `Leaning`, `defect_other` |
| `defect_other` | String | Other – defect type | free text |
| `notes` | String | Notes. Simulated records start with "SIMULATED". | free text |
| `data_origin` | String | Data origin | `Field test`, `Simulated` |
| `qc_status` | String | Set by QC | `Pass`, `Fail` |
| `qc_notes` | String | Set by QC: the rules that failed | e.g. `R2 same-day duplicate` |

Photo attachments are stored with the record; the attachment keyword is the name of the photo question:

| Keyword | Question | Notes |
|---|---|---|
| `field_17` | General hydrant photo | The default name from the web designer was never changed. Planned rename: `hydrant_photo`. |
| `defect_photo` | Defect photo, shown when Defect found = Yes | QC rule R5 looks for this keyword on field-test records |

## AM_Hydrant_Tasks (Field Maps Tasks)
- Task-enabled point layer with photo attachments.
- The `esritask_*` fields are the standard Field Maps task schema. `asset_id` was added for this project.

| Field | Type | Description / allowed values |
|---|---|---|
| `asset_id` | String | Links the task to the hydrant in AM_Hydrants |
| `esritask_type` | Integer | Task type. The project uses *Routine visual inspection*. |
| `esritask_status` | Integer | `0` Unassigned, `1` Assigned, `2` In progress, `3` Completed |
| `esritask_priority` | Integer | Coded `0`–`4`. The project uses *High* for every task. |
| `esritask_assignee` | String | Field Maps user |
| `esritask_duedate` | Date | Due date (2026-11-20 for the pilot) |
| `esritask_description` | String | Hydrant, community and why it was prioritized |
| `esritask_notes` | String | Completion notes. Simulated completions are labelled "SIMULATED". |

## AM_WorkOrders (hosted table; stands in for a CMMS)
| Field | Type | Description / allowed values |
|---|---|---|
| `wo_id` | String | `WO-2026-NNNN` |
| `asset_id` | String | Hydrant ID |
| `community` | String | From the register |
| `inspection_guid` | String | GlobalID of the inspection that raised it. One work order per inspection; also used to avoid duplicates on rerun. |
| `inspect_date` | Date | Inspection date |
| `cond_rating` | Integer | Condition at that inspection |
| `defect_type` | String | Defect types from the inspection |
| `wo_priority` | String | `Urgent`, `High`, `Normal` (rule in SOP §8) |
| `wo_status` | String | `Open`, `In progress`, `Closed` |
| `created_date` | Date | When the work order was raised |
| `data_origin` | String | Copied from the inspection (`Field test` / `Simulated`) |
| `notes` | String | "Raised automatically from QC-passed inspection" |

## Relationships
```
AM_Hydrants.asset_id 1 ── * AM_Hydrant_Tasks.asset_id
AM_Hydrants.asset_id 1 ── * Inspection.asset_id
AM_Hydrant_Tasks.GlobalID 1 ── * Inspection.task_id
Inspection.GlobalID 1 ── 0..1 AM_WorkOrders.inspection_guid
```
These links are maintained by the scripts and by the Survey123 link that pre-fills the form. They are not enforced as database relationship classes.
