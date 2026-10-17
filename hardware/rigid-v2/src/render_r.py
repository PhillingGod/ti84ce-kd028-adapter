"""Preview PNGs and a printable PDF (1:1 page + check pages) for the rigid adapter."""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Polygon as MPoly, Circle, Rectangle, FancyBboxPatch
from shapely.affinity import scale as shp_scale
import geom_r as G
import model_r as M
import out_r as O

plt.rcParams["font.family"] = "DejaVu Sans"
FR4, TOPC, BOTC, POURT, POURB, PADC, SILK = "#2f6b3a", "#d9534f", "#3a7bd5", "#c98b7a", "#7fa3d6", "#e8c547", "white"


def dg(ax, g, fc, alpha=1.0, z=1, hole=FR4):
    if g.is_empty:
        return
    for p in (g.geoms if hasattr(g, "geoms") else [g]):
        if p.geom_type != "Polygon":
            continue
        ax.add_patch(MPoly(list(p.exterior.coords), closed=True, fc=fc, ec="none", alpha=alpha, zorder=z))
        for h in p.interiors:
            ax.add_patch(MPoly(list(h.coords), closed=True, fc=hole, ec="none", zorder=z))


def top_view(ax, d, cu, pours, lw=0.5, silk=True, bodies=True):
    ax.add_patch(MPoly(d.outline, closed=True, fc=FR4, ec="black", lw=lw, zorder=0))
    for n, g in cu["B"].items():
        dg(ax, g, BOTC, 0.25, 1)
    dg(ax, pours["T"], POURT, 0.55, 2)
    for n, g in cu["T"].items():
        dg(ax, g.difference(pours["T"]) if n == "GND" else g, TOPC, 0.95, 3)
    for L, net, x, y, w, h, kind in d.pads:
        ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fc=PADC, ec="none", zorder=4))
    for n, x, y in d.vias:
        ax.add_patch(Circle((x, y), G.VIA_DRILL / 2, fc="black", ec="none", zorder=5))
    if silk:
        dg(ax, O.silk_top_geom(d).difference(O.mask_openings(d).buffer(0.1)), SILK, 1.0, 6)
    if bodies:
        # connector bodies (outline only)
        ax.add_patch(Rectangle((G.J1C - 6.6, G.J1Y - 1.95), 13.2, 3.3, fc="none", ec="#222", lw=0.7, ls="--", zorder=7))
        ax.add_patch(Rectangle((-14.05, G.YZ - 1.2), 28.1, 5.6, fc="none", ec="#222", lw=0.7, ls="--", zorder=7))


def bottom_view(ax, d, cu, pours, lw=0.5):
    m = lambda g: shp_scale(g, xfact=-1, yfact=1, origin=(0, 0))
    ax.add_patch(MPoly([(-x, y) for x, y in d.outline], closed=True, fc=FR4, ec="black", lw=lw, zorder=0))
    dg(ax, m(pours["B"]), POURB, 0.6, 2)
    for n, g in cu["B"].items():
        dg(ax, m(g.difference(pours["B"]) if n == "GND" else g), BOTC, 0.95, 3)
    for n, x, y in d.vias:
        ax.add_patch(Circle((-x, y), G.VIA_DRILL / 2, fc="black", ec="none", zorder=5))
    dg(ax, m(O.silk_bot_geom(d)), SILK, 1.0, 6)


