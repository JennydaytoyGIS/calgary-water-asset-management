"""C3: Check the standardized drainage network against QA rules and connectivity.

Rules (thresholds in metres, EPSG:3776):
  R1  Dangling pipe end: no node (manhole, catch basin, outfall, pump station) and no other pipe within TOL.
  R2  Orphan node: a manhole with no pipe within TOL, or a catch basin with no lead or pipe within TOL.
  R3  System conflict: a storm pipe meets a sanitary manhole or pipe (or the reverse) at its end.
  R4  Construction year is a placeholder (0 or 9999), missing or out of range.
  R5  Duplicate pipe: identical geometry (in either direction) recorded twice.
  R6  Very short pipe, shorter than SHORT_M.
  R7  Rim elevation is zero/missing, or differs from the ground surface built from the
      0.5 m contours by more than RIM_DIFF_M (pilot areas only).
  R8  Neighbourhood or road name missing after standardization.
  R9  Small isolated sub-network: fewer than MIN_COMPONENT pipes, not connected to the rest
      of the network, an outfall, a pump station or a stormwater pond.

Every issue is a point (pipe end, node, or pipe midpoint) with a review status, so it can be
reviewed in the web app. Results are the same every time the script is run on the same data.

Outputs: data/clean/edmonton_drainage_qa.gpkg (qa_issues, pipes_network),
         outputs/qa_issues.csv, outputs/qa_summary.csv, docs/qa_report_<date>.md
Usage:   python scripts/c3_qc_rules.py
"""
import datetime as dt
import pathlib
import shutil
import tempfile
import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
from scipy.interpolate import LinearNDInterpolator
from shapely.geometry import Point

TOL = 0.5
SHORT_M = 1.0
RIM_DIFF_M = 1.0
MIN_COMPONENT = 5
SEVERITY = {"R1": "High", "R3": "High", "R2": "Medium", "R5": "Medium", "R7": "Medium",
            "R9": "Medium", "R4": "Low", "R6": "Low", "R8": "Low"}
RULE_NAME = {"R1": "Dangling pipe end", "R2": "Orphan node", "R3": "Storm/sanitary conflict",
             "R4": "Construction year placeholder or missing", "R5": "Duplicate pipe",
             "R6": "Very short pipe", "R7": "Rim elevation inconsistent with ground",
             "R8": "Neighbourhood or road name missing", "R9": "Small isolated sub-network"}

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "clean" / "edmonton_drainage.gpkg"
FINAL = ROOT / "data" / "clean" / "edmonton_drainage_qa.gpkg"
WORK = pathlib.Path(tempfile.mkdtemp())
CRS = 3776
OPPOSITE = {("STORM", "SANITARY"), ("SANITARY", "STORM")}


def load(layer):
    return gpd.read_file(WORK / "src.gpkg", layer=layer)


def issue(rule, df, geom, detail, value=None):
    out = gpd.GeoDataFrame({
        "rule": rule, "rule_name": RULE_NAME[rule], "severity": SEVERITY[rule],
        "asset_id": df["asset_id"].values, "asset_class": df["asset_id"].str.split("-").str[0].values,
        "system": df["system"].values, "neighbourhood_name": df["neighbourhood_name"].values,
        "pilot": df["pilot"].values, "detail": detail,
        "value": np.nan if value is None else np.asarray(value, dtype=float),
    }, geometry=list(geom), crs=CRS)
    return out


def pipe_ends(p):
    rows = []
    for aid, sysm, g in zip(p.asset_id, p.system, p.geometry):
        rows.append((aid, sysm, "start", Point(g.coords[0])))
        rows.append((aid, sysm, "end", Point(g.coords[-1])))
    return gpd.GeoDataFrame(rows, columns=["asset_id", "system", "end", "geometry"], crs=CRS)


def nearest(left, right, cols):
    j = gpd.sjoin_nearest(left, right[cols + ["geometry"]], how="left", distance_col="dist")
    return j[~j.index.duplicated()]


