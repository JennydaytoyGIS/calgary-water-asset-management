"""
B6b - QC inspections, update the asset register, and raise work orders (run in ArcGIS Notebook).
QC rules
  R1 asset_id must exist in AM_Hydrants
  R2 one inspection per asset per day (later same-day records fail as duplicates)
  R3 accessible = Yes needs a condition rating
  R4 condition 4-5 must be reported as a defect
  R5 field-test defects need a defect photo (simulated records cannot carry photos)
  R6 accessible = No needs an access issue
Write-back: latest QC-passed inspection per asset -> last_inspect_date, last_condition, insp_status, last_insp_origin
Work orders: QC-passed inspections with a defect or condition >= 4 -> AM_WorkOrders (one per inspection)
"""
from arcgis.gis import GIS
from arcgis.features import FeatureLayerCollection
import datetime as dt
from collections import Counter

# Alberta moved to permanent Alberta Time (UTC-6) on 2026-11-01. The ArcGIS Notebook tz database
# still applies the old MST rule (UTC-7) to "America/Edmonton", so use a fixed UTC-6 offset.
# All project data (from Oct 2026) falls in UTC-6 either way (MDT before Nov 1, Alberta Time after).
TZ = dt.timezone(dt.timedelta(hours=-6), "Alberta Time")
gis = GIS("home"); me = gis.users.me.username
def find(title, typ="Feature Service"):
    r = [i for i in gis.content.search(f'title:"{title}" owner:{me}', item_type=typ, max_items=50) if i.title == title]
    return r[0] if r else None

hyd = find("AM_Hydrants").layers[0]
insp_item = find("AM Hydrant Visual Inspection")
insp = insp_item.layers[0]

# --- schema: QC fields, register origin field, work-order table ---
def ensure_fields(layer, defs):
    have = {f["name"].lower() for f in layer.properties.fields}
    new = [d for d in defs if d["name"].lower() not in have]
    if new:
        print("add fields", [d["name"] for d in new], layer.manager.add_to_definition({"fields": new}))
ensure_fields(insp, [{"name": "qc_status", "type": "esriFieldTypeString", "alias": "QC status", "length": 10, "nullable": True, "editable": True},
                     {"name": "qc_notes", "type": "esriFieldTypeString", "alias": "QC notes", "length": 255, "nullable": True, "editable": True}])
ensure_fields(hyd, [{"name": "last_insp_origin", "type": "esriFieldTypeString", "alias": "Last inspection origin", "length": 20, "nullable": True, "editable": True}])
insp = find("AM Hydrant Visual Inspection").layers[0]; hyd = find("AM_Hydrants").layers[0]

wo_item = find("AM_WorkOrders")
if wo_item is None:
    wo_item = gis.content.create_service(name="AM_WorkOrders", service_type="featureService")
    wo_item.update(item_properties={"title": "AM_WorkOrders", "tags": "asset management, hydrant, work order, portfolio",
                                    "snippet": "Work orders raised from QC-passed hydrant inspections (Project B; simulates a CMMS)."})
    try:
        wo_item.move("ProjectB_AM")
    except Exception as e:
        print("move:", e)
    dom = lambda n, vals: {"type": "codedValue", "name": n, "codedValues": [{"name": v, "code": v} for v in vals]}
    S = lambda n, a, l, d=None: {"name": n, "type": "esriFieldTypeString", "alias": a, "length": l, "nullable": True, "editable": True, **({"domain": d} if d else {})}
    table = {"name": "AM_WorkOrders", "type": "Table", "displayField": "wo_id", "objectIdField": "OBJECTID", "globalIdField": "GlobalID",
             "hasAttachments": False, "capabilities": "Create,Delete,Query,Update,Editing",
             "fields": [{"name": "OBJECTID", "type": "esriFieldTypeOID", "alias": "OBJECTID", "nullable": False, "editable": False},
                        {"name": "GlobalID", "type": "esriFieldTypeGlobalID", "alias": "GlobalID", "length": 38, "nullable": False, "editable": False},
                        S("wo_id", "Work order ID", 20), S("asset_id", "Asset ID", 20), S("community", "Community", 40),
                        S("inspection_guid", "Inspection GlobalID", 38),
                        {"name": "inspect_date", "type": "esriFieldTypeDate", "alias": "Inspection date", "length": 8, "nullable": True, "editable": True},
                        {"name": "cond_rating", "type": "esriFieldTypeInteger", "alias": "Condition", "nullable": True, "editable": True},
                        S("defect_type", "Defect type", 255),
                        S("wo_priority", "Priority", 10, dom("wo_priority", ["Urgent", "High", "Normal"])),
                        S("wo_status", "Status", 15, dom("wo_status", ["Open", "In progress", "Closed"])),
                        {"name": "created_date", "type": "esriFieldTypeDate", "alias": "Created", "length": 8, "nullable": True, "editable": True},
                        S("data_origin", "Data origin", 20), S("notes", "Notes", 500)]}
    flc = FeatureLayerCollection.fromitem(wo_item)
    print("service capabilities:", flc.manager.update_definition({"capabilities": "Create,Delete,Query,Update,Editing"}))
    print("work-order table:", flc.manager.add_to_definition({"tables": [table]}))
    wo_item = find("AM_WorkOrders")
wo = wo_item.tables[0]

