"""Write Gerbers, drill, BOM/CPL for the rigid adapter (JLCPCB 2-layer + economic PCBA, top side)."""
import os
import sys
import csv
import numpy as np
from matplotlib.textpath import TextPath
from matplotlib.path import Path as MPath
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from shapely.affinity import rotate, translate, scale

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gerberlib import Gerber, FONT  # noqa: E402  RS-274X writer (same one used for the flex)
import geom_r as G
import model_r as M

BASE = "ti84ce-kd028-rigid-v2"
MASK_EXP = 0.05


def text_geom(s, x, y, size, rot=0, mirror=False):
    tp = TextPath((0, 0), s, size=size, prop=FONT)
    polys = [p for p in tp.to_polygons() if len(p) > 2]
    if not polys:
        return Polygon()
    paths = [MPath(p) for p in polys]
    outer, holes = [], []
    for i, p in enumerate(polys):
        inside = any(j != i and paths[j].contains_point(p[0]) for j in range(len(polys)))
        (holes if inside else outer).append(Polygon(p).buffer(0))
    g = unary_union(outer).difference(unary_union(holes)) if holes else unary_union(outer)
    minx, miny, maxx, maxy = g.bounds
    g = translate(g, -(minx + maxx) / 2, -(miny + maxy) / 2)
    if mirror:
        g = scale(g, xfact=-1, yfact=1, origin=(0, 0))
    g = rotate(g, rot, origin=(0, 0))
    return translate(g, x, y)


def poly_region(g, poly):
    polys = poly.geoms if hasattr(poly, "geoms") else [poly]
    for p in polys:
        if p.is_empty or p.geom_type != "Polygon":
            continue
        g.polarity("D")
        g.region(list(p.exterior.coords)[:-1])
        for h in p.interiors:
            g.polarity("C")
            g.region(list(h.coords)[:-1])
    g.polarity("D")


def write_copper(d, pour, layer, path, func):
    g = Gerber(func)
    if pour is not None and not pour.is_empty:
        poly_region(g, pour)
    for L, net, pts, w in d.tracks:
        if L == layer and len(pts) >= 2:
            g.track(pts, w)
    for net, x, y in d.vias:
        g.flash(g.ap("C", G.VIA_D), x, y)
    for L, net, x, y, w, h, kind in d.pads:
        if L == layer:
            g.flash(g.ap("R", w, h), x, y)
    g.write(path)


def mask_openings(d):
    return unary_union([box(x - w / 2 - MASK_EXP, y - h / 2 - MASK_EXP, x + w / 2 + MASK_EXP, y + h / 2 + MASK_EXP)
                        for L, net, x, y, w, h, kind in d.pads if L == "T"])


def silk_top_geom(d):
    parts = [text_geom(s, x, y, size, rot) for s, x, y, size, rot in d.silk_top]
    # pin-1 triangles next to CE pin 1 (J1) and KD pin 1 (J2)
    x1 = G.x_ce(1)
    parts.append(Polygon([(x1 - 0.30, 0.15), (x1 + 0.30, 0.15), (x1, 0.55)]).buffer(0))
    sk = 1.0 if G.x_kd(1) > 0 else -1.0     # triangle outside the KD1 end, pointing at the pad
    parts.append(Polygon([(G.x_kd(1) + sk * 0.95, G.J2P - 0.3), (G.x_kd(1) + sk * 0.95, G.J2P + 0.3),
                          (G.x_kd(1) + sk * 0.55, G.J2P)]).buffer(0))
    # connector outlines (only outside the pads): J2 body front edge and J1 body sides
    lines = [box(-14.05, G.BOARD_TOP - 0.40, 14.05, G.BOARD_TOP - 0.28)]
    return unary_union(parts + lines)


def silk_bot_geom(d):
    return unary_union([text_geom(s, x, y, size, rot, mirror=True) for s, x, y, size, rot in d.silk_bot])


