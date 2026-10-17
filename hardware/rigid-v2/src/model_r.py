"""Shapely model of the rigid adapter: copper per layer/net, GND pours, stitching, DRC, connectivity."""
import math
from itertools import combinations
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely.strtree import STRtree
import geom_r as G

MIN_CLR = 0.127        # JLC 2-layer minimum is 0.10; design target 0.127 (5 mil)
POUR_CLR = 0.20
EDGE_CLR = 0.30
POUR_EDGE = 0.40


def track_poly(pts, w):
    if len(pts) == 1:
        return Point(pts[0]).buffer(w / 2, 24)
    return LineString(pts).buffer(w / 2, quad_segs=8, cap_style="round", join_style="round")


def pad_poly(x, y, w, h):
    return box(x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def copper(d):
    cu = {"T": {}, "B": {}}
    for layer, net, pts, w in d.tracks:
        cu[layer].setdefault(net, []).append(track_poly(pts, w))
    for net, x, y in d.vias:
        for L in ("T", "B"):
            cu[L].setdefault(net, []).append(Point(x, y).buffer(G.VIA_D / 2, 32))
    for layer, net, x, y, w, h, kind in d.pads:
        cu[layer].setdefault(net, []).append(pad_poly(x, y, w, h))
    return {L: {n: unary_union(v) for n, v in nets.items()} for L, nets in cu.items()}


def keepouts(layer):
    """areas where no GND pour is wanted."""
    ko = []
    # nothing under the J1 body on top between the two pad rows (connector housing)
    if layer == "T":
        ko.append(box(G.J1C - 6.0, G.J1_FRONT_Y + 0.40, G.J1C + 6.0, G.J1_REAR_Y - 0.325))
    return unary_union(ko) if ko else Polygon()


def gnd_pour(d, cu, layer):
    board = Polygon(d.outline)
    region = board.buffer(-POUR_EDGE, join_style="mitre")
    others = [g for n, g in cu[layer].items() if n != "GND"]
    keep_out = unary_union(others).buffer(POUR_CLR, quad_segs=8)
    pour = region.difference(keep_out).difference(keepouts(layer))
    pour = pour.buffer(-0.13, join_style="mitre").buffer(0.13, join_style="mitre")   # no slivers < 0.26
    pour = pour.difference(keep_out)
    gnd = cu[layer].get("GND", Polygon())
    parts = [p for p in (pour.geoms if hasattr(pour, "geoms") else [pour]) if p.area > 0.15]
    merged = unary_union(parts + [gnd])
    comps = list(merged.geoms) if hasattr(merged, "geoms") else [merged]
    good = [c for c in comps if c.intersects(gnd)]
    return unary_union(good).difference(gnd).buffer(0)


def add_stitching(d, pitch=1.6):
    """Add GND vias wherever a via fits inside the GND pour on both layers."""
    cu = copper(d)
    pours = {L: gnd_pour(d, cu, L) for L in ("T", "B")}
    allvia = [(x, y) for _, x, y in d.vias]
    xs = [G.X0 + 0.9 + i * pitch for i in range(int((G.X1 - G.X0 - 1.8) / pitch) + 1)]
    ys = [0.9 + j * pitch for j in range(int((G.BOARD_TOP - 1.8) / pitch) + 1)]
    added = 0
    need = G.VIA_D / 2 + 0.25
    for x in xs:
        for y in ys:
            disk = Point(x, y).buffer(need, 24)
            if all(pours[L].contains(disk) for L in ("T", "B")) and \
                    all(math.hypot(x - a, y - b) > 0.9 for a, b in allvia):
                d.via("GND", x, y)
                allvia.append((x, y))
                added += 1
    return added


def full_copper(d):
    cu = copper(d)
    pours = {L: gnd_pour(d, cu, L) for L in ("T", "B")}
    for L in ("T", "B"):
        cu[L]["GND"] = unary_union([cu[L].get("GND", Polygon()), pours[L]])
    return cu, pours


def drc(d, cu, verbose=True):
    errs = []
    board = Polygon(d.outline)
    for L in ("T", "B"):
        items = list(cu[L].items())
        for (a, ga), (b, gb) in combinations(items, 2):
            dist = ga.distance(gb)
            if dist < MIN_CLR - 1e-6:
                p1 = ga.buffer(MIN_CLR).intersection(gb.buffer(0.001))
                c = p1.centroid if not p1.is_empty else None
                where = f" near ({c.x:.2f},{c.y:.2f})" if c else ""
                errs.append(f"{L}: {a} <-> {b} clearance {dist:.3f}{where}")
    edge = board.exterior
    for L in ("T", "B"):
        for n, g in cu[L].items():
            if not board.buffer(1e-6).contains(g):
                errs.append(f"{L}: {n} copper outside board")
            e = edge.distance(g)
            if e < EDGE_CLR - 1e-6:
                errs.append(f"{L}: {n} edge clearance {e:.3f}")
    for (na, xa, ya), (nb, xb, yb) in combinations(d.vias, 2):
        s = math.hypot(xa - xb, ya - yb)
        if na != nb and s < G.VIA_D + MIN_CLR - 1e-6:
            errs.append(f"via {na}@({xa:.2f},{ya:.2f}) too close to {nb}@({xb:.2f},{yb:.2f}) ({s:.3f})")
        if na == nb and s < G.VIA_DRILL + 0.30:
            errs.append(f"same-net vias too close {na}@({xa:.2f},{ya:.2f}) ({s:.3f})")
    if verbose:
        print(f"DRC: {len(errs)} problem(s)")
        for e in errs[:80]:
            print("  ", e)
    return errs


def terminals(d):
    """(layer, point, label, net) for every connector / passive pad."""
    out = []
    for c in range(1, 40):
        out.append(("T", Point(G.x_ce(c), G.y_ce(c)), f"CE{c}", G.ce_net(c)))
    for m in range(1, 51):
        n = G.kd_net(m)
        if n:
            out.append(("T", Point(G.x_kd(m), G.J2P), f"KD{m}", n))
    for layer, net, x, y, w, h, kind in d.pads:
        out.append((layer, Point(x, y), f"pad({x:.2f},{y:.2f})", net))
    return out


def connectivity(d, cu, verbose=True):
    errs = []
    nets = set(G.NETS) | {"GND"}
    for net in nets:
        pieces = []
        for L in ("T", "B"):
            g = cu[L].get(net)
            if g is None:
                continue
            for p in (g.geoms if hasattr(g, "geoms") else [g]):
                pieces.append((L, p))
        parent = list(range(len(pieces)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        for vn, x, y in d.vias:
            if vn != net:
                continue
            pt = Point(x, y)
            hit = [i for i, (L, p) in enumerate(pieces) if p.contains(pt)]
            if len(hit) != 2:
                errs.append(f"{net}: via ({x:.2f},{y:.2f}) hits {len(hit)} pieces")
            for a, b in zip(hit, hit[1:]):
                parent[find(a)] = find(b)
        roots = set()
        for L, pt, label, tn in terminals(d):
            if tn != net:
                continue
            hit = [i for i, (pl, p) in enumerate(pieces) if pl == L and p.contains(pt)]
            if not hit:
                errs.append(f"{net}: terminal {label} not covered")
                continue
            roots.add(find(hit[0]))
        if len(roots) > 1:
            errs.append(f"{net}: {len(roots)} separate pieces")
        all_roots = {find(i) for i in range(len(pieces))}
        if len(all_roots) > len(roots):
            errs.append(f"{net}: {len(all_roots) - len(roots)} floating piece(s)")
    if verbose:
        print(f"Connectivity: {len(errs)} problem(s)")
        for e in errs:
            print("  ", e)
    return errs


if __name__ == "__main__":
    d = G.build()
    n = add_stitching(d)
    cu, pours = full_copper(d)
    print("stitching vias", n)
    drc(d, cu)
    connectivity(d, cu)
    print("pour area", {L: round(p.area, 1) for L, p in pours.items()})
