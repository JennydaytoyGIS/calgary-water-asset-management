"""C13: Web map and dashboard for the ponding screening (run in an ArcGIS Notebook).
Uses the hosted layer "ProjectC Ponding Screening" (published from outputs/agol/ponding_screening_agol.gdb.zip).
Re-running updates the existing items.
"""
from arcgis.gis import GIS
import json, uuid

gis = GIS("home"); me = gis.users.me.username
FOLDER = "ProjectC_Edmonton"
def find(title, typ):
    r = [i for i in gis.content.search(f'title:"{title}" owner:{me}', item_type=typ, max_items=50) if i.title == title]
    return r[0] if r else None
def add_item(props):
    it = gis.content.add(item_properties=props)
    try: it.move(FOLDER)
    except Exception as e: print("move:", e)
    return it

svc = find("ProjectC Ponding Screening", "Feature Service")
try: svc.move(FOLDER)
except Exception as e: print("move:", e)
lyr = {l.properties.name: l for l in svc.layers}
print("layers:", {k: v.properties.id for k, v in lyr.items()})
print("bluespot fields:", [f["name"] for f in lyr["bluespots_ottewell"].properties.fields])
url = lambda n: f"{svc.url}/{lyr[n].properties.id}"

def line(c, w): return {"type": "esriSLS", "style": "esriSLSSolid", "color": c, "width": w}
def fill(c, oc, ow): return {"type": "esriSFS", "style": "esriSFSSolid", "color": c, "outline": line(oc, ow)}
PRI = {"High": [192, 57, 43], "Medium": [230, 159, 0], "Low": [154, 165, 177]}
bs_renderer = {"type": "uniqueValue", "field1": "priority", "uniqueValueInfos": [
    {"value": k, "label": f"{k} priority", "symbol": fill(v + [110 if k != "Low" else 60], v + [255], 1.6 if k != "Low" else 0.6)} for k, v in PRI.items()]}
nb_renderer = {"type": "classBreaks", "field": "rate_per_km2", "minValue": 0, "classBreakInfos": [
    {"classMaxValue": mx, "label": lab, "symbol": fill(c, [255, 255, 255, 200], 0.4)} for mx, lab, c in
    [(2, "Under 2", [239, 243, 255, 210]), (5, "2–5", [189, 215, 231, 210]), (10, "5–10", [107, 174, 214, 210]), (20, "10–20", [49, 130, 189, 210]), (1000, "20 or more", [8, 81, 156, 210])]]}

BS_ACTION = """
var p = $feature.priority; var cov = $feature.coverage;
if ($feature.terrain_feature == 1) { return 'Ravine head closed by road fill in the surface; check the culvert before treating it as ponding.' }
var a = When(cov == 'Uncovered', 'No catch basin within 40 m of the lowest point: check whether an inlet is missing or the low point is mapped wrongly.',
             cov == 'Partial', 'Nearest catch basin is 15–40 m from the lowest point: check grading towards it and its condition after rain.',
             'An inlet is close to the lowest point: check it is clear and sized for the storage behind it.');
return a;
"""
bs_popup = {"title": "{bluespot_id} · {priority} priority",
            "expressionInfos": [{"name": "act", "title": "What to check", "expression": BS_ACTION, "returnType": "string"}],
            "popupElements": [{"type": "text", "text": "<p>Storage <b>{volume_m3} m³</b> over {area_m2} m², up to {max_depth_m} m deep.</p><p>Nearest catch basin {dist_cb_m} m from the lowest point ({coverage}); {cb_inside_or_5m} catch basins in or within 5 m; {buildings_touching} buildings touching.</p><p><b>What to check:</b> {expression/act}</p>"}]}
nb_popup = {"title": "{neighbourhood_name}",
            "expressionInfos": [{"name": "rate", "title": "Rate", "returnType": "number", "expression": "Round($feature.rate_per_km2, 1)"},
                                {"name": "pred", "title": "Predicted", "returnType": "number", "expression": "Round(Exp($feature.pred_log_rate) - 1, 1)"},
                                {"name": "gap", "title": "Gap", "returnType": "string",
                                 "expression": "var d = $feature.residual; return When(d > 0.5, 'more reports than the model expects', d < -0.5, 'fewer reports than the model expects', 'about as many reports as the model expects')"}],
            "popupElements": [{"type": "text", "text": "<p><b>{reports}</b> rain-season ponding reports (May–Sep 2023–2026), <b>{expression/rate}</b> per km² (rank {obs_rank} of 269).</p><p>Model estimate: {expression/pred} per km² (rank {pred_rank}); {expression/gap}.</p><p>Factors pushing reports up here: <b>{driver_1}</b>, {driver_2}, {driver_3}.</p>"}]}
