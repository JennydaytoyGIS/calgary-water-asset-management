"""
B4 - Dispatch Field Maps tasks for High-priority hydrants (run in ArcGIS Notebook).
1. Adds an asset_id field to the task layer (links each task to an asset)
2. Creates one 'Routine visual inspection' task per High-priority hydrant not yet tasked
3. Sets insp_status = 'Assigned' on those hydrants in AM_Hydrants
4. Adds a task pop-up with a Survey123 link that pre-fills asset_id and task_id
"""
from arcgis.gis import GIS
import datetime as dt, json

FORM_ID = "9b4e1d62249642df90c0a6b5ef647624"
DUE = dt.datetime(2026, 11, 20, 17, 0)

gis = GIS("home"); me = gis.users.me.username
def find(title, typ="Feature Service"):
    return [i for i in gis.content.search(f'title:"{title}" owner:{me}', item_type=typ, max_items=50) if i.title == title][0]

hyd = find("AM_Hydrants").layers[0]
task_item = find("AM_Hydrant_Tasks")
tasks = task_item.layers[0]

if "asset_id" not in [f["name"] for f in tasks.properties.fields]:
    print("add asset_id:", tasks.manager.add_to_definition({"fields": [{"name": "asset_id", "type": "esriFieldTypeString",
          "alias": "Asset ID", "length": 20, "nullable": True, "editable": True}]}))
    tasks = find("AM_Hydrant_Tasks").layers[0]

def field(name):
    return [x for x in tasks.properties.fields if x["name"] == name][0]
def code(name, label):
    for cv in field(name)["domain"]["codedValues"]:
        if cv["name"].lower() == label.lower():
            return cv["code"]
    raise ValueError(f"{name}: {label}")

T_TYPE = code("esritask_type", "Routine visual inspection")
T_ASSIGNED = code("esritask_status", "Assigned")
T_HIGH = code("esritask_priority", "High")
ASSIGNEE = field("esritask_assignee")["domain"]["codedValues"][0]["code"]
SR = tasks.properties.extent["spatialReference"]
OID = hyd.properties.objectIdField

existing = {f.attributes.get("asset_id") for f in tasks.query(where="1=1", out_fields="asset_id", return_geometry=False).features}
high = hyd.query(where="inspect_priority='High'", out_fields=f"{OID},asset_id,community,breaks_200m_since2016,nearest_break_m", out_sr=SR)
adds, upd = [], []
for f in high.features:
    a = f.attributes
    if a["asset_id"] in existing:
        continue
    adds.append({"geometry": f.geometry, "attributes": {
        "esritask_type": T_TYPE, "esritask_status": T_ASSIGNED, "esritask_assignee": ASSIGNEE,
        "esritask_priority": T_HIGH, "esritask_duedate": int(DUE.timestamp() * 1000), "asset_id": a["asset_id"],
        "esritask_description": (f"Visual inspection of {a['asset_id']} ({a['community']}). "
                                 f"{a['breaks_200m_since2016']} main breaks within 200 m since 2016; nearest {a['nearest_break_m']} m. "
                                 "Open the inspection form from the task pop-up.")}})
    upd.append({"attributes": {OID: a[OID], "insp_status": "Assigned"}})

if adds:
    r = tasks.edit_features(adds=adds)
    print("tasks added:", sum(x["success"] for x in r["addResults"]), "/", len(adds))
    r = hyd.edit_features(updates=upd)
    print("hydrants set to Assigned:", sum(x["success"] for x in r["updateResults"]), "/", len(upd))
else:
    print("no new tasks needed")

# Task pop-up with a Survey123 link (pre-fills asset_id, task_id = task GlobalID, and location)
LAT = ("var g = Geometry($feature); if (g.spatialReference.wkid == 4326) { return Round(g.y, 7) } "
       "return Round((2 * Atan(Exp(g.y / 6378137)) - PI / 2) * 180 / PI, 7);")
LON = ("var g = Geometry($feature); if (g.spatialReference.wkid == 4326) { return Round(g.x, 7) } "
       "return Round(g.x / 6378137 * 180 / PI, 7);")
link = (f"https://survey123.arcgis.app?itemID={FORM_ID}&field:asset_id={{asset_id}}&field:task_id={{GlobalID}}"
        "&center={expression/lat},{expression/lon}&callback=https://fieldmaps.arcgis.app")
web = (f"https://survey123.arcgis.com/share/{FORM_ID}?field:asset_id={{asset_id}}&field:task_id={{GlobalID}}"
       "&center={expression/lat},{expression/lon}")
popup = {
    "title": "Task · {asset_id}",
    "expressionInfos": [
        {"name": "lat", "title": "Latitude", "expression": LAT, "returnType": "number"},
        {"name": "lon", "title": "Longitude", "expression": LON, "returnType": "number"}],
    "popupElements": [
        {"type": "text", "text": f'<p><a href="{link}" target="_blank">▶ Start inspection</a></p><p><a href="{web}" target="_blank">(web form)</a></p>'},
        {"type": "fields", "fieldInfos": [
            {"fieldName": "asset_id", "label": "Asset ID", "visible": True},
            {"fieldName": "esritask_type", "label": "Task type", "visible": True},
            {"fieldName": "esritask_status", "label": "Status", "visible": True},
            {"fieldName": "esritask_priority", "label": "Priority", "visible": True},
            {"fieldName": "esritask_assignee", "label": "Assignee", "visible": True},
            {"fieldName": "esritask_duedate", "label": "Due date", "visible": True, "format": {"dateFormat": "shortDate"}},
            {"fieldName": "esritask_description", "label": "Description", "visible": True}]}],
    "fieldInfos": [], "showAttachments": True}

wm_item = find("ProjectB_Hydrant_Inspection_Map", "Web Map")
data = wm_item.get_data()
hit = 0
for lyr in data["operationalLayers"]:
    if lyr.get("itemId") == task_item.id or lyr.get("title") == "AM_Hydrant_Tasks":
        lyr["popupInfo"] = popup; lyr["disablePopup"] = False; hit += 1
print("task pop-up set on", hit, "layer(s):", wm_item.update(data=json.dumps(data)))
print("tasks now:", tasks.query(return_count_only=True))