# --- load data ---
reg = {f.attributes["asset_id"]: f.attributes for f in hyd.query(where="1=1", out_fields="*", return_geometry=False).features}
rows = [f.attributes for f in insp.query(where="1=1", out_fields="*", return_geometry=False).features]
rows.sort(key=lambda a: (a.get("inspect_date") or 0, a["objectid"]))
photos = set()
for a in rows:
    if a.get("defect_found") == "Yes" and a.get("data_origin") == "Field test":
        try:
            if any("defect_photo" in (x.get("keywords") or x.get("name", "")) for x in insp.attachments.get_list(a["objectid"])):
                photos.add(a["objectid"])
        except Exception as e:
            print("attachments:", e)

def local_day(ms):
    return dt.datetime.fromtimestamp(ms / 1000, TZ).date() if ms else None

seen, qc_upd, results = set(), [], []
for a in rows:
    issues = []
    if not a.get("asset_id") or a["asset_id"] not in reg: issues.append("R1 unknown asset_id")
    key = (a.get("asset_id"), local_day(a.get("inspect_date")))
    if key in seen: issues.append("R2 same-day duplicate")
    seen.add(key)
    if a.get("accessible") == "Yes" and not a.get("cond_rating"): issues.append("R3 missing condition")
    c = int(a["cond_rating"]) if a.get("cond_rating") else None
    if c and c >= 4 and a.get("defect_found") != "Yes": issues.append("R4 condition >=4 without defect")
    if a.get("defect_found") == "Yes" and a.get("data_origin") == "Field test" and a["objectid"] not in photos: issues.append("R5 defect without photo")
    if a.get("accessible") == "No" and not a.get("access_issue"): issues.append("R6 missing access issue")
    status = "Fail" if issues else "Pass"
    results.append((a, status, issues))
    if a.get("qc_status") != status or (a.get("qc_notes") or "") != "; ".join(issues):
        qc_upd.append({"attributes": {"objectid": a["objectid"], "qc_status": status, "qc_notes": "; ".join(issues)}})
if qc_upd:
    r = insp.edit_features(updates=qc_upd)
    print("QC written:", sum(x["success"] for x in r["updateResults"]), "/", len(qc_upd))

# --- write-back: latest passed inspection per asset ---
latest = {}
for a, s, _ in results:
    if s == "Pass":
        latest[a["asset_id"]] = a
OID = hyd.properties.objectIdField
upd = []
for aid, a in latest.items():
    if a.get("accessible") == "No":
        st, cond = "Inaccessible", None
    else:
        st = "Inspected - Defect" if a.get("defect_found") == "Yes" else "Inspected - OK"
        cond = int(a["cond_rating"])
    upd.append({"attributes": {OID: reg[aid][OID], "insp_status": st, "last_condition": cond,
                               "last_inspect_date": a["inspect_date"], "last_insp_origin": a.get("data_origin")}})
if upd:
    r = hyd.edit_features(updates=upd)
    print("register updated:", sum(x["success"] for x in r["updateResults"]), "/", len(upd))

# --- work orders ---
existing = {f.attributes["inspection_guid"] for f in wo.query(where="1=1", out_fields="inspection_guid").features}
n = wo.query(return_count_only=True)
now = int(dt.datetime.now(TZ).timestamp() * 1000)
wos = []
for a, s, _ in results:
    c = int(a["cond_rating"]) if a.get("cond_rating") else 0
    if s != "Pass" or not (a.get("defect_found") == "Yes" or c >= 4) or a["globalid"] in existing:
        continue
    n += 1
    types = a.get("defect_type") or ""
    pr = "Urgent" if (c == 5 or "Leaking" in types) else ("High" if c == 4 else "Normal")
    wos.append({"attributes": {"wo_id": f"WO-2026-{n:04d}", "asset_id": a["asset_id"], "community": reg[a["asset_id"]]["community"],
                               "inspection_guid": a["globalid"], "inspect_date": a["inspect_date"], "cond_rating": c or None,
                               "defect_type": types, "wo_priority": pr, "wo_status": "Open", "created_date": now,
                               "data_origin": a.get("data_origin"), "notes": "Raised automatically from QC-passed inspection"}})
if wos:
    r = wo.edit_features(adds=wos)
    print("work orders raised:", sum(x["success"] for x in r["addResults"]), "/", len(wos))

# --- report ---
lines = [f"# QC report {dt.datetime.now(TZ):%Y-%m-%d %H:%M}", "",
         f"- Inspections checked: {len(results)} (" + ", ".join(f"{k}: {v}" for k, v in Counter(a.get('data_origin') for a, _, _ in results).items()) + ")",
         f"- QC pass: {sum(s == 'Pass' for _, s, _ in results)}, fail: {sum(s == 'Fail' for _, s, _ in results)}",
         f"- Assets updated in register: {len(upd)}",
         f"- New work orders: {len(wos)} (" + ", ".join(f"{k}: {v}" for k, v in Counter(w['attributes']['wo_priority'] for w in wos).items()) + ")",
         "", "## Failed records", "", "| asset_id | date | origin | issues |", "|---|---|---|---|"]
for a, s, iss in results:
    if s == "Fail":
        lines.append(f"| {a.get('asset_id')} | {local_day(a.get('inspect_date'))} | {a.get('data_origin')} | {'; '.join(iss)} |")
lines += ["", "## Register status after write-back", ""]
for k, v in sorted(Counter(f.attributes["insp_status"] for f in hyd.query(where="1=1", out_fields="insp_status").features).items()):
    lines.append(f"- {k}: {v}")
report = "\n".join(lines)
open("/arcgis/home/qc_report.md", "w").write(report)
print(report)