def main():
    shutil.copyfile(SRC, WORK / "src.gpkg")
    p, mh, cb, cbl = load("pipes"), load("manholes"), load("catch_basins"), load("cb_leads")
    out_, ps = load("outfalls"), load("pump_stations")
    nodes = gpd.GeoDataFrame(pd.concat([d[["asset_id", "system", "geometry"]] for d in (mh, cb, out_, ps)], ignore_index=True), crs=CRS)
    issues = []

    # Pipe ends against nodes and other pipes
    ends = pipe_ends(p)
    jn = nearest(ends, nodes.rename(columns={"asset_id": "node_id", "system": "node_sys"}), ["node_id", "node_sys"])
    ends["node_id"], ends["node_sys"], ends["d_node"] = jn["node_id"], jn["node_sys"], jn["dist"]
    off = ends[ends.d_node > TOL].copy()
    buf = off.copy(); buf["geometry"] = off.buffer(TOL)
    other = p[["asset_id", "system", "geometry"]].rename(columns={"asset_id": "other_id", "system": "other_sys"})
    hit = gpd.sjoin(buf, other, predicate="intersects")
    hit = hit[hit.asset_id != hit.other_id]
    off["touch_pipe"] = off.index.isin(hit.index)
    attrs = p.set_index("asset_id")[["neighbourhood_name", "pilot"]]

    # R1 dangling ends
    d = off[~off.touch_pipe].join(attrs, on="asset_id")
    issues.append(issue("R1", d, d.geometry, "Pipe " + d["end"] + " has no node or pipe within 0.5 m; nearest node at " + d.d_node.round(1).astype(str) + " m", d.d_node))

    # R3 storm/sanitary conflicts. An end only conflicts when every node or pipe it meets
    # belongs to the opposite system (manholes of both systems often sit side by side).
    eb = ends.copy(); eb["geometry"] = ends.buffer(TOL)
    en = gpd.sjoin(eb, nodes.rename(columns={"asset_id": "node_id2", "system": "nsys"}), predicate="intersects")
    node_sys = en.groupby(level=0)["nsys"].agg(set)
    pipe_sys = hit.groupby(level=0)["other_sys"].agg(set)
    met = node_sys.combine(pipe_sys, lambda a, b: (a if isinstance(a, set) else set()) | (b if isinstance(b, set) else set()), fill_value=set())
    opp = {"STORM": "SANITARY", "SANITARY": "STORM"}
    conflict = [i for i, ss in met.items()
                if ends.at[i, "system"] in opp and opp[ends.at[i, "system"]] in ss
                and not ({ends.at[i, "system"], "COMBINED"} & ss)]
    c = ends.loc[conflict].join(attrs, on="asset_id")
    c["met"] = [", ".join(sorted(met[i])) for i in conflict]
    issues.append(issue("R3", c, c.geometry, c.system + " pipe " + c["end"] + " meets only " + c.met + " assets"))

    # R2 orphan manholes and catch basins
    jm = nearest(mh, p.assign(pid=p.asset_id), ["pid"])
    o1 = mh[jm.dist.values > TOL]
    issues.append(issue("R2", o1, o1.geometry, "Manhole has no pipe within 0.5 m", jm.dist.values[jm.dist.values > TOL]))
    lines = gpd.GeoDataFrame(pd.concat([cbl[["asset_id", "geometry"]], p[["asset_id", "geometry"]]], ignore_index=True), crs=CRS)
    jc = nearest(cb, lines.rename(columns={"asset_id": "lid"}), ["lid"])
    o2 = cb[jc.dist.values > TOL]
    issues.append(issue("R2", o2, o2.geometry, "Catch basin has no lead or pipe within 0.5 m", jc.dist.values[jc.dist.values > TOL]))

    # R4 year placeholders (all asset layers)
    for d in (p, mh, cb, cbl, out_, ps):
        bad = d[d.year_flag != "valid"]
        g = bad.geometry.interpolate(0.5, normalized=True) if bad.geom_type.str.contains("Line").any() else bad.geometry.representative_point()
        issues.append(issue("R4", bad, g, "Construction year is " + bad.year_flag + " (raw value " + bad.year_raw.astype(str) + ")"))

    # R5 duplicates
    key = p.geometry.normalize().to_wkb()
    dup = p[key.duplicated(keep="first")]
    issues.append(issue("R5", dup, dup.geometry.interpolate(0.5, normalized=True), "Same geometry as another pipe"))

    # R6 very short pipes
    sh = p[p.length_m < SHORT_M]
    issues.append(issue("R6", sh, sh.geometry.interpolate(0.5, normalized=True), "Pipe is " + sh.length_m.round(2).astype(str) + " m long", sh.length_m))

    # R7 rim elevation vs ground (pilot areas)
    cont = load("contours_pilot")
    pts = cont.geometry.segmentize(2.0).get_coordinates(index_parts=False)
    pts["z"] = cont.elevation.reindex(pts.index).values
    pts = pts.drop_duplicates(["x", "y"])
    surf = LinearNDInterpolator(pts[["x", "y"]].values, pts["z"].values)
    for d, label in ((mh, "Manhole"), (cb, "Catch basin")):
        q = d[d.pilot.notna()].copy()
        q["ground"] = surf(np.c_[q.geometry.x, q.geometry.y])
        q["diff"] = q.rim_elev - q.ground
        bad = q[(q.rim_flag != "valid") | (q["diff"].abs() > RIM_DIFF_M)]
        txt = np.where(bad.rim_flag != "valid", label + " rim elevation is " + bad.rim_flag,
                       label + " rim " + bad.rim_elev.round(2).astype(str) + " m vs ground " + bad.ground.round(2).astype(str) + " m")
        issues.append(issue("R7", bad, bad.geometry, txt, bad["diff"]))
        q[["asset_id", "rim_elev", "ground", "diff"]].to_csv(ROOT / "outputs" / f"rim_vs_ground_{label.lower().replace(' ', '_')}.csv", index=False)

    # R8 missing names
    for d in (p, mh, cb):
        bad = d[d.neighbourhood_name.isna() | d.road_name.isna()]
        g = bad.geometry.interpolate(0.5, normalized=True) if bad.geom_type.str.contains("Line").any() else bad.geometry
        what = np.where(bad.neighbourhood_name.isna(), "neighbourhood name", "road name")
        issues.append(issue("R8", bad, g, pd.Series(what, index=bad.index).radd("Missing ")))

    # R9 connectivity. Pipes are linked only through their ends (to a node within TOL, or to
    # another pipe they end on), so pipes that merely cross in plan view are not joined.
    G = nx.Graph()
    G.add_nodes_from("P:" + p.asset_id)
    G.add_edges_from(zip("P:" + en.asset_id, "N:" + en.node_id2))
    G.add_edges_from(zip("P:" + hit.asset_id, "P:" + hit.other_id))
    terminals = set("N:" + pd.concat([out_.asset_id, ps.asset_id]))
    comp, sizes = {}, {}
    for k, cset in enumerate(sorted(nx.connected_components(G), key=lambda c: sum(n.startswith("P:") for n in c), reverse=True)):
        pipes_in = [n[2:] for n in cset if n.startswith("P:")]
        if not pipes_in:
            continue
        for a in pipes_in:
            comp[a] = k
        sizes[k] = (len(pipes_in), bool(cset & terminals))
    p["component"] = p.asset_id.map(comp)
    p["component_pipes"] = p.component.map(lambda k: sizes[k][0])
    # Storm pipes often discharge into a stormwater pond rather than an outfall,
    # so a group whose pipe ends within 5 m of a pond also counts as connected.
    swm = load("swm_facilities")
    near_pond = set(gpd.sjoin(gpd.GeoDataFrame(ends[["asset_id"]], geometry=ends.buffer(5.0), crs=CRS), swm[["geometry"]], predicate="intersects").asset_id)
    pond_comp = set(p.loc[p.asset_id.isin(near_pond), "component"])
    p["component_terminal"] = p.component.map(lambda k: sizes[k][1] or k in pond_comp)
    small = p[(p.component_pipes < MIN_COMPONENT) & (~p.component_terminal)]
    issues.append(issue("R9", small, small.geometry.interpolate(0.5, normalized=True),
                        "Part of an isolated group of " + small.component_pipes.astype(str) + " pipe(s) with no outfall, pump station or pond", small.component_pipes))

    qa = gpd.GeoDataFrame(pd.concat(issues, ignore_index=True), crs=CRS)
    qa = qa.sort_values(["rule", "asset_id"]).reset_index(drop=True)
    qa.insert(0, "issue_id", [f"QA-{i:06d}" for i in range(1, len(qa) + 1)])
    qa["review_status"] = "Not reviewed"
    qa["review_note"] = ""
    qa["run_date"] = dt.date.today().isoformat()

    out = WORK / "qa.gpkg"
    qa.to_file(out, layer="qa_issues", driver="GPKG")
    p.to_file(out, layer="pipes_network", driver="GPKG")
    shutil.copyfile(out, FINAL)
    (ROOT / "outputs").mkdir(exist_ok=True)
    qa.drop(columns="geometry").to_csv(ROOT / "outputs" / "qa_issues.csv", index=False)

    summ = qa.groupby(["rule", "rule_name", "severity"]).agg(issues=("issue_id", "size"), assets=("asset_id", "nunique")).reset_index()
    by_sys = qa.pivot_table(index="rule", columns="system", values="issue_id", aggfunc="count", fill_value=0)
    by_pilot = qa[qa.pilot.notna()].pivot_table(index="rule", columns="pilot", values="issue_id", aggfunc="count", fill_value=0)
    summ = summ.merge(by_pilot, left_on="rule", right_index=True, how="left").fillna(0)
    summ.to_csv(ROOT / "outputs" / "qa_summary.csv", index=False)
    comp_stats = p.groupby("component").agg(pipes=("asset_id", "size"), km=("length_m", lambda s: s.sum() / 1000)).sort_values("pipes", ascending=False)

    print(summ.to_string(index=False))
    print("\nby system\n", by_sys.to_string())
    print("\ncomponents:", len(comp_stats), "| largest 5 (pipes, km):", comp_stats.head(5).round(1).values.tolist())
    big = p[p.component == comp_stats.index[0]]
    print("largest component by system:", big.system.value_counts().to_dict())
    print("components with <5 pipes:", (comp_stats.pipes < MIN_COMPONENT).sum())
    print("pipe ends:", len(ends), "| at node:", (ends.d_node <= TOL).sum(), "| join another pipe:", int(off.touch_pipe.sum()), "| dangling:", int((~off.touch_pipe).sum()))


if __name__ == "__main__":
    main()
