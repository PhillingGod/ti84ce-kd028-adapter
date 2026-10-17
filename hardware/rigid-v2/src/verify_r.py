"""Independent check of the rigid adapter, using only:
  * the Gerber/drill/CPL files that will be uploaded,
  * the official KiCad footprints of the two connectors and the 0402 parts (ref/*.kicad_mod),
  * pin tables re-typed here from the GPM1421C0 and KD028QVFMA027 datasheets,
  * two orientation rules written as invariants (see below).
Nothing is imported from geom_r.py / model_r.py.

Orientation invariant: for a cable end sitting in a connector, let t = direction the cable tip
points (into the connector), n = normal of the cable's contact face, s = direction from the cable
centre towards conductor 'pin 1'.  det[t, n, s] does not change when the cable is bent, folded or
twisted, so it is a property of the cable end.
  * CE end (GPM1421C0 in the mainboard FH26, from the SG92A photo): +1.
    -> a type B (opposite-side) FFC has +1 at the other end too; type A has -1.
  * KD028 FPC end (Startek drawing p.6, re-checked): -1.  Front view (folded, as shipped): tail
    sticks out to the right, PI stiffener visible (contacts face the back), tip +x, pin 1 at the
    bottom (back view labels '50' top, '1' bottom; the back view is a left-right flip, the 30.25 mm
    dimension is measured from the top edge in both views).
"""
import re
import os
import sys
import csv
import math
import warnings
from collections import defaultdict
import numpy as np
import gerbonara as gb
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely.affinity import rotate, translate

warnings.filterwarnings("ignore")
D = sys.argv[1] if len(sys.argv) > 1 else "out/gerber"
BASE = "ti84ce-kd028-rigid-v2"
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
FFC_TYPE = "A"
DET_CE = +1
DET_FAR = DET_CE if FFC_TYPE == "B" else -DET_CE
DET_KD = -1


def ce_sig(name):
    return "VLED_K" if name.startswith("VLED_K") else name


def kd_sig(name):
    if name in NC:
        return None
    return FIX.get(name, ALIAS.get(name, name))


# ------------------------------------------------------------------ KiCad footprints
def read_fp(path):
    pads = {}
    for m in re.finditer(r'\(pad "?([^"\s]+)"? smd \w+ \(at ([-\d.]+) ([-\d.]+)\) \(size ([-\d.]+) ([-\d.]+)\)',
                         open(path).read()):
        name, x, y, w, h = m.group(1), *map(float, m.groups()[1:])
        pads.setdefault(name, []).append((x, y, w, h))
    return pads


def place(fp_pads, cx, cy, rot_deg):
    """KiCad footprint coordinates (y down) -> board coordinates (y up), KiCad rotation (CCW on screen)."""
    out = {}
    th = math.radians(rot_deg)
    for name, lst in fp_pads.items():
        for x, y, w, h in lst:
            xu, yu = x, -y                                   # to y-up
            xr = xu * math.cos(th) - yu * math.sin(th)
            yr = xu * math.sin(th) + yu * math.cos(th)
            if abs(math.sin(th)) > 0.5:
                w, h = h, w
            out.setdefault(name, []).append((cx + xr, cy + yr, w, h))
    return out


def kdir(vx, vy, rot_deg):
    th = math.radians(rot_deg)
    xu, yu = vx, -vy
    return (xu * math.cos(th) - yu * math.sin(th), xu * math.sin(th) + yu * math.cos(th))