asset_popup = {"title": "{asset_id} · {asset_type}", "popupElements": [{"type": "text", "text": "<p>{system}, built {year_built}. Serves {bluespot_id} ({priority} priority), {dist_m} m away.</p>"}]}

def op(name, title, renderer=None, popup=None, min_scale=0, max_scale=0, opacity=1, where=None, visible=True):
    d = {"id": f"{name}-{uuid.uuid4().hex[:6]}", "title": title, "url": url(name), "itemId": svc.id, "layerType": "ArcGISFeatureLayer",
         "visibility": visible, "opacity": opacity, "layerDefinition": {"minScale": min_scale, "maxScale": max_scale}}
    if renderer: d["layerDefinition"]["drawingInfo"] = {"renderer": renderer}
    if where: d["layerDefinition"]["definitionExpression"] = where
    if popup: d["popupInfo"] = popup
    return d

layers = [
    op("nb_model", "Rain-season ponding reports per km² (neighbourhood)", nb_renderer, nb_popup, max_scale=60000),
    op("ottewell_boundary", "Ottewell", {"type": "simple", "symbol": {"type": "esriSFS", "style": "esriSFSNull", "outline": line([192, 57, 43, 255], 2)}}),
    op("bluespots_ottewell", "Bluespots (Ottewell)", bs_renderer, bs_popup, min_scale=60000, where="terrain_feature = 0"),
    op("priority_pipes", "Pipes near priority bluespots", {"type": "uniqueValue", "field1": "system", "uniqueValueInfos": [
        {"value": "STORM", "label": "Storm", "symbol": line([44, 127, 184, 255], 1.4)}, {"value": "COMBINED", "label": "Combined", "symbol": line([123, 94, 167, 255], 1.4)},
        {"value": "SANITARY", "label": "Sanitary", "symbol": line([217, 95, 14, 255], 1.0)}]}, asset_popup, min_scale=40000),
    op("priority_catch_basins", "Catch basins near priority bluespots", {"type": "simple", "symbol": {"type": "esriSMS", "style": "esriSMSCircle", "color": [31, 41, 51, 255], "size": 5, "outline": {"color": [255, 255, 255, 255], "width": 0.7}}}, asset_popup, min_scale=40000),
]
wm_data = {"operationalLayers": layers,
           "baseMap": {"title": "Light Gray Canvas", "baseMapLayers": [{"id": "gray-base", "title": "World Light Gray Base", "layerType": "ArcGISTiledMapServiceLayer", "visibility": True, "opacity": 1,
                                                                     "url": "https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer"}]},
           "spatialReference": {"wkid": 102100, "latestWkid": 3857}, "authoringApp": "ArcGIS Notebook", "authoringAppVersion": "1", "version": "2.31",
           "initialState": {"viewpoint": {"targetGeometry": {"xmin": -12654000, "ymin": 7060000, "xmax": -12590000, "ymax": 7120000, "spatialReference": {"wkid": 102100}}}}}
wm_props = {"type": "Web Map", "title": "ProjectC Ponding Screening Map", "tags": "flooding, ponding, drainage, 311, machine learning, Edmonton, portfolio",
            "snippet": "Where water ponds in Ottewell when the sewers are full, and what explains 311 ponding reports across Edmonton (portfolio project).",
            "extent": "-113.72,53.39,-113.27,53.72", "text": json.dumps(wm_data)}
wm = find("ProjectC Ponding Screening Map", "Web Map")
if wm: wm.update(item_properties=wm_props)
else: wm = add_item(wm_props)
ids = {l["title"]: l["id"] for l in layers}
BS, NB = ids["Bluespots (Ottewell)"], ids["Rain-season ponding reports per km² (neighbourhood)"]

U = lambda: str(uuid.uuid4())
STATE = {"noDataState": {"verticalAlignment": "middle", "showTopCaption": True, "showBottomCaption": True},
         "noFilterState": {"verticalAlignment": "middle", "showTopCaption": True, "showBottomCaption": True}}
def ds(layer, group=None, order=None, maxf=None, stat=None, extra=None):
    d = {"type": "serviceDataset", "name": "main", "dataSource": {"type": "layerDataSource", "itemId": wm.id, "layerId": layer},
         "groupByFields": group or [], "orderByFields": order or [],
         "statisticDefinitions": [stat or {"onStatisticField": "OBJECTID", "statisticType": "count", "outStatisticFieldName": "COUNT_OID"}] if (group is not None or maxf is None) else [],
         "outFields": ["*"], "returnDistinctValues": False, "allowSourceDownload": False, "allowSummaryDownload": False}
    if maxf: d["maxFeatures"] = maxf
    if extra: d["statisticDefinitions"].append(extra)
    return d
