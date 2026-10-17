"""Write Gerbers, drill, BOM/CPL for the adapter."""
import os
import sys
import csv
import numpy as np
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path as MPath
from shapely.geometry import Polygon, box

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gerberlib import Gerber, FONT  # noqa: E402  (RS-274X writer used for the earlier flex)
import geom as G
import model as M

BASE = "ti84ce-kd028-flex-v3"


def text_mirrored(g, s, x, y, size, rot=0):
    """Text for a bottom layer: mirrored in X so it reads correctly when seen from the bottom."""
    tp = TextPath((0, 0), s, size=size, prop=FONT)
    polys = [p for p in tp.to_polygons() if len(p) > 2]
    if not polys:
        return
    allp = np.vstack(polys)
    xmin, ymin = allp.min(axis=0)
    xmax, ymax = allp.max(axis=0)
    ox, oy = -(xmin + xmax) / 2, -(ymin + ymax) / 2
    th = np.radians(rot)
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])

    def tf(p):
        q = (p + [ox, oy]) @ R.T
        return [(-a + x, b + y) for a, b in q]
    paths = [MPath(p) for p in polys]
    hole = [any(j != i and paths[j].contains_point(p[0]) for j in range(len(polys))) for i, p in enumerate(polys)]
    for i, p in enumerate(polys):
        if not hole[i]:
            g.polarity("D"); g.region(tf(p))
    for i, p in enumerate(polys):
        if hole[i]:
            g.polarity("C"); g.region(tf(p))
    g.polarity("D")


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
    if pour is not None:
        poly_region(g, pour)
    for L, net, pts, w in d.tracks:
        if L == layer:
            if len(pts) >= 2:
                g.track(pts, w)
    for net, x, y in d.vias:
        g.flash(g.ap("C", G.VIA_D), x, y)
    for L, net, x, y, w, h, kind in d.pads:
        if L == layer:
            if kind == "finger":
                g.rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2)
            else:
                g.flash(g.ap("R", w, h), x, y)
    g.write(path)


def build_all(outdir):
    os.makedirs(outdir, exist_ok=True)
    d = G.build()
    cu, pours = M.full_copper(d)
    errs = M.drc(d, cu, verbose=False) + M.connectivity(d, cu, verbose=False)
    if errs:
        raise SystemExit("DRC/connectivity errors: " + "; ".join(errs))
    p = lambda name: os.path.join(outdir, f"{BASE}-{name}")

    write_copper(d, pours["T"], "T", p("F_Cu.gbr"), "Copper,L1,Top")
    write_copper(d, pours["B"], "B", p("B_Cu.gbr"), "Copper,L2,Bot")

    # ---- coverlay openings (v3): top = gold fingers only; bottom = J2 window + passive pads
    xs = [G.x_kd(m) for m in range(1, 51)]
    j2win = box(min(xs) - 0.35, G.J2_PAD_Y - G.J2_PAD[1] / 2 - 0.10, max(xs) + 0.35,
                G.J2_PAD_Y + G.J2_PAD[1] / 2 + 0.10)
    finwin = box(-G.TAIL_W / 2 - 0.5, -0.5, G.TAIL_W / 2 + 0.5, G.COVERLAY_TAIL_Y)
    g = Gerber("Soldermask,Top", "Negative")
    g.rect(*finwin.bounds)
    g.write(p("F_Mask.gbr"))
    open_top = finwin
    g = Gerber("Soldermask,Bot", "Negative")
    g.rect(*j2win.bounds)
    bot_open = [j2win]
    for L, net, x, y, w, h, kind in d.pads:
        if L == "B" and abs(y - G.J2_PAD_Y) > 0.01:
            g.flash(g.ap("R", w + 0.20, h + 0.20), x, y)        # JLC coverlay expansion 0.1/side
            bot_open.append(box(x - w / 2 - 0.1, y - h / 2 - 0.1, x + w / 2 + 0.1, y + h / 2 + 0.1))
    g.write(p("B_Mask.gbr"))
    from shapely.ops import unary_union as _uu
    open_bot = _uu(bot_open)

    # ---- paste (bottom only: J2 + passives)
    g = Gerber("Paste,Bot")
    for L, net, x, y, w, h, kind in d.pads:
        if L == "B":
            g.flash(g.ap("R", w, h), x, y)
    g.write(p("B_Paste.gbr"))

    # ---- silkscreen (kept 0.15 mm away from coverlay openings)
    g = Gerber("Legend,Top")
    for s_, x, y, size, rot in d.silk_top:
        g.text(s_, x, y, size, rot=rot)
    for pts, w in d.silk_lines_top:
        g.track(pts, w)
    x1 = G.x_ce(1)
    g.region([(x1 - 0.35, 3.15), (x1 + 0.35, 3.15), (x1, 2.85)])   # pin-1 mark next to CE finger 1
    g.write(p("F_Silkscreen.gbr"))

    g = Gerber("Legend,Bot")
    for s_, x, y, size, rot in d.silk_bot:
        text_mirrored(g, s_, x, y, size, rot)
    for pts, w in d.silk_lines_bot:
        g.track(pts, w)
    # J2 body front edge (actuator side, +y): orientation mark
    g.track([(-14.05, G.YZ + 4.45), (14.05, G.YZ + 4.45)], 0.15)
    g.write(p("B_Silkscreen.gbr"))

    # ---- outline
    g = Gerber("Profile,NP")
    pts = d.outline + [d.outline[0]]
    g.track(pts, 0.10)
    g.write(p("Edge_Cuts.gbr"))

    # ---- stiffeners: JLC layer naming (pib_* = PI bottom, fr4t_* = FR4 top), outline regions only
    g = Gerber("Other,Stiffener_PI_BottomSide")
    g.rect(-G.TAIL_W / 2, 0.0, G.TAIL_W / 2, G.PI_STIFF_Y1)
    g.write(os.path.join(outdir, f"pib_{G.PI_STIFF_T}.gbr"))
    g = Gerber("Other,Stiffener_FR4_TopSide")
    head = Polygon(d.outline).intersection(box(-30, G.FR4_Y0, 30, 200)).buffer(-0.20)
    g.region(list(head.exterior.coords)[:-1])
    g.write(os.path.join(outdir, f"fr4t_{G.FR4_T}.gbr"))

    # ---- drill (plated vias)
    with open(p("PTH.drl"), "w") as f:
        f.write("M48\n;TI-84 CE <-> KD028QVFMA027 adapter, plated vias\nFMAT,2\nMETRIC,TZ\n")
        f.write(f"T1C{G.VIA_DRILL:.3f}\n%\nG90\nG05\nT1\n")
        for net, x, y in d.vias:
            f.write(f"X{x:.3f}Y{y:.3f}\n")
        f.write("T0\nM30\n")

    # ---- BOM / CPL (JLCPCB format)
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
            w.writerow([ref, f"{x + 0.0:.3f}mm", f"{y:.3f}mm", d.comp_side.get(ref, "Top"), rot])
    return d, cu, pours


if __name__ == "__main__":
    build_all(sys.argv[1] if len(sys.argv) > 1 else "out/gerber")
    print("written")
