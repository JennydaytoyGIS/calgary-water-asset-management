"""C6: Configure the hosted layer, build the review web map and the dashboard (run in an ArcGIS Notebook).

Step 1  Hosted layer "ProjectC Edmonton Drainage QA" (published from outputs/agol/edmonton_drainage_agol.gdb.zip):
        allow attribute updates only, and give review_status a list of allowed values.
Step 2  Web map "ProjectC Drainage QA Review Map": symbology by system and severity, Arcade pop-ups.
Step 3  Dashboard "ProjectC Drainage QA Dashboard".
Re-running updates the existing items instead of creating new ones.
"""
from arcgis.gis import GIS
import json, uuid

gis = GIS("home"); me = gis.users.me.username
FOLDER = "ProjectC_Edmonton"
def find(title, typ):
    r = [i for i in gis.content.search(f'title:"{title}" owner:{me}', item_type=typ, max_items=50) if i.title == title]
    return r[0] if r else None

for make in (lambda: gis.content.folders.create(FOLDER), lambda: gis.content.create_folder(FOLDER)):
    try:
        make(); break
    except Exception:
        pass
def add_item(props):
    it = gis.content.add(item_properties=props)
    try:
        it.move(FOLDER)
    except Exception as e:
        print("move:", e)
    return it

svc = find("ProjectC Edmonton Drainage QA", "Feature Service")
lyr = {l.properties.name: l for l in svc.layers}
print("layers:", {k: v.properties.id for k, v in lyr.items()})
try:
    svc.move(FOLDER)
except Exception as e:
    print("move:", e)

# ---- Step 1: editing for review fields only
from arcgis.features import FeatureLayerCollection
flc = FeatureLayerCollection.fromitem(svc)
try:
    print("editing:", flc.manager.update_definition({"capabilities": "Query,Editing,Update", "allowGeometryUpdates": False}))
except Exception as e:
    print("editing not changed:", e)
qa = lyr["qa_issues"]
fields = []
for f in qa.properties.fields:
    f = dict(f)
    if f["name"] == "review_status":
        f["domain"] = {"type": "codedValue", "name": "ReviewStatus",
                       "codedValues": [{"name": n, "code": n} for n in ["Not reviewed", "Confirmed error", "Fixed", "Not an issue"]]}
    if f["name"] not in ("review_status", "review_note") and f.get("editable", True) and f["type"] not in ("esriFieldTypeOID", "esriFieldTypeGlobalID"):
        f["editable"] = False
    fields.append(f)
try:
    print("qa_issues fields:", qa.manager.update_definition({"fields": [f for f in fields if f["name"] in ("review_status",) or f.get("editable") is False]}))
except Exception as e:
    print("fields not changed:", e)

# ---- Step 1b: a view that holds only high severity issues (used by the dashboard)
# ("rule" is a reserved word, so the hosted layer stores that field as "rule_")
VIEW = "ProjectC_QA_High_Issues"
view = find(VIEW, "Feature Service")
if not view:
    view = flc.manager.create_view(name=VIEW)
    try:
        view.move(FOLDER)
    except Exception as e:
        print("move view:", e)
vq = [l for l in view.layers if l.properties.name == "qa_issues"][0]
print("view filter:", vq.manager.update_definition({"viewDefinitionQuery": "severity = 'High'"}))

# ---- Step 2: web map
def lid(name): return lyr[name].properties.id
def url(name): return f"{svc.url}/{lid(name)}"
def line(c, w): return {"type": "esriSLS", "style": "esriSLSSolid", "color": c, "width": w}
def pt(c, size, style="esriSMSCircle", outline=(255, 255, 255, 255), ow=0.6):
    return {"type": "esriSMS", "style": style, "color": c, "size": size, "outline": {"color": list(outline), "width": ow}}
SYS = {"STORM": ([44, 127, 184, 255], "Storm"), "SANITARY": ([217, 95, 14, 255], "Sanitary"),
       "COMBINED": ([123, 94, 167, 255], "Combined"), "FOUNDATION DRAIN": ([140, 140, 140, 255], "Foundation drain")}
