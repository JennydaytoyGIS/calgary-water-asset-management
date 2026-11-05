"""
B7 - Create the inspection Dashboard from the project web map (run in ArcGIS Notebook).
Widgets: 3 indicators, inspection-status chart, condition chart, map, work-order list, data note.
The AM_WorkOrders table is added to the web map first so the Dashboard can use it.
"""
from arcgis.gis import GIS
import json, uuid

gis = GIS("home"); me = gis.users.me.username
def find(title, typ="Feature Service"):
    r = [i for i in gis.content.search(f'title:"{title}" owner:{me}', item_type=typ, max_items=50) if i.title == title]
    return r[0] if r else None

wm = find("ProjectB_Hydrant_Inspection_Map", "Web Map")
wo_item = find("AM_WorkOrders")
data = wm.get_data()
ids = {l.get("title"): l["id"] for l in data["operationalLayers"]}
data.setdefault("tables", [])
if not any(t.get("itemId") == wo_item.id for t in data["tables"]):
    data["tables"].append({"id": "am-workorders-table", "title": "AM_WorkOrders", "url": wo_item.url + "/0",
                           "itemId": wo_item.id, "layerType": "ArcGISFeatureLayer", "popupInfo": None})
    print("work-order table added to web map:", wm.update(data=json.dumps(data)))
WO_ID = [t["id"] for t in data["tables"] if t.get("itemId") == wo_item.id][0]
HYD, INSP = ids["AM_Hydrants"], ids["AM_Hydrant_Inspections"]
WM = wm.id

U = lambda: str(uuid.uuid4())
STATE = {"noDataState": {"verticalAlignment": "middle", "showTopCaption": True, "showBottomCaption": True},
         "noFilterState": {"verticalAlignment": "middle", "showTopCaption": True, "showBottomCaption": True}}
def ds(layer, group=None, oid="OBJECTID", order=None, maxf=None):
    d = {"type": "serviceDataset", "name": "main", "dataSource": {"type": "layerDataSource", "itemId": WM, "layerId": layer},
         "groupByFields": group or [], "orderByFields": order or [],
         "statisticDefinitions": [{"onStatisticField": oid, "statisticType": "count", "outStatisticFieldName": "COUNT_OID"}] if (group is not None or maxf is None) else [],
         "outFields": ["*"], "returnDistinctValues": False, "allowSourceDownload": False, "allowSummaryDownload": False}
    if maxf: d["maxFeatures"] = maxf
    return d

def indicator(name, layer, oid, label, color):
    return {"id": U(), "name": name, "showLastUpdate": False, **STATE, "datasets": [ds(layer, oid=oid)],
            "type": "indicatorWidget",
            "defaultSettings": {"topSection": {"fontSize": 80, "textInfo": {}},
                                "middleSection": {"fontSize": 160, "textInfo": {"text": "{calculated/value}"}, "textColor": color},
                                "bottomSection": {"fontSize": 80, "textInfo": {"text": label}}},
            "comparison": "none",
            "valueFormat": {"name": "value", "prefix": False, "style": "decimal", "useGrouping": True, "maximumFractionDigits": 0},
            "percentageFormat": {"name": "percentage", "prefix": False, "style": "percent", "useGrouping": True},
            "ratioFormat": {"name": "ratio", "prefix": False, "style": "decimal", "useGrouping": True, "maximumFractionDigits": 2},
            "valueType": "statistic", "noValueState": {"verticalAlignment": "middle", "showTopCaption": True, "showBottomCaption": True}}

def axis(title, angle, cat):
    a = {"type": "chartAxis", "visible": True,
         "title": {"type": "chartText", "visible": True, "content": {"type": "esriTS", "angle": angle, "font": {"family": "inherit", "style": "normal", "weight": "bold"}, "text": title}},
         "lineSymbol": {"type": "esriSLS", "style": "esriSLSSolid", "width": 1},
         "labels": {"type": "chartText", "visible": True, "content": {"type": "esriTS", "angle": 0, "font": {"family": "inherit", "style": "normal", "weight": "normal"}}},
         "grid": {"type": "esriSLS", "style": "esriSLSSolid", "width": 1}, "guides": []}
    if cat: a["scrollbar"] = {"width": 15, "gripSize": 22}
    a["valueFormat"] = {"type": "category", "characterLimit": 20} if cat else {"type": "number", "intlOptions": {"style": "decimal", "notation": "standard", "minimumFractionDigits": 0, "maximumFractionDigits": 0}}
    if not cat: a["buffer"] = True
    return a

