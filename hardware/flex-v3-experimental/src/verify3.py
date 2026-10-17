"""Independent check of flex v3 from the Gerber/drill/CPL files (gerbonara), not from geom.py.

* Pin tables are typed in again from the two datasheets (GPM1421C0, KD028QVFMA027).
* J2 / R1 / C1 / C2 pads come from the official KiCad footprints, placed by the CPL (bottom side
  = footprint mirrored in x).
* Which finger is CE pin 1 and which J2 contact gets KD pin 1 follows only from the orientation
  invariant det[t, n, s] (t = tip direction, n = contact-face normal, s = pin-1 side):
    CE cable end det = +1  (GPM1421C0 drawing + SG92A photo; same value the rigid board uses)
    KD028 FPC end  det = -1  (Startek drawing p.6 + shop photos)
  Run with an argument 'neg' to flip the KD det: the check must then FAIL.
"""
import csv
import math
import re
import os
import sys
import warnings
from collections import defaultdict
import gerbonara as gb
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

warnings.filterwarnings("ignore")
_args = [a for a in sys.argv[1:] if a != "neg"]
D = _args[0] if _args else "out/gerber"
NEG = "neg" in sys.argv[1:]
BASE = "ti84ce-kd028-flex-v3"
REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ref")

GPM1421C0 = ["GND", "TE", "RESET"] + [f"DB{i}" for i in range(17, -1, -1)] + \
    ["SDO", "SDI", "WR/SCL", "CS", "IOVCC", "VCC", "VLED_A", "VLED_K1", "VLED_K2", "VLED_K3",
     "VLED_K4", "VSYNC", "HSYNC", "GND", "DCLK", "GND", "ENABLE", "GND"]
KD028 = ["GND", "XR", "YD", "XL", "YU", "IOVCC", "IOVCC", "VCI", "VCI", "IM2", "IM1", "IM0",
         "RESET", "CS", "RS(SPI-SCL)", "WR(SPI-RS)", "RD", "VSYNC", "HSYNC", "ENABLE", "DOTCLK",
         "SDA"] + [f"DB{i}" for i in range(18)] + ["SDO", "GND", "LEDA"] + \
    [f"LEDK{i}" for i in range(1, 7)] + ["GND"]
assert len(GPM1421C0) == 39 and len(KD028) == 50
FIX = {"IM2": "IOVCC", "IM0": "IOVCC", "RD": "IOVCC", "IM1": "GND", "WR(SPI-RS)": "GND"}
ALIAS = {"VCI": "VCC", "SDA": "SDI", "RS(SPI-SCL)": "WR/SCL", "DOTCLK": "DCLK", "LEDA": "VLED_A"}
for i in range(1, 7):
    ALIAS[f"LEDK{i}"] = "VLED_K"
NC = {"XR", "YD", "XL", "YU"}
DET_CE = +1
DET_KD = -1 if not NEG else +1


def ce_sig(name):
    return "VLED_K" if name.startswith("VLED_K") else name


def kd_sig(name):
    if name in NC:
        return None
    return FIX.get(name, ALIAS.get(name, name))


def read_fp(path):
    pads = {}
    for m in re.finditer(r'\(pad "?([^"\s]+)"? smd \w+ \(at ([-\d.]+) ([-\d.]+)\) \(size ([-\d.]+) ([-\d.]+)\)',
                         open(path).read()):
        name, x, y, w, h = m.group(1), *map(float, m.groups()[1:])
        pads.setdefault(name, []).append((x, y, w, h))
    return pads


def place(fp_pads, cx, cy, rot_deg, bottom):
    """KiCad footprint (y down) -> board top-view coordinates (y up). Bottom side: mirror x first."""
    out = {}
    th = math.radians(rot_deg)
    for name, lst in fp_pads.items():
        for x, y, w, h in lst:
            xu, yu = (-x if bottom else x), -y
            xr = xu * math.cos(th) - yu * math.sin(th)
            yr = xu * math.sin(th) + yu * math.cos(th)
            if abs(math.sin(th)) > 0.5:
                w, h = h, w
            out.setdefault(name, []).append((cx + xr, cy + yr, w, h))
    return out


def vdir(vx, vy, rot_deg, bottom):
    th = math.radians(rot_deg)
    xu, yu = (-vx if bottom else vx), -vy
    return (xu * math.cos(th) - yu * math.sin(th), xu * math.sin(th) + yu * math.cos(th))


def pin1_side(t, nz, det):
    """s (unit, in-plane, perpendicular to t) with t . (n x s) = det, n = (0, 0, nz)."""
    tx, ty = t
    for s in ((-ty, tx), (ty, -tx)):
        val = nz * (-tx * s[1] + ty * s[0])
        if abs(val - det) < 1e-6:
            return s
    raise ValueError