def by_system(width):
    return {"type": "uniqueValue", "field1": "system", "defaultSymbol": line([160, 160, 160, 255], width),
            "uniqueValueInfos": [{"value": k, "label": v[1], "symbol": line(v[0], width)} for k, v in SYS.items()]}
SEV = {"High": ([192, 57, 43, 255], 9, "esriSMSX"), "Medium": ([230, 159, 0, 255], 8, "esriSMSDiamond"), "Low": ([82, 96, 109, 255], 6, "esriSMSTriangle")}
qa_renderer = {"type": "uniqueValue", "field1": "severity",
               "uniqueValueInfos": [{"value": k, "label": f"{k} severity", "symbol": pt(c, s, st, (255, 255, 255, 255) if st != "esriSMSX" else c, 1.6 if st == "esriSMSX" else 0.6)} for k, (c, s, st) in SEV.items()]}
choropleth = {"type": "classBreaks", "field": "issues_per_km", "minValue": 0,
              "classBreakInfos": [{"classMaxValue": mx, "label": lab, "symbol": {"type": "esriSFS", "style": "esriSFSSolid", "color": c, "outline": line([255, 255, 255, 180], 0.4)}}
                                  for mx, lab, c in [(0.5, "Under 0.5", [254, 240, 217, 200]), (1, "0.5–1", [253, 204, 138, 200]),
                                                     (2, "1–2", [252, 141, 89, 200]), (100, "2 or more", [215, 48, 31, 200])]]}

QA_POPUP_EXPR = """
var r = $feature.rule_;
var check = Decode(r,
  'R1', 'Is there a manhole or pipe missing at this end, or is it a stub left for a future connection?',
  'R2', 'Is a pipe or lead missing, or is this point misplaced?',
  'R3', 'Is this a drawing error, or a real storm/sanitary cross-connection? Check first.',
  'R4', 'Find the year on record drawings, or record an estimated era.',
  'R5', 'Keep one of the two identical pipes.',
  'R6', 'Merge with the neighbouring pipe or delete if it is an artefact.',
  'R7', 'Compare the rim elevation with as-built drawings or a survey point.',
  'R8', 'Add the missing name from the address or street network.',
  'R9', 'Find how this small group connects to the rest of the network.',
  'Review the asset.');
return check;
"""
qa_popup = {"title": "{rule_}  {rule_name}",
            "expressionInfos": [{"name": "check", "title": "What to check", "expression": QA_POPUP_EXPR, "returnType": "string"}],
            "popupElements": [
                {"type": "text", "text": "<p><b>{severity}</b> severity · {asset_id} ({system})</p><p>{detail}</p><p><b>What to check:</b> {expression/check}</p>"},
                {"type": "fields"}],
            "fieldInfos": [{"fieldName": f, "label": lab, "visible": True, "isEditable": f in ("review_status", "review_note")}
                           for f, lab in [("issue_id", "Issue"), ("neighbourhood_name", "Neighbourhood"), ("review_status", "Review status"), ("review_note", "Review note")]]}
pipe_popup = {"title": "{asset_id} · {system}",
              "expressionInfos": [{"name": "age", "title": "Age", "returnType": "string",
                                   "expression": "IIf(IsEmpty($feature.year_built), 'Year unknown', Text(Year(Now()) - $feature.year_built) + ' years (built ' + Text($feature.year_built) + ')')"}],
              "popupElements": [{"type": "text", "text": "<p>{system} pipe, {length_m} m · {expression/age}</p><p>{road_name}, {neighbourhood_name}</p><p>Connected group {component}: {component_pipes} pipes</p>"}]}
mh_popup = {"title": "{asset_id} · {system} manhole",
            "popupElements": [{"type": "text", "text": "<p>Rim elevation: {rim_elev} m ({rim_flag})</p><p>Built: {year_built}</p><p>{road_name}, {neighbourhood_name}</p>"}]}