def indicator(name, layer, label, color, stat=None):
    return {"id": U(), "name": name, "showLastUpdate": False, **STATE, "datasets": [ds(layer, stat=stat)], "type": "indicatorWidget",
            "defaultSettings": {"topSection": {"fontSize": 80, "textInfo": {}}, "middleSection": {"fontSize": 160, "textInfo": {"text": "{calculated/value}"}, "textColor": color},
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
    if not cat: a["buffer"] = False; a["minimum"] = 0
    return a
def chart(name, title, caption, layer, field, val_title, color, order=None, extra=None):
    sym = {"type": "esriSFS", "style": "esriSFSSolid", "color": color, "outline": {"type": "esriSLS", "style": "esriSLSSolid", "color": color, "width": 1}}
    return {"id": U(), "name": name, "title": title, "topCaption": caption, "showLastUpdate": False, **STATE,
            "datasets": [ds(layer, group=[field], order=order, extra=extra)], "dashboardItemType": "widget", "focusModeEnabled": False, "actionMode": "none", "categoryType": "groupByValues",
            "type": "serialChartWidget", "valueFormat": {"name": "value", "prefix": True, "style": "decimal", "useGrouping": True, "maximumFractionDigits": 0},
            "labelFormat": {"name": "label", "prefix": True, "style": "decimal", "useGrouping": True, "maximumFractionDigits": 0},
            "category": {"labelOverrides": [], "nullLabel": "None", "blankLabel": "blank"}, "parseDates": False, "minPeriod": "MM", "categoryAxisLabelsBehavior": "hide",
            "chartConfig": {"version": "25.1.0", "type": "chart", "orderOptions": {}, "colorMatch": False, "axes": [axis("", 270, True), axis(val_title, 0, False)],
                            "series": [{"type": "barSeries", "id": "COUNT_OID", "name": "groupByValues", "x": field, "y": "COUNT_OID",
                                        "dataLabels": {"type": "chartText", "visible": True, "content": {"type": "esriTS", "angle": 0, "font": {"family": "inherit", "size": 12, "style": "normal", "weight": "normal"}}},
                                        "dataTooltipVisible": True, "dataTooltipReverseColor": True, "fillSymbol": sym}],
                            "legend": {"type": "chartLegend", "visible": False, "body": {"type": "esriTS", "angle": 0, "font": {"family": "inherit", "size": 12, "style": "normal", "weight": "normal"}}, "position": "bottom"},
                            "horizontalAxisLabelsBehavior": "hide", "verticalAxisLabelsBehavior": "hide", "rotated": True,
                            "cursorCrosshair": {"type": "cursorCrosshair", "verticalLineVisible": False, "horizontalLineVisible": False}, "stackedType": "sideBySide"}}

ind1 = indicator("Reports", NB, "Rain-season reports", "#7fd6ff", {"onStatisticField": "reports", "statisticType": "sum", "outStatisticFieldName": "value"})
ind2 = indicator("Neighbourhoods", NB, "Neighbourhoods modelled", "#ffffff")
ind3 = indicator("Bluespots", BS, "Bluespots in Ottewell", "#ffd166")
ch1 = chart("Priority", "Ottewell bluespots by priority", "<p>High: large storage, inlet over 15 m away, buildings exposed</p>", BS, "priority", "Bluespots", [255, 140, 102, 255],
           order=["min_vol DESC"], extra={"onStatisticField": "volume_m3", "statisticType": "min", "outStatisticFieldName": "min_vol"})
ch2 = chart("Coverage", "Catch basin coverage at the lowest point", "<p>Covered ≤ 15 m · Partial ≤ 40 m · Uncovered > 40 m</p>", BS, "coverage", "Bluespots", [127, 214, 255, 255])
mp = {"headerBackgroundColor": "#1a4a73", "id": U(), "name": "Map", "showLastUpdate": False, **STATE, "type": "mapWidget", "flashRepeats": 3, "itemId": wm.id,
      "mapTools": [{"type": "legendTool"}, {"type": "mapContentsTool"}, {"type": "basemapGalleryTool"}], "showMeasureTool": False, "showNavigation": True,
      "showPanRotate": False, "showLocate": False, "showCompass": False, "showPopup": True, "scalebarStyle": "line", "editingEnabled": False, "trackedFeatureRadius": 60,
      "layers": [], "selectTool": {"type": "selectTool", "clickToSelect": True, "advanceSketchTools": ["rectangle"]}}
lst = {"accessibleName": "Bluespots", "id": U(), "name": "Bluespot list", "title": "Ottewell bluespots, high priority first", "showLastUpdate": False, **STATE,
       "datasets": [ds(BS, order=["priority ASC", "volume_m3 DESC"], maxf=60)], "events": [], "type": "listWidget", "selectionMode": "none", "iconType": "symbol",
       "text": "<p><strong>{field/bluespot_id}</strong> · {field/priority} · {field/volume_m3} m³</p><p>Nearest inlet {field/dist_cb_m} m ({field/coverage}) · {field/buildings_touching} buildings</p>", "showFilter": True}
findings = {"id": U(), "name": "Findings", "title": "What the model says", "showLastUpdate": False, **STATE, "type": "richTextWidget",
            "text": ("<p><strong>Question:</strong> what explains where people report ponding after rain?</p>"
                     "<p><strong>Terrain alone explains nothing</strong> (cross-validated R² below zero). Adding drainage factors raises it to <strong>0.25</strong> (Spearman 0.54); population adds almost nothing.</p>"
                     "<p><strong>Strongest factors:</strong> older neighbourhoods report more; so do neighbourhoods with more catch basins and pipes per km², which mostly reflects how much street there is to report from; a larger share of land in depressions adds to it, while steeper ground reduces it.</p>"
                     "<p>Residuals still cluster (Moran's I 0.16), so something spatial is missing, for example rainfall differences or street length.</p>")}
note = {"id": U(), "name": "About", "title": "About the data", "showLastUpdate": False, **STATE, "type": "richTextWidget",
        "text": ("<p>311 'Ponding' requests (roads, alleys, sidewalks), May–September 2023–2026, City of Edmonton Open Data; drainage network and contours from the same source (0.5 m in Ottewell, 2.5 m citywide). "
                 "Bluespots: depressions in a 1 m surface from the contours, assuming the sewers are full. A screening, not a hydraulic model.</p>"
                 "<p>Independent portfolio work by Jieni Zhao, not a City of Edmonton or EPCOR product.</p>")}
PREFIXES = [{"key": k, "symbol": s_, "enabled": en} for k, s_, en in [("yotta", "Y", True), ("zeta", "Z", True), ("exa", "E", True), ("peta", "P", True), ("tera", "T", True), ("giga", "G", True), ("mega", "M", True), ("kilo", "k", True), ("base", "", True), ("deci", "d", False), ("centi", "c", False), ("milli", "m", False), ("micro", "µ", False), ("nano", "n", False)]]
def item(w, h, wid): return {"width": w, "height": h, "type": "itemLayoutElement", "id": wid}
def stack(w, h, o, els): return {"width": w, "height": h, "id": U(), "elements": els, "type": "stackLayoutElement", "orientation": o}
layout = {"type": "dockingLayout", "rootElement": stack(1, 1, "col", [
    stack(0.28, 1, "row", [stack(1, 0.17, "col", [item(1 / 3, 1, ind1["id"]), item(1 / 3, 1, ind2["id"]), item(1 / 3, 1, ind3["id"])]),
                          item(1, 0.45, findings["id"]), item(1, 0.38, ch1["id"])]),
    item(0.46, 1, mp["id"]),
    stack(0.26, 1, "row", [item(1, 0.34, ch2["id"]), item(1, 0.42, lst["id"]), item(1, 0.24, note["id"])])])}
dash = {"version": "5.1.0", "authoringApp": "ArcGIS Dashboards", "authoringAppVersion": "5.1.0", "maxPaginationRecords": 50000, "maxChartRecords": 10000,
        "timeZone": "system", "theme": {"id": "midnight-blue", "type": "defined"}, "numberPrefixOverrides": PREFIXES, "elementMappings": {},
        "desktopView": {"layout": layout, "type": "desktopView", "widgets": [mp, ind1, ind2, ind3, findings, ch1, ch2, lst, note],
                        "settings": {"allowElementResizing": True, "allowElementExpansion": True, "allowReset": False},
                        "header": {"type": "header", "title": "Where water ponds in Edmonton · bluespot screening and an explainable model of 311 reports (Project C)",
                                   "logoImageURL": None, "logoURL": None, "logoSize": "small", "backgroundImageSizing": "fit-height", "normalBackgroundImagePlacement": "left",
                                   "horizontalBackgroundImagePlacement": "top", "showSignOutMenu": False, "subtitlePlacement": "sameLine", "showMargin": True, "menuContents": []}}}
dprops = {"type": "Dashboard", "title": "ProjectC Ponding Screening Dashboard", "typeKeywords": "Dashboard,Operations Dashboard",
          "tags": "flooding, ponding, drainage, 311, machine learning, dashboard, portfolio", "snippet": "Bluespot screening for Ottewell and an explainable model of 311 ponding reports (portfolio project).",
          "text": json.dumps(dash)}
d_item = find("ProjectC Ponding Screening Dashboard", "Dashboard")
if d_item: d_item.update(item_properties=dprops)
else: d_item = add_item(dprops)
base = gis.url.split("//")[1]
print("web map:", f"https://{base}/apps/mapviewer/index.html?webmap={wm.id}")
print("dashboard:", f"https://{base}/apps/dashboards/{d_item.id}")