# ------------------------------------------------------------------ Gerber reading
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
    # CPL rotation is in JLC's convention.  JLC's model of C92280 at 0 deg has its FPC opening
    # towards -y (checked in JLC's 3D preview: 20 leads on the 0.8 mm pads, black actuator towards J2);
    # the KiCad footprint at 0 deg has its FPC side towards -x, so KiCad angle = JLC angle + 90.
    KICAD_ROT_OFFSET = {"J1": 90.0}
    pos = {k: (float(v["Mid X"].rstrip("mm")), float(v["Mid Y"].rstrip("mm")),
               float(v["Rotation"]) + KICAD_ROT_OFFSET.get(k, 0.0)) for k, v in cpl.items()}
    top = load_layer(f"{D}/{BASE}-F_Cu.gbr")
    bot = load_layer(f"{D}/{BASE}-B_Cu.gbr")
    mask = load_layer(f"{D}/{BASE}-F_Mask.gbr")
    edge_f = gb.GerberFile.open(f"{D}/{BASE}-Edge_Cuts.gbr")
    epts = [(o.x1, o.y1) for o in edge_f.objects]
    outline = Polygon(epts)
    holes = [(h.x, h.y, h.tool.diameter) for h in gb.ExcellonFile.open(f"{D}/{BASE}-PTH.drl").objects]

    # ---- connectors: footprint pads from KiCad, placed by the CPL
    fh26 = read_fp(f"{REF}/Hirose_FH26-39S-0.3SHW_2Rows-39Pins-1MP_P0.60mm_Horizontal.kicad_mod")
    fh12 = read_fp(f"{REF}/Hirose_FH12-50S-0.5SH_1x50-1MP_P0.50mm_Horizontal.kicad_mod")
    c0402 = read_fp(f"{REF}/C_0402_1005Metric.kicad_mod")
    r0402 = read_fp(f"{REF}/R_0402_1005Metric.kicad_mod")
    J1 = place(fh26, *pos["J1"])
    J2 = place(fh12, *pos["J2"])
    all_pads = [("J1", n, p) for n, l in J1.items() for p in l] + [("J2", n, p) for n, l in J2.items() for p in l]
    for ref, fp in (("R1", r0402), ("C1", c0402), ("C2", c0402)):
        for n, l in place(fp, *pos[ref]).items():
            for p in l:
                all_pads.append((ref, n, p))
    for ref, n, (x, y, w, h) in all_pads:
        r = box(x - w / 2, y - h / 2, x + w / 2, y + h / 2)
        if not top.buffer(1e-4).contains(r):
            print(f"!! {ref} pad {n} at ({x:.3f},{y:.3f}) not fully covered by F_Cu"); ok = False
        if not mask.buffer(1e-4).contains(r):
            print(f"!! {ref} pad {n} at ({x:.3f},{y:.3f}) has no soldermask opening"); ok = False

    # ---- which J1 pad gets CE pin 1 (type-B FFC, bottom contact, top side: n = -z)
    # FH26: FPC enters from the footprint's -x side (actuator side, 3D model) -> tip points +x (KiCad)
    tx, ty = kdir(1.0, 0.0, pos["J1"][2])
    # det[t, n, s] with n = (0,0,-1): t . (n x s) = tx*sy - ty*sx ; s perpendicular to t
    cands = [(-ty, tx), (ty, -tx)]
    s = [c for c in cands if abs((tx * c[1] - ty * c[0]) - DET_FAR) < 1e-6][0]
    sig = sorted(range(1, 40), key=lambda k: -(J1[str(k)][0][0] * s[0] + J1[str(k)][0][1] * s[1]))
    ce_pad = {c: J1[str(sig[c - 1])][0] for c in range(1, 40)}      # CE pin c -> pad geometry
    # FH12: FPC enters from the footprint's +y (KiCad, front/actuator side) -> tip points -y (KiCad)
    tx, ty = kdir(0.0, -1.0, pos["J2"][2])
    cands = [(-ty, tx), (ty, -tx)]
    s = [c for c in cands if abs((tx * c[1] - ty * c[0]) - DET_KD) < 1e-6][0]
    sig2 = sorted(range(1, 51), key=lambda k: -(J2[str(k)][0][0] * s[0] + J2[str(k)][0][1] * s[1]))
    kd_pad = {m: J2[str(sig2[m - 1])][0] for m in range(1, 51)}
    print(f"J1: CE pin 1 at ({ce_pad[1][0]:.2f},{ce_pad[1][1]:.2f}), pin 39 at ({ce_pad[39][0]:.2f},{ce_pad[39][1]:.2f})")
    print(f"J2: KD pin 1 at ({kd_pad[1][0]:.2f},{kd_pad[1][1]:.2f}), pin 50 at ({kd_pad[50][0]:.2f},{kd_pad[50][1]:.2f})")

    # ---- copper components (union-find over pieces joined by plated holes)
    pieces = [("T", p) for p in (top.geoms if hasattr(top, "geoms") else [top])] + \
             [("B", p) for p in (bot.geoms if hasattr(bot, "geoms") else [bot])]
    parent = list(range(len(pieces)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for x, y, dia in holes:
        hit = [i for i, (L, p) in enumerate(pieces) if p.contains(Point(x, y).buffer(dia / 2 + 0.09))]
        if len(hit) != 2:
            print(f"!! hole at ({x:.2f},{y:.2f}) has annular copper on {len(hit)} layer(s)"); ok = False
        for a, b in zip(hit, hit[1:]):
            parent[find(a)] = find(b)

    def comp(xy, layer="T"):
        hit = [i for i, (L, p) in enumerate(pieces) if L == layer and p.contains(Point(*xy))]
        return find(hit[0]) if hit else None

    sig_comp = defaultdict(set)
    for c in range(1, 40):
        cc = comp(ce_pad[c][:2])
        if cc is None:
            print(f"!! CE{c} pad has no copper"); ok = False
        sig_comp[ce_sig(GPM1421C0[c - 1])].add(cc)
    for m in range(1, 51):
        name = KD028[m - 1]
        sname = kd_sig(name)
        cc = comp(kd_pad[m][:2])
        if sname is None:
            if cc is not None and any(cc in v for v in sig_comp.values()):
                print(f"!! KD{m} {name} should be NC but is connected"); ok = False
            continue
        if cc not in sig_comp.get(sname, set()):
            print(f"!! KD{m} {name} is not connected to CE {sname}"); ok = False
        sig_comp[sname].add(cc)
    for ref in ("MP",):
        for x, y, w, h in J1["MP"] + J2["MP"]:
            sig_comp["GND"].add(comp((x, y)))
    owner = {}
    for sname, cs in sig_comp.items():
        if len(cs) != 1:
            print(f"!! signal {sname} is split into {len(cs)} pieces"); ok = False
        for cc in cs:
            if cc in owner and owner[cc] != sname:
                print(f"!! SHORT between {sname} and {owner[cc]}"); ok = False
            owner[cc] = sname
    one = lambda n: list(sig_comp[n])[0]
    # passives
    want = {"R1": ("TE", "GND"), "C1": ("IOVCC", "GND"), "C2": ("VCC", "GND")}
    for ref, (a, b) in want.items():
        fp = r0402 if ref.startswith("R") else c0402
        pl = place(fp, *pos[ref])
        nets = sorted([owner.get(comp(pl[k][0][:2]), "?") for k in ("1", "2")])
        if nets != sorted([a, b]):
            print(f"!! {ref} connects {nets}, expected {a}-{b}"); ok = False
    # TE must reach GND only through R1
    if one("TE") == one("GND"):
        print("!! TE shorted to GND"); ok = False

    # ---- clearances measured on the Gerber copper
    for L, g in (("F_Cu", top), ("B_Cu", bot)):
        parts = list(g.geoms) if hasattr(g, "geoms") else [g]
        mind = 9.0
        for i in range(len(parts)):
            for j in range(i + 1, len(parts)):
                if parts[i].bounds[0] - 0.3 > parts[j].bounds[2] or parts[j].bounds[0] - 0.3 > parts[i].bounds[2]:
                    continue
                dd = parts[i].distance(parts[j])
                mind = min(mind, dd)
        e = outline.exterior.distance(g)
        print(f"{L}: min copper gap {mind:.3f} mm, min copper-to-edge {e:.3f} mm")
        if mind < 0.125 or e < 0.25:
            ok = False
    print("board outline:", [round(v, 2) for v in outline.bounds])
    print("pin map check:", "PASS" if ok else "FAIL")
    for c in range(1, 40):
        cc = comp(ce_pad[c][:2])
        kds = [m for m in range(1, 51) if comp(kd_pad[m][:2]) == cc]
        print(f"CE{c:2d} {GPM1421C0[c - 1]:8s} -> KD {','.join(map(str, kds)) or '-'}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
