# QA rules (C3)

Script: `scripts/c3_qc_rules.py`. Distances in metres (EPSG:3776). Each issue is stored as a point so it can be reviewed on a map. Results are identical on re-runs of the same data.

| Rule | Severity | What is checked | Threshold | Why it matters |
|---|---|---|---|---|
| R1 Dangling pipe end | High | A pipe end has no manhole, catch basin, outfall or pump station and no other pipe within the tolerance | 0.5 m | A network model or Utility Network trace stops at a break in connectivity |
| R2 Orphan node | Medium | A manhole with no pipe, or a catch basin with no lead or pipe, within the tolerance | 0.5 m | Usually a missing pipe or a misplaced point |
| R3 Storm/sanitary conflict | High | A storm pipe end meets only sanitary assets (or the reverse). Combined assets are treated as compatible with both | 0.5 m | Either a drawing error or a possible cross-connection, which a utility would want to know about |
| R4 Construction year | Low | Year is 0, 9999, missing, or outside 1900–2026 | — | Age drives renewal planning; placeholders look like real values in summaries |
| R5 Duplicate pipe | Medium | Identical geometry recorded twice (either direction) | exact | Double-counts length and confuses network tracing |
| R6 Very short pipe | Low | Pipe shorter than the threshold | 1.0 m | Often a digitizing artefact |
| R7 Rim elevation | Medium | Rim elevation missing or near zero, or more than the threshold away from the ground surface interpolated from 0.5 m contours (pilot areas) | 1.0 m | Rim elevations feed hydraulic models and surcharge checks |
| R8 Names missing | Low | Neighbourhood or road name empty after standardization | — | Hampers work orders and reporting |
| R9 Isolated sub-network | Medium | A connected group of fewer than 5 pipes that reaches no outfall, pump station or stormwater pond | 5 pipes | Flows from these pipes have nowhere to go in the data |

## How the thresholds were set
- **0.5 m tolerance.** 83% of the 269,534 pipe ends sit on a node (within 1 cm). Of the rest, 39,638 end on another pipe; the 4,906 that meet nothing are a median of 14 m from the nearest node, so a small tolerance separates real gaps from rounding.
- **Rim elevation 1.0 m.** In the pilot areas, the difference between rim and interpolated ground has a median of about −0.1 m, and half of all values fall between about −0.25 m and +0.07 m, for both manholes and catch basins, so 1.0 m is well outside normal variation.
- **Connectivity.** Pipes are linked only through their ends (to a node, or ending on another pipe). Pipes that merely cross in plan view are not joined, because storm and sanitary mains often cross at different depths.

## Limits
These rules use geometry and attributes only. Without depth, invert or flow direction, an issue means **"needs review"**, not "confirmed error". Some dangling ends are real (stubs left for future connections, pipes that continue outside the city's data).