def chart(name, title, caption, field, cat_title, null_label, color):
    sym = {"type": "esriSFS", "style": "esriSFSSolid", "color": color, "outline": {"type": "esriSLS", "style": "esriSLSSolid", "color": color, "width": 1}}
    return {"id": U(), "name": name, "title": title, "topCaption": caption, "showLastUpdate": False, **STATE,
            "datasets": [ds(HYD, group=[field], oid="ObjectId")], "dashboardItemType": "widget", "focusModeEnabled": False, "actionMode": "none", "categoryType": "groupByValues",
            "type": "serialChartWidget",
            "valueFormat": {"name": "value", "prefix": True, "style": "decimal", "useGrouping": True, "maximumFractionDigits": 0},
            "labelFormat": {"name": "label", "prefix": True, "style": "decimal", "useGrouping": True, "maximumFractionDigits": 0},
            "category": {"labelOverrides": [], "nullLabel": null_label, "blankLabel": "blank"},
            "parseDates": False, "minPeriod": "MM", "categoryAxisLabelsBehavior": "hide",
            "chartConfig": {"version": "25.1.0", "type": "chart", "orderOptions": {}, "colorMatch": False,
                            "axes": [axis(cat_title, 270, True), axis("Hydrants", 0, False)],
                            "series": [{"type": "barSeries", "id": "COUNT_OID", "name": "groupByValues", "x": field, "y": "COUNT_OID",
                                        "dataLabels": {"type": "chartText", "visible": True, "content": {"type": "esriTS", "angle": 0, "font": {"family": "inherit", "size": 12, "style": "normal", "weight": "normal"}}},
                                        "dataTooltipVisible": True, "dataTooltipReverseColor": True, "fillSymbol": sym}],
                            "legend": {"type": "chartLegend", "visible": False, "body": {"type": "esriTS", "angle": 0, "font": {"family": "inherit", "size": 12, "style": "normal", "weight": "normal"}}, "position": "bottom"},
                            "horizontalAxisLabelsBehavior": "hide", "verticalAxisLabelsBehavior": "hide", "rotated": True,
                            "cursorCrosshair": {"type": "cursorCrosshair", "verticalLineVisible": False, "horizontalLineVisible": False},
                            "stackedType": "sideBySide"}}

ind1 = indicator("Hydrants indicator", HYD, "ObjectId", "Hydrants in pilot area", "#ffffff")
ind2 = indicator("Inspections indicator", INSP, "objectid", "Inspections recorded", "#7fd6ff")
ind3 = indicator("Work orders indicator", WO_ID, "OBJECTID", "Work orders raised", "#ff8c66")
ch1 = chart("Status chart", "Inspection status", "<p>Asset register status after QC write-back</p>", "insp_status", "Status", "No status", [96, 175, 255, 255])
ch2 = chart("Condition chart", "Condition at last inspection", "<p>1 = Very good, 5 = Very poor</p>", "last_condition", "Condition", "Not inspected", [255, 170, 80, 255])
mp = {"headerBackgroundColor": "#1a4a73", "id": U(), "name": "Inspection map", "showLastUpdate": False, **STATE, "type": "mapWidget",
      "flashRepeats": 3, "itemId": WM, "mapTools": [{"type": "legendTool"}, {"type": "mapContentsTool"}, {"type": "basemapGalleryTool"}],
      "showMeasureTool": False, "showNavigation": True, "showPanRotate": False, "showLocate": False, "showCompass": False,
      "showPopup": True, "scalebarStyle": "line", "editingEnabled": False, "trackedFeatureRadius": 60, "layers": [],
      "selectTool": {"type": "selectTool", "clickToSelect": True, "advanceSketchTools": ["rectangle"]}}
