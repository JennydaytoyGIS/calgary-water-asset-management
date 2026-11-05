"""
B6a - Simulated inspection records for the dashboard demo (run in ArcGIS Notebook).
Every record is labelled data_origin = 'Simulated' and notes start with 'SIMULATED'.
Montgomery High-priority tasks are left open for the real field test (B5).
Also adds two deliberate QC test cases (an inconsistent rating and a same-day duplicate).
"""
from arcgis.gis import GIS
import random, datetime as dt
from zoneinfo import ZoneInfo

random.seed(42)
TZ = ZoneInfo("America/Edmonton")
gis = GIS("home"); me = gis.users.me.username
def find(title, typ="Feature Service"):
    return [i for i in gis.content.search(f'title:"{title}" owner:{me}', item_type=typ, max_items=50) if i.title == title][0]

hyd = find("AM_Hydrants").layers[0]
tasks = find("AM_Hydrant_Tasks").layers[0]
insp = find("AM Hydrant Visual Inspection").layers[0]

if insp.query(where="data_origin='Simulated' AND notes LIKE 'SIMULATED%'", return_count_only=True) > 0:
    raise SystemExit("Simulated records already exist - not adding again")

H = {f.attributes["asset_id"]: f for f in hyd.query(where="1=1", out_fields="asset_id,community,inspect_priority", out_sr=4326).features}
T = {f.attributes["asset_id"]: f.attributes for f in tasks.query(where="1=1", out_fields="OBJECTID,GlobalID,asset_id", return_geometry=False).features}

high_sim = [a for a in T if H[a].attributes["community"] != "Montgomery"]
others = [a for a, f in H.items() if f.attributes["inspect_priority"] != "High" and a != "HYD-MON-001"]
sample = high_sim + random.sample(others, 22)

def when():
    d = dt.date(2026, 10, 26) + dt.timedelta(days=random.randint(0, 7))
    t = dt.datetime(d.year, d.month, d.day, random.randint(9, 15), random.choice([0, 15, 30, 45]), tzinfo=TZ)
    return int(t.timestamp() * 1000)

def record(asset_id, high, cond=None, defect=None):
    a = {"asset_id": asset_id, "inspect_date": when(), "data_origin": "Simulated",
         "notes": "SIMULATED record (demo data)", "task_id": "{" + T[asset_id]["GlobalID"].strip("{}").upper() + "}" if asset_id in T else None}
    if random.random() < 0.08:
        a.update(accessible="No", access_issue=random.choice(["Vehicle parked", "Snow or ice", "Vegetation"]))
        return a
    w = [5, 25, 35, 25, 10] if high else [15, 40, 30, 12, 3]
    c = cond or random.choices([1, 2, 3, 4, 5], weights=w)[0]
    a.update(accessible="Yes", cond_rating=str(c), obstructions="None", paint="Good", damage="None",
             caps="All present", leakage="None", defect_found="No")
    if c == 3 and random.random() < 0.3:
        a["paint"] = "Faded"
    types = []
    if c >= 4:
        types = random.sample(["Damaged", "Leaking", "Missing_caps", "Obstructed", "Paint_markings", "Leaning"], random.choice([1, 1, 2]))
    if defect is not None:
        a["defect_found"] = defect
    elif types:
        a["defect_found"] = "Yes"
    if a["defect_found"] == "Yes" and types:
        a["defect_type"] = ",".join(types)
        if "Paint_markings" in types: a["paint"] = "Peeling or rust"
        if "Leaking" in types: a["leakage"] = "Pooling water"
        if "Missing_caps" in types: a["caps"] = "One or more missing"
        if "Damaged" in types: a["damage"] = "Visible damage"
        if "Leaning" in types: a["damage"] = "Slight lean"
        if "Obstructed" in types: a["obstructions"] = "Vegetation"
    return a

adds = []
for aid in sample:
    adds.append({"geometry": H[aid].geometry, "attributes": record(aid, aid in T)})
# deliberate QC test cases
qc1 = record(others[0], False, cond=4, defect="No"); qc1["notes"] = "SIMULATED QC test case: rating 4 without defect"
adds.append({"geometry": H[others[0]].geometry, "attributes": qc1})
dup = dict(adds[0]["attributes"]); dup["notes"] = "SIMULATED QC test case: same-day duplicate"
adds.append({"geometry": adds[0]["geometry"], "attributes": dup})

r = insp.edit_features(adds=adds)
ok = sum(x["success"] for x in r["addResults"])
print("simulated inspections added:", ok, "/", len(adds))

# simulated task completion for the High-priority hydrants inspected above
done = [{"attributes": {"OBJECTID": T[a]["OBJECTID"], "esritask_status": 3,
                        "esritask_notes": "SIMULATED completion (demo data)"}} for a in high_sim]
r = tasks.edit_features(updates=done)
print("tasks marked Completed (simulated):", sum(x["success"] for x in r["updateResults"]), "/", len(done))
print("open tasks left for the field test:", [a for a in T if a not in high_sim])
