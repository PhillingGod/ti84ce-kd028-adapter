"""Minimal RS-274X Gerber writer (apertures, regions, flashes, text outlines)."""
import os
import sys
import numpy as np
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path as MPath


FONT = FontProperties(family="DejaVu Sans", weight="bold")


def c(v):
    return int(round(v * 1e6))


class Gerber:
    def __init__(self, func, polarity="Positive"):
        self.lines = ["%FSLAX46Y46*%", "%MOMM*%",
                      f"%TF.FileFunction,{func}*%", f"%TF.FilePolarity,{polarity}*%",
                      "%TF.GenerationSoftware,custom-python,ti84ce-flex,1*%", "%LPD*%"]
        self.aps = {}
        self.body = []
        self.cur_ap = None
        self.pol = "D"

    def ap(self, kind, *dims):
        key = (kind,) + tuple(round(d, 4) for d in dims)
        if key not in self.aps:
            code = 10 + len(self.aps)
            self.aps[key] = code
        return self.aps[key]

    def use(self, code):
        if code != self.cur_ap:
            self.body.append(f"D{code}*")
            self.cur_ap = code

    def polarity(self, p):
        if p != self.pol:
            self.body.append(f"%LP{p}*%")
            self.pol = p

    def flash(self, code, x, y):
        self.use(code)
        self.body.append(f"X{c(x)}Y{c(y)}D03*")

    def track(self, pts, w):
        self.use(self.ap("C", w))
        x0, y0 = pts[0]
        self.body.append(f"X{c(x0)}Y{c(y0)}D02*")
        for x, y in pts[1:]:
            self.body.append(f"X{c(x)}Y{c(y)}D01*")

    def region(self, pts):
        self.body.append("G36*")
        x0, y0 = pts[0]
        self.body.append(f"X{c(x0)}Y{c(y0)}D02*")
        for x, y in pts[1:]:
            self.body.append(f"X{c(x)}Y{c(y)}D01*")
        self.body.append(f"X{c(x0)}Y{c(y0)}D01*")
        self.body.append("G37*")

    def rect(self, x0, y0, x1, y1):
        self.region([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])

    def text(self, s, x, y, size, rot=0, anchor="center"):
        tp = TextPath((0, 0), s, size=size, prop=FONT)
        polys = [p for p in tp.to_polygons() if len(p) > 2]
        if not polys:
            return
        allp = np.vstack(polys)
        xmin, ymin = allp.min(axis=0)
        xmax, ymax = allp.max(axis=0)
        if anchor == "center":
            ox, oy = -(xmin + xmax) / 2, -(ymin + ymax) / 2
        else:  # left-middle
            ox, oy = -xmin, -(ymin + ymax) / 2
        th = np.radians(rot)
        R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])

        def tf(p):
            q = (p + [ox, oy]) @ R.T
            return [(a + x, b + y) for a, b in q]

        # outer contours dark, holes clear (holes = polygons inside another polygon)
        paths = [MPath(p) for p in polys]
        is_hole = []
        for i, p in enumerate(polys):
            inside = any(j != i and paths[j].contains_point(p[0]) for j in range(len(polys)))
            is_hole.append(inside)
        for i, p in enumerate(polys):
            if not is_hole[i]:
                self.polarity("D")
                self.region(tf(p))
        for i, p in enumerate(polys):
            if is_hole[i]:
                self.polarity("C")
                self.region(tf(p))
        self.polarity("D")

    def write(self, path):
        head = list(self.lines)
        for key, code in sorted(self.aps.items(), key=lambda kv: kv[1]):
            kind, *d = key
            if kind == "C":
                head.append(f"%ADD{code}C,{d[0]:.4f}*%")
            elif kind == "R":
                head.append(f"%ADD{code}R,{d[0]:.4f}X{d[1]:.4f}*%")
        with open(path, "w") as f:
            f.write("\n".join(head + self.body + ["M02*"]) + "\n")