lst = {"accessibleName": "Work orders", "id": U(), "name": "Work order list", "title": "Work orders (simulated CMMS)", "showLastUpdate": False, **STATE,
       "datasets": [ds(WO_ID, order=["wo_id ASC"], maxf=50)], "events": [], "type": "listWidget", "selectionMode": "none", "iconType": "symbol",
       "text": ("<p><strong>{field/wo_id}</strong> · {field/asset_id} ({field/community})</p>"
                "<p>Priority: <strong>{field/wo_priority}</strong> · Condition {field/cond_rating} · {field/defect_type}</p>"
                "<p>Status: {field/wo_status} · Origin: {field/data_origin}</p>"), "showFilter": True}
note = {"id": U(), "name": "Data note", "title": "About the data", "showLastUpdate": False, **STATE, "type": "richTextWidget",
        "text": ("<p><strong>Asset data:</strong> City of Calgary Open Data (Water Hydrants, Water Main Breaks), retrieved 2026-10-31.</p>"
                 "<p><strong>Inspection data:</strong> includes records marked <em>Simulated</em> (data_origin) to demonstrate the workflow; "
                 "field-test records are added as they are collected. Inspections are visual only.</p>"
                 "<p><strong>Pipeline:</strong> Field Maps task → Survey123 form → Python QC → asset register update → work order.</p>")}

# Dashboards 5.1 number formatting reads one entry per SI prefix; an empty list breaks serial charts
# ("Cannot read properties of undefined (reading 'enabled')").
PREFIXES = [{"key": k, "symbol": sym, "enabled": en} for k, sym, en in [("yotta", "Y", True), ("zeta", "Z", True), ("exa", "E", True), ("peta", "P", True), ("tera", "T", True), ("giga", "G", True), ("mega", "M", True), ("kilo", "k", True), ("base", "", True), ("deci", "d", False), ("centi", "c", False), ("milli", "m", False), ("micro", "\u00b5", False), ("nano", "n", False)]]

def item(w, h, wid): return {"width": w, "height": h, "type": "itemLayoutElement", "id": wid}
def stack(w, h, orient, els): return {"width": w, "height": h, "id": U(), "elements": els, "type": "stackLayoutElement", "orientation": orient}
layout = {"type": "dockingLayout", "rootElement": stack(1, 1, "col", [
    stack(0.27, 1, "row", [stack(1, 0.2, "col", [item(1 / 3, 1, ind1["id"]), item(1 / 3, 1, ind2["id"]), item(1 / 3, 1, ind3["id"])]),
                           item(1, 0.4, ch1["id"]), item(1, 0.4, ch2["id"])]),
    item(0.45, 1, mp["id"]),
    stack(0.28, 1, "row", [item(1, 0.72, lst["id"]), item(1, 0.28, note["id"])])])}

dash = {"version": "5.1.0", "authoringApp": "ArcGIS Dashboards", "authoringAppVersion": "5.1.0", "maxPaginationRecords": 50000,
        "maxChartRecords": 10000, "timeZone": "system", "theme": {"id": "midnight-blue", "type": "defined"},
        "numberPrefixOverrides": PREFIXES, "elementMappings": {},
        "desktopView": {"layout": layout, "type": "desktopView", "widgets": [mp, ind1, ind2, ind3, ch1, ch2, lst, note],
                        "settings": {"allowElementResizing": True, "allowElementExpansion": True, "allowReset": False},
                        "header": {"type": "header", "title": "Hydrant Visual Inspection · Montgomery, Parkdale & Point McKay (Project B)",
                                   "logoImageURL": None, "logoURL": None, "logoSize": "small", "backgroundImageSizing": "fit-height",
                                   "normalBackgroundImagePlacement": "left", "horizontalBackgroundImagePlacement": "top",
                                   "showSignOutMenu": False, "subtitlePlacement": "sameLine", "showMargin": True, "menuContents": []}}}

old = find("AM Hydrant Inspection Dashboard", "Dashboard")
props = {"type": "Dashboard", "title": "AM Hydrant Inspection Dashboard", "typeKeywords": "Dashboard,Operations Dashboard",
         "tags": "asset management, hydrant, inspection, dashboard, portfolio",
         "snippet": "Inspection progress, condition and work orders for the Project B hydrant pilot (includes labelled simulated data).",
         "text": json.dumps(dash)}
if old:
    print("updated:", old.update(item_properties=props)); dash_item = old
else:
    dash_item = gis.content.add(item_properties=props, folder="ProjectB_AM")
print("dashboard:", dash_item.id, f"https://{gis.url.split('//')[1]}/apps/dashboards/{dash_item.id}")
