"""C13: Web maps for the ponding screening app (run in an ArcGIS Notebook).

Uses the hosted layer "ProjectC Ponding Screening" (published from outputs/agol/ponding_screening_agol.gdb.zip) and builds
the two web maps that the Experience Builder app "ProjectC Ponding Screening App" reads:
  1. "ProjectC Ponding Screening Map": Ottewell bluespots by priority, low points with no inlet within 40 m,
     and the catch basins and pipes around the priority bluespots.
  2. "ProjectC Ponding Reports Model Map": neighbourhoods coloured by how far 311 ponding reports differ from the model.
Style: light basemap, a blue ramp for bluespots (darker = check first), one amber accent for missing inlets,
and a teal-to-coral diverging scheme for the model gap. Re-running updates the existing items in place.
"""
from arcgis.gis import GIS
import json, uuid

gis = GIS("home"); me = gis.users.me.username
FOLDER = "ProjectC_Edmonton"
def find(title, typ):
    r = [i for i in gis.content.search(f'title:"{title}" owner:{me}', item_type=typ, max_items=50) if i.title == title]
    return r[0] if r else None
def save_item(title, props):
    it = find(title, props["type"])
    if it: it.update(item_properties=props); return it
    it = gis.content.add(item_properties=props)
    try: it.move(FOLDER)
    except Exception as e: print("move:", e)
    return it

svc = find("ProjectC Ponding Screening", "Feature Service")
lyr = {l.properties.name: l for l in svc.layers}
print("layers:", {k: v.properties.id for k, v in lyr.items()})
url = lambda n: f"{svc.url}/{lyr[n].properties.id}"

# ---------- palette ----------
INK = [31, 42, 51]            # text and outlines
AMBER = [232, 163, 61]        # the one warning accent: no inlet near the low point
PRI = {"High": ([8, 48, 107], 225), "Medium": ([66, 146, 198], 170), "Low": ([198, 219, 239], 160)}
PRI_OUTLINE = {"High": ([8, 48, 107, 255], 1.4), "Medium": ([33, 113, 181, 255], 0.7), "Low": ([107, 174, 214, 255], 0.5)}
GAP = [(-0.5, "Far fewer reports than expected", [42, 157, 143]), (-0.15, "Fewer than expected", [143, 211, 199]),
       (0.15, "About as expected", [236, 236, 236]), (0.5, "More than expected", [244, 165, 130]),
       (10, "Far more reports than expected", [214, 96, 77])]

def line(c, w, style="esriSLSSolid"): return {"type": "esriSLS", "style": style, "color": c, "width": w}
def fill(c, outline): return {"type": "esriSFS", "style": "esriSFSSolid", "color": c, "outline": outline}

bs_renderer = {"type": "uniqueValue", "field1": "priority", "uniqueValueInfos": [
    {"value": k, "label": {"High": "Check first", "Medium": "Check next", "Low": "Monitor"}[k] + f" ({k.lower()} priority)",
     "symbol": fill(c + [a], line(*PRI_OUTLINE[k]))}
    for k, (c, a) in PRI.items()]}
uncovered_renderer = {"type": "simple", "label": "No catch basin within 40 m of the lowest point",
                      "symbol": {"type": "esriSFS", "style": "esriSFSNull", "outline": line(AMBER + [255], 2.4)}}
gap_renderer = {"type": "classBreaks", "field": "residual", "minValue": -10, "classBreakInfos": [
    {"classMaxValue": mx, "label": lab, "symbol": fill(c + [225], line([255, 255, 255, 230], 0.5))} for mx, lab, c in GAP]}
cb_renderer = {"type": "simple", "label": "Catch basin", "symbol": {"type": "esriSMS", "style": "esriSMSCircle", "color": INK + [255], "size": 5,
                                                                "outline": {"color": [255, 255, 255, 255], "width": 0.8}}}
pipe_renderer = {"type": "uniqueValue", "field1": "system", "uniqueValueInfos": [
    {"value": "STORM", "label": "Storm sewer", "symbol": line([84, 110, 122, 255], 1.6)},
    {"value": "COMBINED", "label": "Combined sewer", "symbol": line([123, 94, 167, 255], 1.6)},
    {"value": "SANITARY", "label": "Sanitary sewer", "symbol": line([161, 136, 127, 255], 1.0)}]}
boundary_renderer = {"type": "simple", "label": "Ottewell", "symbol": {"type": "esriSFS", "style": "esriSFSNull", "outline": line(INK + [255], 1.8, "esriSLSDash")}}

# ---------- pop-ups ----------
BS_ACTION = """
var cov = $feature.coverage;
if ($feature.terrain_feature == 1) { return 'Ravine head closed by road fill in the surface; check the culvert before treating it as ponding.' }
return When(cov == 'Uncovered', 'No catch basin within 40 m of the lowest point: check whether an inlet is missing or the low point is mapped wrongly.',
            cov == 'Partial', 'Nearest catch basin is 15–40 m from the lowest point: check grading towards it and its condition after rain.',
            'An inlet is close to the lowest point: check it is clear and sized for the storage behind it.');
"""
bs_popup = {"title": "{bluespot_id} · {priority} priority",
            "expressionInfos": [{"name": "act", "title": "What to check", "expression": BS_ACTION, "returnType": "string"}],
            "fieldInfos": [{"fieldName": f, "format": {"places": p, "digitSeparator": True}} for f, p in
                           [("volume_m3", 0), ("area_m2", 0), ("max_depth_m", 2), ("dist_cb_m", 1), ("buildings_touching", 0), ("cb_inside_or_5m", 0)]],
            "popupElements": [{"type": "text", "text": "<p><b>What to check:</b> {expression/act}</p><p>Holds <b>{volume_m3} m³</b> over {area_m2} m² when the sewers are full, up to {max_depth_m} m deep; {buildings_touching} buildings touching.</p><p>Nearest catch basin {dist_cb_m} m from the lowest point ({coverage}); {cb_inside_or_5m} catch basins in or within 5 m.</p>"}]}