def build_all(outdir):
    os.makedirs(outdir, exist_ok=True)
    d = G.build()
    n_stitch = M.add_stitching(d)
    cu, pours = M.full_copper(d)
    errs = M.drc(d, cu, verbose=False) + M.connectivity(d, cu, verbose=False)
    if errs:
        raise SystemExit("DRC/connectivity errors: " + "; ".join(errs))
    p = lambda name: os.path.join(outdir, f"{BASE}-{name}")

    write_copper(d, pours["T"], "T", p("F_Cu.gbr"), "Copper,L1,Top")
    write_copper(d, pours["B"], "B", p("B_Cu.gbr"), "Copper,L2,Bot")

    # soldermask: openings on top pads only, vias tented, bottom fully covered
    g = Gerber("Soldermask,Top", "Negative")
    for L, net, x, y, w, h, kind in d.pads:
        if L == "T":
            g.flash(g.ap("R", w + 2 * MASK_EXP, h + 2 * MASK_EXP), x, y)
    g.write(p("F_Mask.gbr"))
    g = Gerber("Soldermask,Bot", "Negative")
    g.write(p("B_Mask.gbr"))

    # Paste: J1 (FH26) uses the metal-mask openings from the Hirose FH26 catalog (t = 0.1 mm):
    # 0.23 x 0.65 on the 0.3 x 0.8 pads, 0.23 x 0.55 on the 0.3 x 0.65 pads, 0.3 x 0.7 on the fittings.
    # Pad sizes are unique to J1 on this board, so they identify the J1 pads.
    FH26_PASTE = {(0.30, 0.80): (0.23, 0.65), (0.30, 0.65): (0.23, 0.55), (0.40, 0.95): (0.30, 0.70)}
    g = Gerber("Paste,Top")
    for L, net, x, y, w, h, kind in d.pads:
        if L == "T":
            pw, ph = FH26_PASTE.get((round(w, 2), round(h, 2)), (w, h))
            g.flash(g.ap("R", pw, ph), x, y)
    g.write(p("F_Paste.gbr"))

    # silkscreen (clipped away from mask openings)
    keep_clear = mask_openings(d).buffer(0.10)
    st = silk_top_geom(d)
    clipped = st.intersection(keep_clear)
    st = st.difference(keep_clear)
    g = Gerber("Legend,Top")
    poly_region(g, st)
    g.write(p("F_Silkscreen.gbr"))
    g = Gerber("Legend,Bot")
    poly_region(g, silk_bot_geom(d))
    g.write(p("B_Silkscreen.gbr"))

    g = Gerber("Profile,NP")
    pts = d.outline + [d.outline[0]]
    g.track(pts, 0.10)
    g.write(p("Edge_Cuts.gbr"))

    with open(p("PTH.drl"), "w") as f:
        f.write("M48\n;TI-84 CE <-> KD028QVFMA027 rigid adapter, plated vias\nFMAT,2\nMETRIC,TZ\n")
        f.write(f"T1C{G.VIA_DRILL:.3f}\n%\nG90\nG05\nT1\n")
        for net, x, y in d.vias:
            f.write(f"X{x:.3f}Y{y:.3f}\n")
        f.write("T0\nM30\n")

    groups = {}
    for ref, val, lcsc, x, y, rot, fp in d.comps:
        groups.setdefault((val, fp, lcsc), []).append(ref)
    with open(os.path.join(outdir, "BOM-JLC.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (val, fp, lcsc), refs in groups.items():
            w.writerow([val, ",".join(sorted(refs)), fp, lcsc])
    with open(os.path.join(outdir, "CPL-JLC.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for ref, val, lcsc, x, y, rot, fp in d.comps:
            w.writerow([ref, f"{x + 0.0:.3f}mm", f"{y:.3f}mm", "Top", rot])
    return d, cu, pours, n_stitch, clipped


if __name__ == "__main__":
    d, cu, pours, n, clipped = build_all(sys.argv[1] if len(sys.argv) > 1 else "out/gerber")
    print("written; stitching vias:", n, "; vias total:", len(d.vias),
          "; silk clipped area mm2:", round(clipped.area, 3))