def previews(d, cu, pours, outdir):
    fig, ax = plt.subplots(figsize=(10, 7.8))
    top_view(ax, d, cu, pours)
    ax.set_xlim(G.X0 - 0.6, G.X1 + 0.6); ax.set_ylim(-1.6, G.BOARD_TOP + 1.6); ax.set_aspect("equal"); ax.axis("off")
    ax.annotate("", xy=(G.J1C, 1.0), xytext=(G.J1C, -1.5), arrowprops=dict(arrowstyle="->", lw=1.6))
    ax.text(G.J1C + 0.4, -1.2, "dây FFC 39P 0.3 mm (CÙNG CHIỀU) cắm vào J1 từ cạnh dưới", fontsize=8)
    ax.annotate("", xy=(0, G.BOARD_TOP - 1.0), xytext=(0, G.BOARD_TOP + 1.5), arrowprops=dict(arrowstyle="->", lw=1.6))
    ax.text(0.4, G.BOARD_TOP + 0.9, "cáp màn KD028 cắm vào J2 từ cạnh trên", fontsize=8)
    ax.set_title(f"MẶT TRÊN (mặt có linh kiện) – {G.X1 - G.X0:.1f} × {G.BOARD_TOP:.1f} mm. Đỏ = đồng mặt trên, xanh mờ = mặt dưới",
                 fontsize=9)
    fig.savefig(f"{outdir}/preview-top.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 7.8))
    bottom_view(ax, d, cu, pours)
    ax.set_xlim(-G.X1 - 0.6, -G.X0 + 0.6); ax.set_ylim(-1.0, G.BOARD_TOP + 1.0); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("MẶT DƯỚI (không có linh kiện), nhìn từ dưới lên", fontsize=9)
    fig.savefig(f"{outdir}/preview-bottom.png", dpi=200, bbox_inches="tight"); plt.close(fig)


def ffc_sketch(ax, x0, y0, typ):
    """Flat FFC seen from one face. Contacts drawn gold where they face the viewer."""
    L, W = 34, 6
    ax.add_patch(Rectangle((x0, y0), W, L, fc="#f3e7c9", ec="#555", lw=0.8))
    # end A (bottom): contacts towards viewer
    ax.add_patch(Rectangle((x0, y0), W, 3.5, fc="#d4a017", ec="none"))
    for i in range(12):
        ax.plot([x0 + 0.4 + i * 0.47] * 2, [y0 + 0.2, y0 + 3.3], color="#8a6d0b", lw=0.6)
    if typ == "B":
        ax.add_patch(Rectangle((x0, y0 + L - 3.5), W, 3.5, fc="#2a62b8", ec="none"))
        ax.text(x0 + W / 2, y0 + L - 1.75, "nẹp\nxanh", ha="center", va="center", fontsize=6.5, color="white")
    else:
        ax.add_patch(Rectangle((x0, y0 + L - 3.5), W, 3.5, fc="#d4a017", ec="none"))
        for i in range(12):
            ax.plot([x0 + 0.4 + i * 0.47] * 2, [y0 + L - 3.3, y0 + L - 0.2], color="#8a6d0b", lw=0.6)


def pdf(d, cu, pours, path):
    A4 = (210 / 25.4, 297 / 25.4)
    with PdfPages(path) as pp:
        # ---------- page 1: 1:1
        fig = plt.figure(figsize=A4)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(-105, 105); ax.set_ylim(-200, 97); ax.set_aspect("equal"); ax.axis("off")
        top_view(ax, d, cu, pours, lw=0.3)
        ax.plot([-80, -30], [-20, -20], "k", lw=1.5)
        for x in (-80, -30):
            ax.plot([x, x], [-22, -18], "k", lw=1.5)
        ax.text(-55, -16, "Thước kiểm tra: đúng 50 mm", ha="center", fontsize=9)
        ax.text(-98, 88, "TRANG 1 – TỈ LỆ 1:1 (in 'Actual size / 100%'). Nhìn từ MẶT TRÊN (mặt có linh kiện).",
                fontsize=8.5, weight="bold")
        ax.text(-98, 82, f"Board cứng 2 lớp {G.X1 - G.X0:.1f} × {G.BOARD_TOP:.1f} mm, dày 0.8 mm. "
                         "J1 ở cạnh dưới (dây FFC), J2 ở cạnh trên (cáp màn KD028).", fontsize=7.5)
        ax.text(-98, 77, "Cắt hình chữ nhật này ra, đặt thử vào trong máy để xem có vừa chỗ không trước khi đặt hàng.",
                fontsize=7.5)
        pp.savefig(fig); plt.close(fig)

        # ---------- page 2: FFC type + J1 orientation + mainboard check
        fig = plt.figure(figsize=A4)
        fig.text(0.06, 0.965, "TRANG 2 – DÂY FFC VÀ ĐẦU J1", fontsize=12, weight="bold")
        ax = fig.add_axes([0.06, 0.62, 0.40, 0.32])
        ax.set_xlim(-2, 30); ax.set_ylim(-4, 38); ax.set_aspect("equal"); ax.axis("off")
        ffc_sketch(ax, 1, 0, "A"); ffc_sketch(ax, 17, 0, "B")
        ax.text(4, -3, "CÙNG CHIỀU (A)\n→ MUA LOẠI NÀY", ha="center", fontsize=8.5, weight="bold", color="#0a7a2a")
        ax.text(20, -3, "NGƯỢC CHIỀU (B)\n→ KHÔNG DÙNG ĐƯỢC", ha="center", fontsize=8.5, weight="bold", color="#b22")
        fig.text(0.50, 0.93,
                 "Cách phân biệt: đặt dây nằm phẳng trên bàn, nhìn từ trên xuống.\n"
                 "• Cùng chiều (A): cả hai đầu đều thấy tiếp điểm vàng (nẹp xanh\n"
                 "  ở mặt dưới cả hai đầu).\n"
                 "• Ngược chiều (B): một đầu thấy tiếp điểm vàng, đầu kia thấy nẹp.\n\n"
                 "Thông số cần mua:\n"
                 "• 39 chân (39P), bước 0.3 mm (pitch 0.3 mm)\n"
                 "• CÙNG CHIỀU / Type A / same side / forward\n"
                 "• Đầu tiếp điểm dày 0.2 mm (loại chuẩn cho đầu nối 0.3 mm)\n"
                 "• Dài: đo trong máy (nên mua 2 loại, ví dụ 6 cm và 10 cm)\n"
                 "• Rộng ~12 mm",
                 fontsize=8.3, va="top")
        ax = fig.add_axes([0.06, 0.30, 0.88, 0.30])
        top_view(ax, d, cu, pours, lw=0.8, silk=True)
        ax.set_xlim(-10.2, 6.2); ax.set_ylim(-1.2, 7.2); ax.set_aspect("equal"); ax.axis("off")
        for c in range(1, 40):
            col = "red" if G.CE[c] == "GND" else "black"
            ax.text(G.x_ce(c), -0.65, str(c), ha="center", va="center", fontsize=5.5, color=col, rotation=90,
                    weight="bold" if G.CE[c] == "GND" else None, zorder=9)
        ax.add_patch(Rectangle((-10.2, -1.2), 16.4, 1.15, fc="white", ec="none", zorder=8))
        fig.text(0.06, 0.605, "J1 nhìn từ mặt trên. Số dưới cùng = chân CE (GPM1421C0) đi tới tiếp điểm đó "
                              "(đỏ = GND). Chân 1 bên PHẢI.", fontsize=7.5)
        fig.text(0.06, 0.28,
                 "CÁCH CẮM DÂY:\n"
                 "• Tháo pin trước khi cắm/rút.\n"
                 "• Đầu nối trên mainboard CE và J1 đều là loại tiếp điểm DƯỚI: ở cả hai đầu, mặt tiếp điểm vàng của dây\n"
                 "  ÚP XUỐNG board, mặt nẹp hướng lên. Lật nắp khóa lên, đẩy dây vào hết, đóng nắp.\n"
                 "• Dây cùng chiều: hai đầu như nhau – đầu nào vào CE cũng được. Dây gập/xoắn ở giữa không sao.\n"
                 "• J1: lật thanh khóa màu ĐEN (phía J2) lên, đẩy dây vào từ cạnh dưới cho hết, đóng thanh đen xuống.\n\n"
                 "KIỂM TRA ĐẦU NỐI TRÊN MAINBOARD (đã làm ở bản flex, giữ nguyên):\n"
                 "1. Tháo pin. Đồng hồ chế độ thông mạch, một que chạm TP-GND1.\n"
                 "2. Đặt máy: phần màn ở trên, đầu nối màn ở góc trên-trái, nhìn từ phía sau máy.\n"
                 "3. Kim may chạm lần lượt chân hàn ở hai đầu đầu nối. Đầu có 3 chân liền nhau cùng hàng đều kêu\n"
                 "   (chân 35, 37, 39 = GND) phải nằm bên TRÁI. Nếu ngược lại: đừng cắm, báo lại.",
                 fontsize=8.2, va="top")
        pp.savefig(fig); plt.close(fig)

        # ---------- page 3: J2 + panel check
        fig = plt.figure(figsize=A4)
        fig.text(0.06, 0.965, "TRANG 3 – J2 VÀ CÁP MÀN KD028QVFMA027", fontsize=12, weight="bold")
        ax = fig.add_axes([0.04, 0.55, 0.92, 0.38])
        top_view(ax, d, cu, pours, lw=0.8)
        ax.set_xlim(-15.8, 15.8); ax.set_ylim(G.J2P - 4.4, G.BOARD_TOP + 2.2); ax.set_aspect("equal"); ax.axis("off")
        ax.add_patch(Rectangle((-16, G.J2P - 4.4), 32, 3.05, fc="white", ec="none", zorder=8))
        for m in range(1, 51):
            nm = G.KD.get(m, "")
            ax.text(G.x_kd(m), G.J2P - 2.1, str(m), ha="center", va="center", fontsize=4.8, rotation=90,
                    color="red" if nm == "GND" else "black", zorder=9)
        ax.annotate("", xy=(0, G.BOARD_TOP - 0.6), xytext=(0, G.BOARD_TOP + 2.0), arrowprops=dict(arrowstyle="->", lw=1.5))
        ax.text(0.6, G.BOARD_TOP + 1.3, "cáp màn KD028 cắm vào đây (tiếp điểm vàng ÚP XUỐNG)", fontsize=7)
        ax.text(-15.5, G.J2P - 3.7, "Số = chân của màn KD028 đi tới tiếp điểm đó (đỏ = GND). Chân 1 bên TRÁI, chân 50 bên PHẢI "
                "(nhìn từ mặt trên).", fontsize=7, zorder=9)
        fig.text(0.06, 0.52,
                 "KIỂM TRA KHI NHẬN MÀN (trước khi đặt board / trước khi cắm):\n\n"
                 "Chân màn: 1 = GND, 42 = GND, 50 = GND, 9 = VCI. Hai đầu dãy tiếp điểm đều là GND, nên phân biệt bằng\n"
                 "ngón thứ 9: ở đầu chân 50, ngón ngoài cùng và ngón thứ 9 (chân 42) KÊU với nhau; ở đầu chân 1 thì KHÔNG.\n\n"
                 "1. Đồng hồ thông mạch. Đo như trên để biết đầu nào là chân 1, đầu nào là chân 50 (đánh dấu bằng bút).\n"
                 "2. Màn để NGỬA (mặt kính lên trên), cáp gập ra sau như lúc giao hàng, đuôi cáp thò ra một bên.\n"
                 "   Mặt trên của đuôi cáp là miếng nẹp có chữ in trắng; tiếp điểm vàng nằm ở MẶT DƯỚI.\n"
                 "3. Board để mặt linh kiện lên, J2 ở cạnh xa bạn. Xoay màn (vẫn ngửa) sao cho đuôi cáp chĩa vào J2.\n"
                 "   Lúc này CHÂN 1 phải ở bên TRÁI, chân 50 bên PHẢI (đúng như số in trên board cạnh J2).\n"
                 "   Theo bản vẽ của hãng thì sẽ đúng như vậy. Nếu ngược lại: KHÔNG cắm, báo lại.\n"
                 "4. Đẩy đuôi cáp vào J2 (tiếp điểm úp xuống), đóng nắp khóa J2.\n\n"
                 "BẬT THỬ: lắp pin, bật máy. Hình âm bản → cần chương trình bật đảo màu (INVON).\n"
                 "Đỏ/xanh dương đổi chỗ hoặc hình bị lật → sửa bằng phần mềm (MADCTL).",
                 fontsize=8.2, va="top")
        pp.savefig(fig); plt.close(fig)


if __name__ == "__main__":
    outdir = sys.argv[1] if len(sys.argv) > 1 else "out"
    d = G.build()
    M.add_stitching(d)
    cu, pours = M.full_copper(d)
    previews(d, cu, pours, outdir)
    pdf(d, cu, pours, f"{outdir}/ti84ce-kd028-rigid-in-1-1.pdf")
    print("ok")
