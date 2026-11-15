# Data gap report: is the open drainage data ready for a Utility Network or a hydraulic model?

Edmonton drainage network, City of Edmonton Open Data retrieved 2026-11-14. Prepared as independent portfolio work.

## 1. Purpose
Two common next steps for a drainage dataset are moving it into the **ArcGIS Utility Network**, where connectivity is enforced and the network can be traced, and building a **hydraulic model** for capacity and flooding studies. Both need more than locations. This report sets out what the published data supports, what it is missing, and the order in which the gaps would be closed.

## 2. What the data already supports
| Need | Status | Evidence |
|---|---|---|
| Location of pipes and structures | Good | 134,767 pipes, 107,739 manholes, 65,928 catch basins and their leads, 262 outfalls, 109 pump stations, 372 ponds |
| System type (storm, sanitary, combined) | Good | Present on every asset; 97 storm/sanitary conflicts to review (R3) |
| Geometric connectivity | Mostly good | 98% of pipe ends meet a node or another pipe; 4,906 dangling ends (R1) and 437 pipes in small isolated groups (R9) to review |
| Construction year | Mostly good | 98% of assets have a usable year; 7,856 placeholders or blanks (R4) |
| Rim elevation | Mostly good | 1,423 manholes without one; a systematic 1–2 m offset in one pilot area (R7) |

## 3. What is missing
| Missing attribute | Needed for | Impact |
|---|---|---|
| Unique, persistent asset ID | Both | Edits and inspections cannot be tied back to the City's records. This project created its own IDs for review only. |
| Pipe diameter and shape | Both | No capacity, velocity or flow calculation is possible |
| Pipe material | Both | Needed for roughness in a model and for asset groups and renewal planning |
| Invert elevations (up and downstream) | Hydraulic model; Utility Network attributes | Without inverts there is no slope and no flow direction |
| Flow direction | Utility Network tracing | Upstream and downstream traces cannot be run |
| Manhole depth or invert | Hydraulic model | Surcharge and flooding depth cannot be assessed |
| Lifecycle status (active, abandoned, proposed) | Utility Network | Abandoned pipes may be inflating dangles and duplicates |
| Catchment areas and connections | Hydraulic model | Inflows cannot be assigned to nodes |

The published layers are a location and type reference, not a full engineering dataset. The City's internal records very likely hold some of these attributes; this report concerns only what is public.

## 4. Recommended order of work
1. **Review high severity issues** (R1, R3) with the web app, starting with dangling ends more than 5 m from a node and every storm/sanitary conflict.
2. **Confirm the Terwillegar Towne elevation offset** against as-built drawings or a small survey sample before using any rim elevation in a model.
3. **Clean geometry**: remove duplicates (R5), merge or remove very short pipes (R6), connect or retire orphan nodes (R2).
4. **Add attributes from records**: diameter, material, inverts and lifecycle status, starting with trunk mains and the combined sewer areas, where most pipes are 60 years or older.
5. **Load into the Utility Network** once inverts or flow direction exist, and use its connectivity rules to catch anything the checks here missed.

## 5. Where to start: combined sewer areas
82% of combined sewer length was built 60 or more years ago, against about 21% of sanitary and 24% of storm sewers. Combined pipes make up most of the network in a group of older neighbourhoods; Garneau, Forest Heights, Holyrood, Idylwylde and Highlands are all above 80% combined by length. These areas are where renewal and separation decisions are most likely, so complete, connected data there brings the most value first.

## 6. Limits of this assessment
- Checks use 2D geometry and published attributes only, so every issue means "needs review", not "confirmed error".
- Contours used for the elevation check are from 2019.
- Neighbourhood summaries use the 2019 boundaries, the newest polygons published; newer neighbourhoods are counted within the 2019 polygon that contains them.
