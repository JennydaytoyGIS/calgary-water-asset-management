"""
Build AM_Hydrants.csv (Project B asset register) from City of Calgary Open Data.

Inputs (data/, downloaded 2026-10-31 via SODA API):
  Water Hydrants_437.csv           Water Hydrants (5qgc-b482), 437 rows in a bounding box around the pilot area
  Water Main Breaks.csv              Water Main Breaks (dpcu-jr23) since 2016-01-01, same bounding box
  Community District Boundaries.csv  Community District Boundaries (surr-xmvs): MONTGOMERY, PARKDALE, POINT MCKAY
Steps:
  1. Keep hydrants that fall inside the three community polygons (point-in-polygon)
  2. Give each a readable asset_id (HYD-<COMM>-NNN, numbered north -> south)
  3. Count main breaks within 200 m since 2016 and the distance to the nearest one
  4. Set inspection priority from the break count (rule documented in docs/decisions.md)
No synthetic attributes: install year / model are not published by the City.
"""
import csv, math, re, os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
R = 6371000.0
NAMES = {"MONTGOMERY": "Montgomery", "PARKDALE": "Parkdale", "POINT MCKAY": "Point McKay"}

def parse_point(s):  # "POINT (-114.15 51.06)"
    x, y = re.findall(r"-?\d+\.?\d*", s)[:2]
    return float(x), float(y)

def parse_multipolygon(wkt):  # -> [ [ring, hole, ...], ... ]
    body = wkt[wkt.index("(") :]
    polys = []
    for poly in re.findall(r"\(\((.*?)\)\)", body.replace(") ,", "),").replace(", (", ",(")):
        rings = []
        for ring in poly.split("),("):
            pts = [tuple(map(float, p.split())) for p in ring.strip("() ").split(",")]
            rings.append(pts)
        polys.append(rings)
    return polys

def pip(pt, ring):
    x, y = pt; inside = False
    for i in range(len(ring)):
        x1, y1 = ring[i - 1]; x2, y2 = ring[i]
        if (y2 > y) != (y1 > y) and x < (x1 - x2) * (y - y2) / (y1 - y2) + x2:
            inside = not inside
    return inside

def in_multipolygon(pt, mp):
    return any(pip(pt, p[0]) and not any(pip(pt, h) for h in p[1:]) for p in mp)

def dist_m(a, b):
    lat = math.radians((a[1] + b[1]) / 2)
    dx = math.radians(b[0] - a[0]) * math.cos(lat) * R
    dy = math.radians(b[1] - a[1]) * R
    return math.hypot(dx, dy)

comms = {}
with open(os.path.join(DATA, "Community District Boundaries.csv"), newline="") as f:
    for r in csv.DictReader(f):
        comms[r["name"]] = (r["comm_code"], parse_multipolygon(r["multipolygon"]))

breaks = []
with open(os.path.join(DATA, "Water Main Breaks.csv"), newline="") as f:
    for r in csv.DictReader(f):
        breaks.append((parse_point(r["point"]), r["break_date"][:10]))

rows = []
with open(os.path.join(DATA, "Water Hydrants_437.csv"), newline="") as f:
    for r in csv.DictReader(f):
        pt = parse_point(r["point"])
        for name, (code, mp) in comms.items():
            if in_multipolygon(pt, mp):
                d = sorted(dist_m(pt, b[0]) for b in breaks)
                n200 = sum(1 for x in d if x <= 200)
                rows.append({
                    "community": NAMES.get(name, name.title()), "comm_code": code,
                    "city_globalid": r["globalid"], "owner": r["owner_cd"], "status": r["status_ind"],
                    "rotation": r["rotation"], "longitude": f"{pt[0]:.7f}", "latitude": f"{pt[1]:.7f}",
                    "breaks_200m_since2016": n200, "nearest_break_m": round(d[0]) if d else "",
                })
                break

def priority(n):
    return "High" if n >= 3 else ("Medium" if n >= 1 else "Low")

out = []
for code in sorted({r["comm_code"] for r in rows}):
    grp = sorted([r for r in rows if r["comm_code"] == code], key=lambda r: (-float(r["latitude"]), float(r["longitude"])))
    for i, r in enumerate(grp, 1):
        out.append({"asset_id": f"HYD-{code}-{i:03d}", **r,
                    "inspect_priority": priority(r["breaks_200m_since2016"]),
                    "insp_status": "Not inspected", "last_inspect_date": "", "last_condition": "",
                    "data_source": "City of Calgary Open Data: Water Hydrants (5qgc-b482); Water Main Breaks (dpcu-jr23); retrieved 2026-10-31"})

cols = ["asset_id", "city_globalid", "community", "comm_code", "owner", "status", "rotation", "longitude", "latitude",
        "breaks_200m_since2016", "nearest_break_m", "inspect_priority", "insp_status", "last_inspect_date",
        "last_condition", "data_source"]
with open(os.path.join(DATA, "AM_Hydrants.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(out)

from collections import Counter
print("hydrants in pilot area:", len(out), dict(Counter(r["community"] for r in out)))
print("breaks since 2016 in bbox:", len(breaks))
print("priority:", dict(Counter(r["inspect_priority"] for r in out)))
print("breaks_200m distribution:", sorted(Counter(r["breaks_200m_since2016"] for r in out).items()))