nb_popup = {"title": "{neighbourhood_name}",
            "popupElements": [{"type": "text", "text": "<p>{pipe_km} km of pipe · {combined_share} combined by length · median year built {median_year}</p><p>{issues_med_high} medium and high issues ({issues_per_km} per km), {issues_all} issues in total</p>"}]}

def op(name, title, renderer=None, popup=None, visible=True, min_scale=0, opacity=1, max_scale=0):
    d = {"id": f"{name}-{uuid.uuid4().hex[:6]}", "title": title, "url": url(name), "itemId": svc.id, "layerType": "ArcGISFeatureLayer",
         "visibility": visible, "opacity": opacity, "layerDefinition": {"minScale": min_scale, "maxScale": max_scale}}
    if renderer: d["layerDefinition"]["drawingInfo"] = {"renderer": renderer}
    if popup: d["popupInfo"] = popup
    return d

layers = [
    op("neighbourhood_summary", "QA issues per km (neighbourhood)", choropleth, nb_popup, opacity=0.75, max_scale=30000),
    op("pilot_areas", "Pilot areas", {"type": "simple", "symbol": {"type": "esriSFS", "style": "esriSFSNull", "outline": line([31, 41, 51, 255], 1.6)}}),
    op("swm_facilities", "Stormwater ponds", {"type": "simple", "symbol": {"type": "esriSFS", "style": "esriSFSSolid", "color": [207, 227, 243, 220], "outline": line([156, 195, 228, 255], 0.6)}}),
    op("pipes_citywide", "Pipes (citywide)", by_system(0.8), pipe_popup, min_scale=150000),
    op("pipes_pilot", "Pipes (pilot areas, with connectivity)", by_system(1.6), pipe_popup, min_scale=40000),
    op("catch_basins_pilot", "Catch basins (pilot)", {"type": "simple", "symbol": pt([154, 165, 177, 255], 3, outline=(154, 165, 177, 255), ow=0)}, min_scale=10000),
    op("manholes_pilot", "Manholes (pilot)", {"type": "simple", "symbol": pt([255, 255, 255, 255], 5, outline=(31, 41, 51, 255), ow=0.7)}, mh_popup, min_scale=15000),
    op("outfalls", "Outfalls", {"type": "simple", "symbol": pt([0, 109, 119, 255], 9, "esriSMSTriangle")}),
    op("pump_stations", "Pump stations", {"type": "simple", "symbol": pt([31, 41, 51, 255], 9, "esriSMSSquare")}),
    op("qa_issues", "QA issues", qa_renderer, qa_popup, min_scale=80000),
]
layers.append({"id": "qa-high-view", "title": "QA issues, high severity (view)", "url": f"{view.url}/{vq.properties.id}", "itemId": view.id,
               "layerType": "ArcGISFeatureLayer", "visibility": False, "opacity": 1,
               "layerDefinition": {"minScale": 80000, "maxScale": 0, "drawingInfo": {"renderer": qa_renderer}}, "popupInfo": qa_popup})
wm_data = {"operationalLayers": layers,
           "baseMap": {"title": "Light Gray Canvas", "baseMapLayers": [
               {"id": "gray-base", "title": "World Light Gray Base", "layerType": "ArcGISTiledMapServiceLayer", "visibility": True, "opacity": 1,
                "url": "https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer"}]},
           "spatialReference": {"wkid": 102100, "latestWkid": 3857}, "authoringApp": "ArcGIS Notebook", "authoringAppVersion": "1", "version": "2.31",
           "initialState": {"viewpoint": {"targetGeometry": {"xmin": -12654000, "ymin": 7060000, "xmax": -12590000, "ymax": 7120000, "spatialReference": {"wkid": 102100}}}}}
wm_props = {"type": "Web Map", "title": "ProjectC Drainage QA Review Map", "tags": "drainage, sewer, QA, utility network, portfolio, Edmonton",
            "snippet": "Review map for Edmonton drainage QA issues (portfolio project).", "extent": "-113.72,53.39,-113.27,53.72", "text": json.dumps(wm_data)}
wm = find("ProjectC Drainage QA Review Map", "Web Map")
if wm:
    wm.update(item_properties=wm_props)