GAP_TEXT = "var d = $feature.residual; var t = When(" + ", ".join(
    f"d <= {mx}, '{lab.lower() if i else lab}'" for i, (mx, lab, _) in enumerate(GAP[:-1])) + f", '{GAP[-1][1].lower()}'); return Upper(Left(t, 1)) + Mid(t, 1);"
nb_popup = {"title": "{neighbourhood_name}",
            "expressionInfos": [{"name": "rate", "title": "Rate", "returnType": "number", "expression": "Round($feature.rate_per_km2, 1)"},
                                {"name": "pred", "title": "Expected", "returnType": "number", "expression": "Round(Exp($feature.pred_log_rate) - 1, 1)"},
                                {"name": "gap", "title": "Gap", "returnType": "string", "expression": GAP_TEXT}],
            "popupElements": [{"type": "text", "text": "<p><b>{expression/gap}</b>: {expression/rate} rain-season ponding reports per km² against {expression/pred} expected from terrain, drainage and population.</p><p>{reports} reports, May–September 2023–2026 (rank {obs_rank} of 269; expected rank {pred_rank}).</p><p>Factors pushing reports up here: <b>{driver_1}</b>, {driver_2}, {driver_3}.</p>"}]}
asset_popup = {"title": "{asset_id} · {asset_type}", "popupElements": [{"type": "text", "text": "<p>{system}, built {year_built}. Serves {bluespot_id} ({priority} priority), {dist_m} m away.</p>"}]}

def op(name, title, renderer, popup=None, min_scale=0, max_scale=0, where=None, opacity=1, visible=True):
    d = {"id": f"{name}-{uuid.uuid4().hex[:6]}", "title": title, "url": url(name), "itemId": svc.id, "layerType": "ArcGISFeatureLayer",
         "visibility": visible, "opacity": opacity, "disablePopup": popup is None,
         "layerDefinition": {"minScale": min_scale, "maxScale": max_scale, "drawingInfo": {"renderer": renderer}}}
    if where: d["layerDefinition"]["definitionExpression"] = where
    if popup: d["popupInfo"] = popup
    return d

BASE = {"title": "Light Gray Canvas", "baseMapLayers": [
    {"id": "gray-base", "title": "World Light Gray Base", "layerType": "ArcGISTiledMapServiceLayer", "visibility": True, "opacity": 1,
     "url": "https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer"},
    {"id": "gray-ref", "title": "World Light Gray Reference", "layerType": "ArcGISTiledMapServiceLayer", "visibility": True, "opacity": 1, "isReference": True,
     "url": "https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer"}]}
def webmap(layers, xmin, ymin, xmax, ymax):
    return {"operationalLayers": layers, "baseMap": BASE, "spatialReference": {"wkid": 102100, "latestWkid": 3857},
            "authoringApp": "ArcGIS Notebook", "authoringAppVersion": "1", "version": "2.31",
            "initialState": {"viewpoint": {"targetGeometry": {"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax, "spatialReference": {"wkid": 102100}}}}}

ottewell = [
    op("bluespots_ottewell", "Where water ponds (bluespots by priority)", bs_renderer, bs_popup, where="terrain_feature = 0"),
    op("bluespots_ottewell", "No catch basin within 40 m of the lowest point", uncovered_renderer, None, where="terrain_feature = 0 AND coverage = 'Uncovered'"),
    op("priority_pipes", "Sewers near priority bluespots", pipe_renderer, asset_popup, min_scale=25000),
    op("priority_catch_basins", "Catch basins near priority bluespots", cb_renderer, asset_popup, min_scale=25000),
    op("ottewell_boundary", "Ottewell", boundary_renderer),        # no pop-up: the app's detail panel should only show bluespots
]
wm1 = save_item("ProjectC Ponding Screening Map", {
    "type": "Web Map", "title": "ProjectC Ponding Screening Map",
    "tags": "flooding, ponding, drainage, bluespot, Edmonton, portfolio",
    "snippet": "Where water ponds in Ottewell when the sewers are full, which low points lack an inlet, and the catch basins and sewers to check (portfolio project).",
    "extent": "-113.452,53.515,-113.408,53.546",
    "text": json.dumps(webmap(ottewell, -12629750, 7078270, -12624190, 7085010))})

city = [op("nb_model", "311 ponding reports compared with the model", gap_renderer, nb_popup)]   # one layer, so the detail panel follows it
wm2 = save_item("ProjectC Ponding Reports Model Map", {
    "type": "Web Map", "title": "ProjectC Ponding Reports Model Map",
    "tags": "flooding, ponding, 311, machine learning, SHAP, Edmonton, portfolio",
    "snippet": "Edmonton neighbourhoods by how far rain-season 311 ponding reports differ from an explainable model of terrain, drainage and population (portfolio project).",
    "extent": "-113.72,53.39,-113.27,53.72",
    "text": json.dumps(webmap(city, -12654000, 7060000, -12590000, 7120000))})

base = gis.url.split("//")[1]
for wm in (wm1, wm2): print(wm.title, f"https://{base}/apps/mapviewer/index.html?webmap={wm.id}")
