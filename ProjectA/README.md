# Project A: Calgary Water Main Mini AMP (in progress)

**Question.** Which water main segments should Calgary renew first over the next ten years, what would that cost, and how large is the gap against a fixed annual budget?

**Why this project.** The original Water Main Risk project mapped risk as a continuous surface and summarized it by community. That shows where risk concentrates, but an asset management plan works pipe by pipe. This project:
- scores each pipe segment instead of an area,
- uses the recorded break history for likelihood of failure,
- models consequence of failure separately,
- adds lifecycle cost, levels of service and a funding gap,
- and builds the data processing as a repeatable pipeline.

## Status (2026-11-05)
**Done: A0, data inventory.**
- Downloaded the asset register (60,740 water main segments, 5,418.8 km), 37,558 recorded breaks (1956 to 2026) and the consequence layers from Open Calgary and OpenStreetMap.
- Ran the first data checks: undecoded material and break codes, 1,466 records with no pressure zone, 14 records with a diameter of zero or less, and install years to verify. See [`data/README.md`](data/README.md).

**Planned steps**

| Step | Work | Tools |
|---|---|---|
| A1 | Data pipeline: pull mains and breaks from the Open Calgary (SODA) API, validate attributes and geometry into a data gap report, link each break to its nearest segment and count breaks per segment | FME Form |
| A2 | Likelihood of failure (LoF 1–5) from break rate (breaks / km / yr) and remaining useful life by material | Python (pandas), QGIS |
| A3 | Consequence of failure (CoF 1–5) from diameter, road class, nearby critical facilities, rivers and community vulnerability; AHP weights with sensitivity analysis | QGIS, Python |
| A3 | Risk = LoF × CoF, a 5 × 5 risk matrix and a critical asset list | Python (pandas) |
| A4 | Levels of service: three KPIs with targets | Excel |
| A5 | Replacement cost (length × unit cost by diameter), a 20-year renewal forecast and funding gap scenarios | Excel |
| A6 | Operations dashboard on ArcGIS Online | ArcGIS Online |
| A7 | Management dashboard | Power BI |
| A8 | A 3–4 page report in asset management plan format, including data limitations and an improvement plan | |

Every parameter (expected life by material, unit costs, thresholds and weights) will be recorded with its source, or marked as an assumption.

## Known limitations
- **No shared key between mains and breaks**, so breaks have to be joined spatially.
- **Survivorship bias.** Most recorded breaks happened on mains that have since been replaced, so they are no longer in the asset register.
- **Valve and inspection data are not public**, so there is no isolation analysis and no observed condition data.

## References
- City of Calgary, *2020 Infrastructure Status Report*
- City of Calgary, *2026 Corporate Asset Management Plan*, Appendix B
- Folkman, S. (2018). *Water Main Break Rates in the USA and Canada: A Comprehensive Study*. Utah State University.