else:
    wm = add_item(wm_props)
print("web map:", wm.id)
ids = {l["title"]: l["id"] for l in wm_data["operationalLayers"]}
QA, NB, PP, QH = ids["QA issues"], ids["QA issues per km (neighbourhood)"], ids["Pipes (citywide)"], ids["QA issues, high severity (view)"]

# ---- Step 3: dashboard (structure follows Project B's B7 script)
U = lambda: str(uuid.uuid4())
STATE = {"noDataState": {"verticalAlignment": "middle", "showTopCaption": True, "showBottomCaption": True},
         "noFilterState": {"verticalAlignment": "middle", "showTopCaption": True, "showBottomCaption": True}}
def ds(layer, group=None, oid="OBJECTID", order=None, maxf=None, where=None, stat=None):
    d = {"type": "serviceDataset", "name": "main", "dataSource": {"type": "layerDataSource", "itemId": wm.id, "layerId": layer},
         "groupByFields": group or [], "orderByFields": order or [],
         "statisticDefinitions": [stat or {"onStatisticField": oid, "statisticType": "count", "outStatisticFieldName": "COUNT_OID"}] if (group is not None or maxf is None) else [],
         "outFields": ["*"], "returnDistinctValues": False, "allowSourceDownload": False, "allowSummaryDownload": False}
    if where:  # where = (field, value): equality filter in the Dashboards filter format
        d["filter"] = {"type": "filterGroup", "condition": "AND", "rules": [
            {"type": "filterRule", "field": {"name": where[0], "type": "esriFieldTypeString"}, "operator": "is",
             "constraint": {"type": "value", "value": where[1]}}]}
    if maxf: d["maxFeatures"] = maxf
    return d
def indicator(name, layer, label, color, where=None):
    return {"id": U(), "name": name, "showLastUpdate": False, **STATE, "datasets": [ds(layer, where=where)], "type": "indicatorWidget",
            "defaultSettings": {"topSection": {"fontSize": 80, "textInfo": {}},
                                "middleSection": {"fontSize": 160, "textInfo": {"text": "{calculated/value}"}, "textColor": color},
                                "bottomSection": {"fontSize": 80, "textInfo": {"text": label}}},
            "comparison": "none", "valueFormat": {"name": "value", "prefix": False, "style": "decimal", "useGrouping": True, "maximumFractionDigits": 0},
            "percentageFormat": {"name": "percentage", "prefix": False, "style": "percent", "useGrouping": True},
            "ratioFormat": {"name": "ratio", "prefix": False, "style": "decimal", "useGrouping": True, "maximumFractionDigits": 2},
            "valueType": "statistic", "noValueState": {"verticalAlignment": "middle", "showTopCaption": True, "showBottomCaption": True}}
def axis(title, angle, cat):
    a = {"type": "chartAxis", "visible": True,
         "title": {"type": "chartText", "visible": not cat, "content": {"type": "esriTS", "angle": angle, "font": {"family": "inherit", "style": "normal", "weight": "bold"}, "text": title}},
         "lineSymbol": {"type": "esriSLS", "style": "esriSLSSolid", "width": 1},
         "labels": {"type": "chartText", "visible": True, "content": {"type": "esriTS", "angle": 0, "font": {"family": "inherit", "style": "normal", "weight": "normal"}}},
         "grid": {"type": "esriSLS", "style": "esriSLSSolid", "width": 1}, "guides": []}
    if cat: a["scrollbar"] = {"width": 15, "gripSize": 22}
    a["valueFormat"] = {"type": "category", "characterLimit": 30} if cat else {"type": "number", "intlOptions": {"style": "decimal", "notation": "standard", "minimumFractionDigits": 0, "maximumFractionDigits": 0}}
    if not cat: a["buffer"] = True
    return a
