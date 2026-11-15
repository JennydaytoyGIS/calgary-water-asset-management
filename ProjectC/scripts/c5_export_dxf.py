"""C5: Export a pilot neighbourhood's drainage network to CAD (DXF) for engineers, then read it back.

- One layer per system (DRN-STORM, DRN-SANITARY, DRN-COMBINED, DRN-FDN), pipes as polylines.
- Manholes as blocks with attributes (asset ID, system, rim elevation, year built).
- QA issues on their own layer (DRN-QA-ISSUES) so a reviewer can switch them on and off.
- Coordinates in NAD83 / Alberta 3TM 114W (EPSG:3776), metres.
The read-back counts entities per layer and compares them with the source.

Outputs: cad/<pilot>_drainage.dxf, cad/<pilot>_readback.md
Usage:   python scripts/c5_export_dxf.py [pilot]   (default: Ottewell)
"""
import pathlib
import sys
import geopandas as gpd
import ezdxf
from ezdxf.enums import TextEntityAlignment

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "clean" / "edmonton_drainage.gpkg"
QA = ROOT / "data" / "clean" / "edmonton_drainage_qa.gpkg"
CAD = ROOT / "cad"
LAYER = {"STORM": ("DRN-STORM", 5), "SANITARY": ("DRN-SANITARY", 30), "COMBINED": ("DRN-COMBINED", 6), "FOUNDATION DRAIN": ("DRN-FDN", 8)}
MH_LAYER = {k: (v[0].replace("DRN-", "DRN-MH-"), v[1]) for k, v in LAYER.items()}


def main(pilot="Ottewell"):
    tag = pilot.lower().replace(" ", "_")
    area = gpd.read_file(SRC, layer="pilot_areas").query("pilot == @pilot")
    xmin, ymin, xmax, ymax = area.total_bounds
    p = gpd.read_file(SRC, layer="pipes", bbox=(xmin, ymin, xmax, ymax))
    mh = gpd.read_file(SRC, layer="manholes", bbox=(xmin, ymin, xmax, ymax))
    qa = gpd.read_file(QA, layer="qa_issues", bbox=(xmin, ymin, xmax, ymax))

    doc = ezdxf.new("R2018", setup=True)
    doc.header["$INSUNITS"] = 6  # metres
    msp = doc.modelspace()
    doc.appids.new("DRN")
    for name, color in list(LAYER.values()) + list(MH_LAYER.values()) + [("DRN-QA-ISSUES", 1)]:
        doc.layers.add(name, color=color)
    blk = doc.blocks.new("MH")
    blk.add_circle((0, 0), radius=0.6)
    for i, tagname in enumerate(["ASSET_ID", "SYSTEM", "RIM_ELEV", "YEAR_BUILT"]):
        blk.add_attdef(tagname, insert=(0.9, 0.6 - i * 0.5), dxfattribs={"height": 0.35})

    for sysname, d in p.groupby("system"):
        lyr = LAYER[sysname][0]
        for aid, g in zip(d.asset_id, d.geometry):
            e = msp.add_lwpolyline(list(g.coords), dxfattribs={"layer": lyr})
            e.set_xdata("DRN", [(1000, aid)])  # asset ID travels with each pipe
    for _, r in mh.iterrows():
        ref = msp.add_blockref("MH", (r.geometry.x, r.geometry.y), dxfattribs={"layer": MH_LAYER[r.system][0]})
        ref.add_auto_attribs({"ASSET_ID": r.asset_id, "SYSTEM": r.system,
                              "RIM_ELEV": "" if r.rim_elev != r.rim_elev else f"{r.rim_elev:.2f}",
                              "YEAR_BUILT": "" if r.year_built != r.year_built else str(int(r.year_built))})
    for _, r in qa.iterrows():
        msp.add_circle((r.geometry.x, r.geometry.y), radius=2.0, dxfattribs={"layer": "DRN-QA-ISSUES"})
        msp.add_text(r.rule, height=1.5, dxfattribs={"layer": "DRN-QA-ISSUES"}).set_placement((r.geometry.x + 2.5, r.geometry.y), align=TextEntityAlignment.MIDDLE_LEFT)

    CAD.mkdir(exist_ok=True)
    out = CAD / f"{tag}_drainage.dxf"
    doc.saveas(out)

    # Read back and compare
    back = ezdxf.readfile(out).modelspace()
    rows = []
    for sysname, (lyr, _) in LAYER.items():
        rows.append((lyr, int((p.system == sysname).sum()), len(back.query(f'LWPOLYLINE[layer=="{lyr}"]'))))
    for sysname, (lyr, _) in MH_LAYER.items():
        rows.append((lyr, int((mh.system == sysname).sum()), len(back.query(f'INSERT[layer=="{lyr}"]'))))
    rows.append(("DRN-QA-ISSUES", len(qa), len(back.query('CIRCLE[layer=="DRN-QA-ISSUES"]'))))
    ok = all(a == b for _, a, b in rows)
    lines = [f"# CAD export read-back check: {pilot}", "",
             f"File: `cad/{out.name}` (DXF R2018, metres, EPSG:3776). Extent: pilot area plus margin.", "",
             "| Layer | Source features | Entities read back |", "|---|---|---|"]
    lines += [f"| {l} | {a} | {b} |" for l, a, b in rows]
    lines += ["", f"Result: **{'all counts match' if ok else 'MISMATCH, check the export'}**."]
    (CAD / f"{tag}_readback.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "Ottewell")
