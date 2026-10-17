"""Previews + 1:1 PDF for flex v3."""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Polygon as MPoly, Circle, Rectangle
from shapely.geometry import Polygon, box
from shapely.affinity import scale
import geom as G
import model as M

TOPC, BOTC, POURT, POURB = "#d84a3a", "#3a6fd8", "#f3cfc6", "#c9d6f2"
BOARDC = "#f2dca8"


def dg(ax, g, fc, alpha=1.0, z=1, mirror=False, ec="none", lw=0):
    if g is None or g.is_empty:
        return
    if mirror:
        g = scale(g, xfact=-1, yfact=1, origin=(0, 0))
    for p in (g.geoms if hasattr(g, "geoms") else [g]):
        if p.geom_type != "Polygon":
            continue
        ax.add_patch(MPoly(list(p.exterior.coords), closed=True, fc=fc, ec=ec, lw=lw, alpha=alpha, zorder=z))
        for h in p.interiors:
            ax.add_patch(MPoly(list(h.coords), closed=True, fc=BOARDC, ec="none", zorder=z))


def side_view(ax, d, cu, pours, side, lw=0.5):
    """side 'T': seen from the top; side 'B': seen from below (x mirrored)."""
    mir = side == "B"
    outline = Polygon(d.outline)
    dg(ax, outline, BOARDC, 1, 0, mir, ec="#333", lw=lw)
    far, near = ("B", "T") if side == "T" else ("T", "B")
    farc, nearc = (BOTC, TOPC) if side == "T" else (TOPC, BOTC)
    pourc = POURT if side == "T" else POURB
    for n, g in cu[far].items():
        dg(ax, g if n != "GND" else g.difference(pours[far]), farc, 0.18, 1, mir)
    dg(ax, pours[near], pourc, 1.0, 2, mir)
    for n, g in cu[near].items():
        dg(ax, g.difference(pours[near]) if n == "GND" else g, nearc, 0.9, 3, mir)
    sx = -1 if mir else 1
    for n, x, y in d.vias:
        ax.add_patch(Circle((sx * x, y), G.VIA_DRILL / 2, fc="black", ec="none", zorder=4))
    # stiffeners
    if side == "B":
        ax.add_patch(Rectangle((-G.TAIL_W / 2, 0), G.TAIL_W, G.PI_STIFF_Y1, fc="none", ec="#7a4b00",
                               hatch="////", lw=0.6, zorder=5))
    else:
        head = outline.intersection(box(-30, G.FR4_Y0, 30, 200)).buffer(-0.2)
        ax.add_patch(MPoly(list(head.exterior.coords), closed=True, fc="none", ec="#2a7a2a",
                           hatch="\\\\", lw=0.6, alpha=0.6, zorder=5))
    ax.set_xlim(-21, 21)
    ax.set_ylim(-1.5, G.BOARD_TOP + 1.5)
    ax.set_aspect("equal")
    ax.axis("off")


def label_pins(ax, side):
    sx = -1 if side == "B" else 1
    if side == "B":
        for m in (1, 13, 23, 40, 50):
            ax.text(sx * G.x_kd(m), G.J2_PAD_Y + 1.15, str(m), fontsize=5, ha="center", zorder=6)
    for n in (1, 39):
        ax.text(sx * G.x_ce(n), 3.4, str(n), fontsize=5, ha="center", zorder=6,
                color="black")


def previews(d, cu, pours, outdir):
    for side, title, fn in (
            ("T", "MAT TREN (F_Cu): tiep diem vang cam vao CE. Gach xanh la = tam FR4 dan mat nay", "preview-top.png"),
            ("B", "MAT DUOI (B_Cu) nhin tu duoi: J2 + R1/C1/C2 lap o mat nay. Gach nau = tam PI o duoi", "preview-bottom.png")):
        fig, ax = plt.subplots(figsize=(6.2, 12))
        side_view(ax, d, cu, pours, side)
        label_pins(ax, side)
        ax.set_title(title, fontsize=7)
        fig.savefig(f"{outdir}/{fn}", dpi=220)
        plt.close(fig)


def pdf(d, cu, pours, path):
    W, H = 8.27, 11.69
    with PdfPages(path) as pp:
        fig = plt.figure(figsize=(W, H))
        # 1:1 scale: axes sized in inches = mm / 25.4
        bw = 45.0
        for i, (side, title) in enumerate((("T", "MAT TREN (tiep diem CE)"), ("B", "MAT DUOI nhin tu duoi (J2)"))):
            x0 = 0.6 + i * (bw + 8) / 25.4
            ax = fig.add_axes([x0 / W, 1.6 / H, (bw / 25.4) / W, (80 / 25.4) / H])
            ax.set_xlim(-bw / 2, bw / 2)
            ax.set_ylim(-2, 78)
            side_view(ax, d, cu, pours, side, lw=0.3)
            ax.set_xlim(-bw / 2, bw / 2)          # axes box is exactly bw x 80 mm -> 1:1
            ax.set_ylim(-2, 78)
            label_pins(ax, side)
            ax.set_title(title, fontsize=8)
        fig.text(0.5, 0.97, "Flex TI-84 CE -> KD028 v3  -  IN 100% (Actual size / Ty le thuc). "
                 "Thuoc kiem tra 50 mm duoi day.", ha="center", fontsize=9)
        ax = fig.add_axes([0.6 / W, 0.7 / H, (50 / 25.4) / W, (3 / 25.4) / H])
        ax.set_xlim(0, 50); ax.set_ylim(0, 3); ax.axis("off")
        ax.plot([0, 50], [1.5, 1.5], "k-", lw=1)
        for k in range(0, 51, 10):
            ax.plot([k, k], [0.5, 2.5], "k-", lw=0.8)
        ax.text(25, 2.6, "50 mm", ha="center", fontsize=7)
        pp.savefig(fig)
        plt.close(fig)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "out"
    d = G.build()
    cu, pours = M.full_copper(d)
    previews(d, cu, pours, out)
    pdf(d, cu, pours, f"{out}/ti84ce-kd028-flex-v3-in-1-1.pdf")
    print("ok")