def chart(name, title, caption, layer, field, cat_title, val_title, color, oid="OBJECTID"):
    sym = {"type": "esriSFS", "style": "esriSFSSolid", "color": color, "outline": {"type": "esriSLS", "style": "esriSLSSolid", "color": color, "width": 1}}
    return {"id": U(), "name": name, "title": title, "topCaption": caption, "showLastUpdate": False, **STATE,
            "datasets": [ds(layer, group=[field], oid=oid)], "dashboardItemType": "widget", "focusModeEnabled": False, "actionMode": "none", "categoryType": "groupByValues",
            "type": "serialChartWidget",
            "valueFormat": {"name": "value", "prefix": True, "style": "decimal", "useGrouping": True, "maximumFractionDigits": 0},
            "labelFormat": {"name": "label", "prefix": True, "style": "decimal", "useGrouping": True, "maximumFractionDigits": 0},
            "category": {"labelOverrides": [], "nullLabel": "None", "blankLabel": "blank"},
            "parseDates": False, "minPeriod": "MM", "categoryAxisLabelsBehavior": "hide",
            "chartConfig": {"version": "25.1.0", "type": "chart", "orderOptions": {}, "colorMatch": False,
                            "axes": [axis(cat_title, 270, True), axis(val_title, 0, False)],
                            "series": [{"type": "barSeries", "id": "COUNT_OID", "name": "groupByValues", "x": field, "y": "COUNT_OID",
                                        "dataLabels": {"type": "chartText", "visible": True, "content": {"type": "esriTS", "angle": 0, "font": {"family": "inherit", "size": 12, "style": "normal", "weight": "normal"}}},
                                        "dataTooltipVisible": True, "dataTooltipReverseColor": True, "fillSymbol": sym}],
                            "legend": {"type": "chartLegend", "visible": False, "body": {"type": "esriTS", "angle": 0, "font": {"family": "inherit", "size": 12, "style": "normal", "weight": "normal"}}, "position": "bottom"},
                            "horizontalAxisLabelsBehavior": "hide", "verticalAxisLabelsBehavior": "hide", "rotated": True,
                            "cursorCrosshair": {"type": "cursorCrosshair", "verticalLineVisible": False, "horizontalLineVisible": False}, "stackedType": "sideBySide"}}

ind1 = indicator("All issues", QA, "QA issues", "#ffffff")
ind2 = indicator("High severity", QH, "High severity", "#ff7b6b")
ind3 = indicator("Pipes checked", PP, "Pipes checked", "#7fd6ff")
ch1 = chart("Issues by rule", "Issues by rule", "<p>Rule codes are explained under About the data</p>", QA, "rule_", "Rule", "Issues", [255, 140, 102, 255])
ch2 = chart("Issues by system", "Issues by system", "<p>Storm, sanitary, combined</p>", QA, "system", "System", "Issues", [127, 214, 255, 255])
ch3 = chart("Review status", "Review status", "<p>Reviewers update this in the map pop-ups</p>", QA, "review_status", "Status", "Issues", [255, 209, 102, 255])
mp = {"headerBackgroundColor": "#1a4a73", "id": U(), "name": "Review map", "showLastUpdate": False, **STATE, "type": "mapWidget",
      "flashRepeats": 3, "itemId": wm.id, "mapTools": [{"type": "legendTool"}, {"type": "mapContentsTool"}, {"type": "basemapGalleryTool"}],
      "showMeasureTool": False, "showNavigation": True, "showPanRotate": False, "showLocate": False, "showCompass": False,
      "showPopup": True, "scalebarStyle": "line", "editingEnabled": False, "trackedFeatureRadius": 60, "layers": [],
      "selectTool": {"type": "selectTool", "clickToSelect": True, "advanceSketchTools": ["rectangle"]}}
lst = {"accessibleName": "High severity issues", "id": U(), "name": "High issues list", "title": "High severity issues (first 200)", "showLastUpdate": False, **STATE,
       "datasets": [ds(QH, order=["rule_ ASC", "issue_id ASC"], maxf=200)], "events": [], "type": "listWidget", "selectionMode": "none", "iconType": "symbol",
       "text": "<p><strong>{field/rule_}</strong> · {field/asset_id} ({field/system})</p><p>{field/detail}</p><p>{field/neighbourhood_name} · {field/review_status}</p>", "showFilter": True}