def load_layer(path):
    f = gb.GerberFile.open(path)
    geom = Polygon()
    batch, pol = [], True

    def flush():
        nonlocal geom, batch
        if batch:
            u = unary_union(batch)
            geom = geom.union(u) if pol else geom.difference(u)
        batch = []
    for o in f.objects:
        t = type(o).__name__
        if o.polarity_dark != pol:
            flush()
            pol = o.polarity_dark
        if t == "Line":
            batch.append(LineString([(o.x1, o.y1), (o.x2, o.y2)]).buffer(o.aperture.diameter / 2, 16))
        elif t == "Flash":
            a = o.aperture
            if hasattr(a, "w"):
                batch.append(box(o.x - a.w / 2, o.y - a.h / 2, o.x + a.w / 2, o.y + a.h / 2))
            else:
                batch.append(Point(o.x, o.y).buffer(a.diameter / 2, 24))
        elif t == "Region":
            pts = [(p[0], p[1]) for p in o.outline]
            if len(pts) >= 3:
                batch.append(Polygon(pts).buffer(0))
        else:
            raise SystemExit(f"unhandled object {t}")
    flush()
    return geom


def main():
    ok = True
    cpl = {r["Designator"]: r for r in csv.DictReader(open(f"{D}/CPL-JLC.csv"))}
    pos = {k: (float(v["Mid X"].rstrip("mm")), float(v["Mid Y"].rstrip("mm")), float(v["Rotation"]),
               v["Layer"] == "Bottom") for k, v in cpl.items()}
    top = load_layer(f"{D}/{BASE}-F_Cu.gbr")
    bot = load_layer(f"{D}/{BASE}-B_Cu.gbr")
    tmask = load_layer(f"{D}/{BASE}-F_Mask.gbr")
    bmask = load_layer(f"{D}/{BASE}-B_Mask.gbr")
    epts = [(o.x1, o.y1) for o in gb.GerberFile.open(f"{D}/{BASE}-Edge_Cuts.gbr").objects]
    outline = Polygon(epts)
    holes = [(h.x, h.y, h.tool.diameter) for h in gb.ExcellonFile.open(f"{D}/{BASE}-PTH.drl").objects]
    layer_geom = {"T": top, "B": bot}

    # ---- footprints placed from the CPL
    fh12 = read_fp(f"{REF}/Hirose_FH12-50S-0.5SH_1x50-1MP_P0.50mm_Horizontal.kicad_mod")
    c0402 = read_fp(f"{REF}/C_0402_1005Metric.kicad_mod")
    r0402 = read_fp(f"{REF}/R_0402_1005Metric.kicad_mod")
    J2 = place(fh12, *pos["J2"])
    all_pads = [("J2", n, p) for n, l in J2.items() for p in l]
    pas = {}
    for ref, fp in (("R1", r0402), ("C1", c0402), ("C2", c0402)):
        pas[ref] = place(fp, *pos[ref])
        for n, l in pas[ref].items():
            for p in l:
                all_pads.append((ref, n, p))
    for ref, n, (x, y, w, h) in all_pads:
        side = "B" if pos[ref][3] else "T"
        r = box(x - w / 2, y - h / 2, x + w / 2, y + h / 2)
        if not layer_geom[side].buffer(1e-4).contains(r):
            print(f"!! {ref} pad {n} at ({x:.3f},{y:.3f}) not covered by {side}_Cu"); ok = False
        if not (bmask if side == "B" else tmask).buffer(1e-4).contains(r):
            print(f"!! {ref} pad {n} at ({x:.3f},{y:.3f}) has no coverlay opening"); ok = False
        if not outline.contains(r):
            print(f"!! {ref} pad {n} outside the board"); ok = False

    # ---- CE fingers: tail tip = the outline edge at y = 0, contacts on F_Cu (n = +z)
    tip_y = min(y for x, y in epts)
    t_ce = (0.0, -1.0)
    s_ce = pin1_side(t_ce, +1, DET_CE)
    fing = [p for p in (top.intersection(box(-7, tip_y, 7, tip_y + 2.0)).geoms
                        if hasattr(top.intersection(box(-7, tip_y, 7, tip_y + 2.0)), "geoms")
                        else [top.intersection(box(-7, tip_y, 7, tip_y + 2.0))])]
    fing = [f for f in fing if f.area > 0.05]
    if len(fing) != 39:
        print(f"!! found {len(fing)} gold fingers on F_Cu (expected 39)"); ok = False
    fing.sort(key=lambda f: -(f.centroid.x * s_ce[0] + f.centroid.y * s_ce[1]))
    ce_pt = {c: (fing[c - 1].centroid.x, fing[c - 1].centroid.y) for c in range(1, 40)}
    if not tmask.buffer(1e-4).contains(box(-6.0, tip_y, 6.0, tip_y + 2.2)):
        print("!! gold fingers not fully exposed by the top coverlay"); ok = False
    if bot.intersects(box(-7, tip_y, 7, tip_y + 4.5)):
        print("!! copper on the bottom (stiffener) side of the tail"); ok = False

    # ---- J2: FH12 FPC enters from the footprint's +y (KiCad) side -> tip points -y (KiCad)
    t_kd = vdir(0.0, -1.0, pos["J2"][2], pos["J2"][3])
    nz = +1 if pos["J2"][3] else -1        # bottom-contact connector: tail contacts face the board
    s_kd = pin1_side(t_kd, nz, DET_KD)
    order = sorted([k for k in J2 if k.isdigit()], key=lambda k: -(J2[k][0][0] * s_kd[0] + J2[k][0][1] * s_kd[1]))
    assert len(order) == 50
    kd_pad = {m: J2[order[m - 1]][0] for m in range(1, 51)}
    print(f"CE pin 1 finger at x={ce_pt[1][0]:+.2f}, pin 39 at x={ce_pt[39][0]:+.2f} (top view)")
    print(f"J2 ({'bottom' if pos['J2'][3] else 'top'}): KD pin 1 at x={kd_pad[1][0]:+.2f}, pin 50 at x={kd_pad[50][0]:+.2f}")

    # ---- copper components joined by plated holes
    pieces = [("T", p) for p in (top.geoms if hasattr(top, "geoms") else [top])] + \
             [("B", p) for p in (bot.geoms if hasattr(bot, "geoms") else [bot])]
    parent = list(range(len(pieces)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for x, y, dia in holes:
        hit = [i for i, (L, p) in enumerate(pieces) if p.contains(Point(x, y).buffer(dia / 2 + 0.1))]
        if len(hit) != 2:
            print(f"!! hole at ({x:.2f},{y:.2f}) has annular copper on {len(hit)} layer(s)"); ok = False
        for a, b in zip(hit, hit[1:]):
            parent[find(a)] = find(b)

    def comp(layer, xy):
        hit = [i for i, (L, p) in enumerate(pieces) if L == layer and p.contains(Point(*xy))]
        return find(hit[0]) if hit else None

    sig_comp = defaultdict(set)
    for c in range(1, 40):
        sig_comp[ce_sig(GPM1421C0[c - 1])].add(comp("T", ce_pt[c]))
    for m in range(1, 51):
        name = KD028[m - 1]
        s = kd_sig(name)
        x, y, w, h = kd_pad[m]
        cc = comp("B" if pos["J2"][3] else "T", (x, y))
        if s is None:
            if cc is not None and any(cc in v for v in sig_comp.values()):
                print(f"!! KD{m} {name} should be NC but is connected"); ok = False
            continue
        if cc is None:
            print(f"!! KD{m} {name} pad has no copper"); ok = False
            continue
        if cc not in sig_comp.get(s, set()):
            print(f"!! KD{m} {name} is not connected to CE {s}"); ok = False
        sig_comp[s].add(cc)
    owner = {}
    for s, cs in sig_comp.items():
        if len(cs) != 1:
            print(f"!! signal {s} split into {len(cs)} pieces"); ok = False
        for cc in cs:
            if cc in owner and owner[cc] != s:
                print(f"!! SHORT between {s} and {owner[cc]}"); ok = False
            owner[cc] = s
    one = lambda s: next(iter(sig_comp[s]))
    want = {"R1": {"TE", "GND"}, "C1": {"IOVCC", "GND"}, "C2": {"VCC", "GND"}}
    for ref, pads in pas.items():
        side = "B" if pos[ref][3] else "T"
        nets = {owner.get(comp(side, (l[0][0], l[0][1]))) for l in pads.values()}
        if nets != want[ref]:
            print(f"!! {ref} connects {nets}, expected {want[ref]}"); ok = False
    mp = [p for k, l in J2.items() if not k.isdigit() for p in l]
    for x, y, w, h in mp:
        if owner.get(comp("B" if pos["J2"][3] else "T", (x, y))) != "GND":
            print("!! J2 fitting not on GND"); ok = False
    if one("TE") == one("GND"):
        print("!! TE shorted to GND"); ok = False

    # ---- clearances read back from the Gerbers
    for L, g in (("F_Cu", top), ("B_Cu", bot)):
        parts = list(g.geoms) if hasattr(g, "geoms") else [g]
        mind = min(a.distance(b) for i, a in enumerate(parts) for b in parts[i + 1:]
                   if a.distance(b) < 0.5) if len(parts) > 1 else 9
        e = outline.exterior.distance(g.difference(box(-6.5, -1, 6.5, 5.5)))
        et = outline.exterior.distance(g.intersection(box(-6.5, -1, 6.5, 5.5))) if not g.intersection(box(-6.5, -1, 6.5, 5.5)).is_empty else 9
        print(f"{L}: min copper gap {mind:.3f} mm, copper-to-edge {e:.3f} mm (tail/finger zone {et:.3f} mm)")
        if mind < 0.10 - 1e-3 or e < 0.30 - 1e-3 or et < 0.20 - 1e-3:
            ok = False
    print("pin map check:", "PASS" if ok else "FAIL")
    for c in range(1, 40):
        kds = [m for m in range(1, 51) if comp("B" if pos["J2"][3] else "T", kd_pad[m][:2]) == comp("T", ce_pt[c])]
        print(f"CE{c:2d} {GPM1421C0[c - 1]:8s} -> KD {','.join(map(str, kds)) or '-'}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
