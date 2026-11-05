# SOP: Fire Hydrant Visual Inspection (Project B Pilot)

| | |
|---|---|
| Version | 1.0 (2026-11-02) |
| Scope | 114 hydrants in Montgomery, Parkdale and Point McKay (City of Calgary Open Data) |
| Applies to | Visual, walk-by inspections only. No flushing, no flow testing, and no operating of hydrants or valves. |
| Systems | ArcGIS Online: Field Maps (Tasks), Survey123, an ArcGIS Notebook for QC, and Dashboards |

> **Portfolio note.** This is a portfolio project, not a City of Calgary procedure. The condition scale and QC rules were written for this pilot. One person plays all the roles below.

## 1. Roles
| Role | Responsibility |
|---|---|
| Planner / GIS analyst | Sets inspection priority, creates and assigns tasks, and maintains the asset register (AM_Hydrants). |
| Field inspector | Does the visual inspection and submits one Survey123 record per hydrant visit. |
| Data steward (QC) | Runs QC, reviews failed records and runs the register write-back. |
| Maintenance supervisor | Reviews work orders, then schedules and closes them in the CMMS (AM_WorkOrders in this pilot). |

## 2. Before going out
1. **Planner: create the tasks.** Run `b4_create_tasks.py` to create a task for every hydrant with `inspect_priority = High`. Each task is:
   - type *Routine visual inspection*
   - status *Assigned*
   - priority *High*
   - assigned to the inspector, with a due date

   The same script sets those hydrants to `insp_status = Assigned` in the register.
2. **Inspector: prepare the phone.**
   - Open **ProjectB_Hydrant_Inspection_Map** in Field Maps and confirm the tasks appear under *Tasks*.
   - Check that the Survey123 app is installed and signed in.
   - If coverage is poor, download the map for offline use.
3. **Safety (all roles).**
   - Wear a high-visibility vest.
   - Stay on the sidewalk or boulevard, and don't stand in traffic lanes.
   - Don't touch, open or operate the hydrant.
   - Don't enter private property. If the hydrant can only be reached through private property, record it as *Not accessible*.

## 3. In the field
1. In Field Maps, open the task and set its status to **In progress**.
2. Tap **▶ Start inspection** in the task pop-up. Survey123 opens with three things already filled in:
   - **Asset ID**
   - **Task ID**
   - **location**

   Check that the asset ID matches the hydrant you are standing at.
3. Answer **Is the hydrant accessible?**
   - **No:** choose a *Reason not accessible*, add a photo if you can, and submit.
   - **Yes:** carry on with the steps below.
4. Record what you see, using the definitions in section 5:
   - obstructions
   - paint and markings
   - leaning or damage
   - caps and outlet covers
   - signs of leakage
5. Give an **Overall condition** from 1 to 5, using the scale in section 4.
6. **Defect found?** Answer *Yes* if anything needs maintenance. Then:
   - choose one or more **Defect types**
   - take at least one **defect photo**

   A condition of 4 or 5 must always come with a defect (QC rule R4).
7. Make sure **Data origin** is set to **Field test**. Records with `Simulated` are demo data only.
8. Submit the form. Return to Field Maps and set the task to **Completed**, adding a short note if useful.

## 4. Condition scale (overall rating)
| Rating | Label | Visual criteria (pilot definition) |
|---|---|---|
| 1 | Very good | Looks new. Paint intact, all caps present, upright, no leaks, clear surroundings. |
| 2 | Good | Minor cosmetic wear only, for example slightly faded paint. No defects. |
| 3 | Fair | Noticeable wear: faded or chipped paint, light surface rust or minor vegetation nearby. Still no defect that needs a work order. |
| 4 | Poor | At least one defect that needs maintenance: a leak, a missing cap, a slight lean, visible damage, or paint peeling or rusting badly. |
| 5 | Very poor | Several defects, or a defect that could affect fire-fighting use or safety. Examples: active leaking with pooling water, a clear lean, impact damage. |

Rate what is visible on the day. If you are unsure between two ratings, pick the worse one and explain in *Notes*.

## 5. Defect types
| Code | Meaning |
|---|---|
| `Damaged` | Visible physical damage, such as impact, cracking or broken parts |
| `Leaking` | Water pooling, ice build-up or wet ground at the base |
| `Missing_caps` | One or more outlet caps or covers missing |
| `Obstructed` | Vegetation, a structure, snow or other objects blocking access or visibility |
| `Paint_markings` | Peeling or rusting paint, or missing markings |
| `Leaning` | Hydrant not plumb |
| `defect_other` | Anything else. Describe it in *Other – Defect type*. |

## 6. QC (data steward)
Run `b6_qc_workorders.py` after each batch of submissions. It is safe to run more than once. Each inspection record gets `qc_status` (Pass/Fail) and `qc_notes`.

| Rule | Check | If it fails |
|---|---|---|
| R1 | `asset_id` exists in AM_Hydrants | Correct the asset ID and rerun QC |
| R2 | Only one inspection per asset per day, by Alberta Time (UTC-6). Later same-day records fail. | Delete the duplicate or keep the correct record |
| R3 | Accessible = Yes must have a condition rating | Ask the inspector, then fix the record |
| R4 | A condition of 4 or 5 must have Defect found = Yes | Ask the inspector: either the rating or the defect answer is wrong |
| R5 | A field-test record with a defect must have a defect photo | Get the photo, or downgrade the record after review |
| R6 | Accessible = No must have a reason | Ask the inspector, then fix the record |

Only records that **pass** QC update the register or raise work orders. Failed records stay in the inspection layer, flagged for review.

## 7. Register write-back
For each hydrant, the latest record that passed QC updates AM_Hydrants:
- `last_inspect_date`
- `last_condition`
- `last_insp_origin`
- `insp_status`:

| Inspection result | `insp_status` | `last_condition` |
|---|---|---|
| Not accessible | `Inaccessible` | left blank |
| Defect found | `Inspected - Defect` | the rating |
| No defect | `Inspected - OK` | the rating |

Hydrants with no passed inspection keep `Assigned` or `Not inspected`.

## 8. Work orders
A record that passes QC and has a defect or a condition of 4 or more creates one work order in **AM_WorkOrders**. It gets an ID of the form `WO-2026-NNNN` and status `Open`.

| Priority | Rule |
|---|---|
| Urgent | Condition 5, or the defect types include `Leaking` |
| High | Condition 4 |
| Normal | Any other defect |

The supervisor moves each work order through `Open → In progress → Closed`.

## 9. Monitoring and records
- **Dashboard.** **AM Hydrant Inspection Dashboard** shows the register status, the condition distribution, the map and open work orders.
- **QC reports.** Each QC run writes `qc_report.md` in the Notebook. A copy is kept in `docs/` with the date in the file name.
- **Simulated records.** These stay in the system, labelled `data_origin = Simulated`. They are never used as evidence of real asset condition.