note = {"id": U(), "name": "About", "title": "About the data", "showLastUpdate": False, **STATE, "type": "richTextWidget",
        "text": ("<p><strong>Data:</strong> City of Edmonton Open Data drainage network, retrieved 2026-11-14. QA by Python scripts (rules R1–R9).</p>"
                 "<p><strong>Rules:</strong> R1 dangling pipe end · R2 orphan node · R3 storm/sanitary conflict · R4 year missing or placeholder · R5 duplicate pipe · R6 very short pipe · R7 rim elevation vs ground · R8 name missing · R9 small isolated group.</p>"
                 "<p>An issue means <em>needs review</em>, not a confirmed error: the open data has no diameter, material, invert or flow direction. Reviewers set the review status in the map pop-ups.</p>"
                 "<p>Independent portfolio work, not a City of Edmonton or EPCOR product.</p>")}
PREFIXES = [{"key": k, "symbol": s_, "enabled": en} for k, s_, en in [("yotta", "Y", True), ("zeta", "Z", True), ("exa", "E", True), ("peta", "P", True), ("tera", "T", True), ("giga", "G", True), ("mega", "M", True), ("kilo", "k", True), ("base", "", True), ("deci", "d", False), ("centi", "c", False), ("milli", "m", False), ("micro", "µ", False), ("nano", "n", False)]]
def item(w, h, wid): return {"width": w, "height": h, "type": "itemLayoutElement", "id": wid}
def stack(w, h, orient, els): return {"width": w, "height": h, "id": U(), "elements": els, "type": "stackLayoutElement", "orientation": orient}
layout = {"type": "dockingLayout", "rootElement": stack(1, 1, "col", [
    stack(0.3, 1, "row", [stack(1, 0.18, "col", [item(1 / 3, 1, ind1["id"]), item(1 / 3, 1, ind2["id"]), item(1 / 3, 1, ind3["id"])]),
                          item(1, 0.47, ch1["id"]), item(1, 0.35, ch2["id"])]),
    item(0.44, 1, mp["id"]),
    stack(0.26, 1, "row", [item(1, 0.6, lst["id"]), item(1, 0.4, note["id"])])])}
dash = {"version": "5.1.0", "authoringApp": "ArcGIS Dashboards", "authoringAppVersion": "5.1.0", "maxPaginationRecords": 50000,
        "maxChartRecords": 10000, "timeZone": "system", "theme": {"id": "midnight-blue", "type": "defined"},
        "numberPrefixOverrides": PREFIXES, "elementMappings": {},
        "desktopView": {"layout": layout, "type": "desktopView", "widgets": [mp, ind1, ind2, ind3, ch1, ch2, lst, note],
                        "settings": {"allowElementResizing": True, "allowElementExpansion": True, "allowReset": False},
                        "header": {"type": "header", "title": "Edmonton Drainage Network · Data Readiness and QA (Project C)",
                                   "logoImageURL": None, "logoURL": None, "logoSize": "small", "backgroundImageSizing": "fit-height",
                                   "normalBackgroundImagePlacement": "left", "horizontalBackgroundImagePlacement": "top",
                                   "showSignOutMenu": False, "subtitlePlacement": "sameLine", "showMargin": True, "menuContents": []}}}
dprops = {"type": "Dashboard", "title": "ProjectC Drainage QA Dashboard", "typeKeywords": "Dashboard,Operations Dashboard",
          "tags": "drainage, sewer, QA, dashboard, portfolio, Edmonton",
          "snippet": "QA issues on Edmonton's open drainage data by rule, system and review status (portfolio project).", "text": json.dumps(dash)}
d_item = find("ProjectC Drainage QA Dashboard", "Dashboard")
if d_item:
    d_item.update(item_properties=dprops)
else:
    d_item = add_item(dprops)
base = gis.url.split("//")[1]
print("web map:", f"https://{base}/apps/mapviewer/index.html?webmap={wm.id}")
print("dashboard:", f"https://{base}/apps/dashboards/{d_item.id}")
