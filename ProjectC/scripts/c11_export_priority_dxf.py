"""C11: Hand-over for engineers. Ottewell bluespots and the inlets and pipes around priority ones, as DXF.
Layers: BLUESPOT-HIGH / -MEDIUM / -LOW (closed polylines), CB-NEAR-PRIORITY (blocks with ID), PIPE-NEAR-PRIORITY.
Output: cad/ottewell_bluespots.dxf and a read-back count check (cad/ottewell_bluespots_readback.md)
"""
import pathlib
import geopandas as gpd, ezdxf
ROOT = pathlib.Path(__file__).resolve().parents[1]
B = ROOT / "data" / "clean" / "edmonton_bluespots.gpkg"

def rings(g):
    polys = g.geoms if g.geom_type == "MultiPolygon" else [g]
    for p in polys:
        yield list(p.exterior.coords)

def main():
    bs = gpd.read_file(B, layer="bluespots_ottewell"); bs = bs[~bs.terrain_feature]
    pa = gpd.read_file(B, layer="priority_assets_ottewell")
    doc = ezdxf.new("R2018", setup=True); doc.header["$INSUNITS"] = 6; msp = doc.modelspace(); doc.appids.new("DRN")
    for n, c in [("BLUESPOT-HIGH", 1), ("BLUESPOT-MEDIUM", 30), ("BLUESPOT-LOW", 8), ("CB-NEAR-PRIORITY", 7), ("PIPE-NEAR-PRIORITY", 5)]:
        doc.layers.add(n, color=c)
    blk = doc.blocks.new("CB"); blk.add_circle((0, 0), 0.5); blk.add_attdef("ASSET_ID", (0.7, 0.2), dxfattribs={"height": 0.3})
    n_bs = {}
    for _, b in bs.iterrows():
        lyr = f"BLUESPOT-{b.priority.upper()}"
        for ring in rings(b.geometry):
            e = msp.add_lwpolyline(ring, close=True, dxfattribs={"layer": lyr}); e.set_xdata("DRN", [(1000, b.bluespot_id), (1000, f"vol={int(b.volume_m3)} m3; maxdepth={b.max_depth_m} m")])
            n_bs[lyr] = n_bs.get(lyr, 0) + 1
    cbs = pa[pa.asset_type == "catch basin"].drop_duplicates("asset_id"); pps = pa[pa.asset_type == "pipe"].drop_duplicates("asset_id")
    for _, a in cbs.iterrows():
        msp.add_blockref("CB", (a.geometry.x, a.geometry.y), dxfattribs={"layer": "CB-NEAR-PRIORITY"}).add_auto_attribs({"ASSET_ID": a.asset_id})
    for _, a in pps.iterrows():
        e = msp.add_lwpolyline(list(a.geometry.coords), dxfattribs={"layer": "PIPE-NEAR-PRIORITY"}); e.set_xdata("DRN", [(1000, a.asset_id), (1000, a.system)])
    out = ROOT / "cad" / "ottewell_bluespots.dxf"; doc.saveas(out)
    back = ezdxf.readfile(out).modelspace()
    rows = [(l, n, len(back.query(f'LWPOLYLINE[layer=="{l}"]'))) for l, n in sorted(n_bs.items())]
    rows += [("CB-NEAR-PRIORITY", len(cbs), len(back.query('INSERT[layer=="CB-NEAR-PRIORITY"]'))), ("PIPE-NEAR-PRIORITY", len(pps), len(back.query('LWPOLYLINE[layer=="PIPE-NEAR-PRIORITY"]')))]
    ok = all(a == b for _, a, b in rows)
    txt = ["# DXF read-back check: Ottewell bluespots", "", "| Layer | Written | Read back |", "|---|---|---|"] + [f"| {l} | {a} | {b} |" for l, a, b in rows] + ["", f"Result: **{'all counts match' if ok else 'MISMATCH'}**."]
    (ROOT / "cad" / "ottewell_bluespots_readback.md").write_text("\n".join(txt) + "\n"); print("\n".join(txt))

if __name__ == "__main__":
    main()
