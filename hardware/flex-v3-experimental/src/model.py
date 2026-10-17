"""Shapely model of the adapter: copper per layer/net, GND pour, DRC and connectivity checks."""
import math
from itertools import combinations
from shapely.geometry import LineString, Point, Polygon, box, MultiPolygon
from shapely.ops import unary_union
import geom as G

MIN_CLR = 0.10      # JLC FPC 0.5 oz: 3.5 mil; via ring to trace >= 0.1
PAD_CLR = 0.15      # JLC FPC: exposed pad to other copper >= 0.15
POUR_CLR = 0.20
EDGE_CLR = 0.30     # JLC FPC copper to edge >= 0.3 (gold fingers >= 0.2)


def track_poly(pts, w):
    if len(pts) == 1:
        return Point(pts[0]).buffer(w / 2, 24)
    return LineString(pts).buffer(w / 2, quad_segs=8, cap_style="round", join_style="round")


def pad_poly(x, y, w, h):
    return box(x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def copper(d):
    """dict layer -> dict net -> polygon (without pour)."""
    cu = {"T": {}, "B": {}}
    for layer, net, pts, w in d.tracks:
        cu[layer].setdefault(net, []).append(track_poly(pts, w))
    for net, x, y in d.vias:
        for L in ("T", "B"):
            cu[L].setdefault(net, []).append(Point(x, y).buffer(G.VIA_D / 2, 24))
    for layer, net, x, y, w, h, kind in d.pads:
        cu[layer].setdefault(net, []).append(pad_poly(x, y, w, h))
    return {L: {n: unary_union(v) for n, v in nets.items()} for L, nets in cu.items()}


def hatch(region, pitch=0.9, width=0.25):
    minx, miny, maxx, maxy = region.bounds
    lines = []
    span = (maxx - minx) + (maxy - miny)
    k = -span
    while k < span:
        lines.append(LineString([(minx + k, miny), (minx + k + span, miny + span)]).buffer(width / 2))
        lines.append(LineString([(maxx - k, miny), (maxx - k - span, miny + span)]).buffer(width / 2))
        k += pitch
    return region.intersection(unary_union(lines))


def gnd_pour(d, cu, layer="T"):
    board = Polygon(d.outline)
    region = board.buffer(-0.35).intersection(box(-30, 7.5, 30, 200))
    others = [g for n, g in cu[layer].items() if n != "GND"]
    if layer == "B":     # v3: no pour inside / near the J2 coverlay window (bottom side)
        xs = [G.x_kd(m) for m in range(1, 51)]
        region = region.difference(box(min(xs) - 0.8, G.PAD_BOT - 0.45, max(xs) + 0.8,
                                       G.J2_PAD_Y + G.J2_PAD[1] / 2 + 0.35))
    keep_out = unary_union(others).buffer(POUR_CLR)
    pour = region.difference(keep_out)
    # remove slivers narrower than ~0.25 mm
    pour = pour.buffer(-0.12).buffer(0.12)
    pour = pour.difference(keep_out)
    # hatch the neck (flex zone), solid elsewhere
    neck = box(-30, 7.5, 30, G.YN - 4.0)
    pour = unary_union([hatch(pour.intersection(neck)), pour.difference(neck)])
    gnd = cu[layer].get("GND")
    parts = list(pour.geoms) if hasattr(pour, "geoms") else [pour]
    # keep pieces that touch GND copper or are big enough to be fed by a neighbour piece
    keep = [p for p in parts if p.area > 0.05]
    merged = unary_union(keep + [gnd])
    # only keep the component(s) connected to GND copper
    comps = list(merged.geoms) if hasattr(merged, "geoms") else [merged]
    good = [c for c in comps if c.intersects(gnd)]
    return unary_union(good).difference(gnd).buffer(0)


def full_copper(d):
    cu = copper(d)
    pours = {L: gnd_pour(d, cu, L) for L in ("T", "B")}
    for L in ("T", "B"):
        cu[L]["GND"] = unary_union([cu[L]["GND"], pours[L]])
    return cu, pours


def drc(d, cu, verbose=True):
    errs = []
    board = Polygon(d.outline)
    for L in ("T", "B"):
        items = list(cu[L].items())
        for (a, ga), (b, gb) in combinations(items, 2):
            dist = ga.distance(gb)
            lim = MIN_CLR
            if dist < lim - 1e-6:
                errs.append(f"{L}: {a} <-> {b} clearance {dist:.3f}")
    # copper to board edge
    edge = board.exterior
    for L in ("T", "B"):
        for n, g in cu[L].items():
            if not board.buffer(1e-6).contains(g):
                errs.append(f"{L}: {n} copper outside board")
            e = edge.distance(g)
            # fingers are allowed to sit 0.2 from the tail side edges and 0.25 from the tip
            tail = g.intersection(box(-7, -1, 7, 5))
            rest = g.difference(box(-7, -1, 7, 5))
            if not rest.is_empty and edge.distance(rest) < EDGE_CLR - 1e-6:
                errs.append(f"{L}: {n} edge clearance {edge.distance(rest):.3f}")
            if not tail.is_empty and edge.distance(tail) < 0.20 - 1e-6:
                errs.append(f"{L}: {n} tail edge clearance {edge.distance(tail):.3f}")
    # exposed pads (coverlay openings) need 0.15 mm to any other net's copper
    raw = copper(d)
    import copy as _c
    dn = _c.copy(d)
    dn.pads = [p for p in d.pads if p[6] != "finger"]
    raw_nf = copper(dn)      # gold fingers share one coverlay window: finger-finger gap 0.14 is the FFC norm
    for L, pn, x, y, w, h, kind in d.pads:
        pp = pad_poly(x, y, w, h)
        for n, g in (raw_nf if kind == "finger" else raw)[L].items():
            if n == pn:
                continue
            dist = pp.distance(g)
            if dist < PAD_CLR - 1e-6:
                errs.append(f"{L}: pad {pn}@({x:.2f},{y:.2f}) to {n} {dist:.3f} < {PAD_CLR}")
    # drill spacing
    for (na, xa, ya), (nb, xb, yb) in combinations(d.vias, 2):
        s = math.hypot(xa - xb, ya - yb)
        if s < G.VIA_DRILL + 0.20 and na != nb:
            errs.append(f"via {na}@({xa:.2f},{ya:.2f}) too close to {nb} ({s:.3f})")
        if s < 0.45 and na == nb:
            errs.append(f"same-net vias overlap/too close {na}@({xa:.2f},{ya:.2f}) ({s:.3f})")
    # nothing on the bottom inside the PI stiffener zone of the tail
    for n, g in cu["B"].items():
        if g.intersects(box(-7, -1, 7, 6.0)):
            errs.append(f"B: {n} copper inside tail stiffener zone")
    if verbose:
        print(f"DRC: {len(errs)} problem(s)")
        for e in errs[:60]:
            print("  ", e)
    return errs


def connectivity(d, cu, verbose=True):
    """Every net must be one connected piece containing all its terminals."""
    errs = []
    for net, (ce_pins, kd_pins) in list(G.NETS.items()):
        pieces = []
        for L in ("T", "B"):
            g = cu[L].get(net)
            if g is None:
                continue
            for p in (g.geoms if hasattr(g, "geoms") else [g]):
                pieces.append((L, p))
        # union-find over pieces; same-layer pieces are already disjoint; vias join layers
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
            for a, b in zip(hit, hit[1:]):
                parent[find(a)] = find(b)
        terms = []
        for n in ce_pins:
            terms.append(("T", Point(G.x_ce(n), 1.0), f"CE{n}"))
        for m in kd_pins:
            terms.append(("B", Point(G.x_kd(m), G.J2_PAD_Y), f"KD{m}"))
        for layer, pn, x, y, w, h, kind in d.pads:
            if pn == net and kind == "smd" and (abs(y - G.J2_PAD_Y) > 0.01):
                terms.append((layer, Point(x, y), f"pad({x:.2f},{y:.2f})"))
        roots = set()
        for L, pt, label in terms:
            hit = [i for i, (pl, p) in enumerate(pieces) if pl == L and p.contains(pt)]
            if not hit:
                errs.append(f"{net}: terminal {label} not covered by copper")
                continue
            roots.add(find(hit[0]))
        if len(roots) > 1:
            errs.append(f"{net}: {len(roots)} separate pieces")
        # dangling pieces
        all_roots = {find(i) for i in range(len(pieces))}
        if len(all_roots) > len(roots) and net != "GND":
            errs.append(f"{net}: {len(all_roots) - len(roots)} floating copper piece(s)")
    if verbose:
        print(f"Connectivity: {len(errs)} problem(s)")
        for e in errs:
            print("  ", e)
    return errs


if __name__ == "__main__":
    d = G.build()
    cu, pours = full_copper(d)
    drc(d, cu)
    connectivity(d, cu)
    print("pour area", {L: round(p.area, 1) for L, p in pours.items()})
