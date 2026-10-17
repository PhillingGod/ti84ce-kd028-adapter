"""One-page illustrated guide: how pin reversal could happen and how to prevent it."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, FancyBboxPatch, Arc
from matplotlib.backends.backend_pdf import PdfPages

plt.rcParams["font.family"] = "DejaVu Sans"
GOLD, BLUE, BOARD, BODY, BLK, RED, GRN = "#d4a017", "#2a62b8", "#2f6b3a", "#c9b38a", "#222", "#c0392b", "#1e8449"


def ffc(ax, x, y, w, L, top_gold, bot_gold, label=None):
    ax.add_patch(Rectangle((x, y), w, L, fc="#f3e7c9", ec="#555", lw=0.8))
    for yy, g in ((y, bot_gold), (y + L - 3, top_gold)):
        ax.add_patch(Rectangle((x, yy), w, 3, fc=GOLD if g else BLUE, ec="none"))
        if g:
            for i in range(9):
                ax.plot([x + 0.5 + i * (w - 1) / 8] * 2, [yy + 0.3, yy + 2.7], color="#7a5e08", lw=0.7)
    if label:
        ax.text(x + w / 2, y - 2.2, label, ha="center", va="top", fontsize=8.5, weight="bold")


def tick(ax, x, y, ok):
    ax.text(x, y, "✔" if ok else "✘", fontsize=22, color=GRN if ok else RED, ha="center", va="center", weight="bold")


def panel_a(ax):
    ax.set_xlim(0, 60); ax.set_ylim(-12, 40); ax.axis("off")
    ax.set_title("① Loại dây FFC  (rủi ro lớn nhất)", fontsize=11, weight="bold", loc="left")
    ffc(ax, 6, 0, 9, 34, True, True, "CÙNG CHIỀU (A)\nhai đầu đều thấy vàng")
    ffc(ax, 36, 0, 9, 34, False, True, "NGƯỢC CHIỀU (B)\nmột đầu vàng, một đầu nẹp")
    tick(ax, 10.5, 37.5, True); tick(ax, 40.5, 37.5, False)
    ax.text(30, -10.5, "Mua nhầm loại B → toàn bộ 39 chân bị đảo thứ tự.\n"
            "Phòng: đặt dây nằm phẳng, nhìn từ trên – phải thấy tiếp điểm vàng ở CẢ HAI đầu.",
            ha="center", fontsize=8.3, va="bottom")


def zif(ax, x0, y0, contacts_down, title, ok):
    # board
    ax.add_patch(Rectangle((x0, y0), 26, 1.6, fc=BOARD, ec="none"))
    # connector body (side view): contacts on the BOTTOM of the slot
    ax.add_patch(Rectangle((x0 + 14, y0 + 1.6), 9, 4.2, fc=BODY, ec="#555", lw=0.8))
    ax.add_patch(Rectangle((x0 + 14, y0 + 2.4), 6.5, 1.2, fc="white", ec="none"))       # slot
    for i in range(3):
        ax.plot([x0 + 15 + i * 1.8, x0 + 16 + i * 1.8], [y0 + 2.4, y0 + 2.4], color=GOLD, lw=3)  # bottom springs
    ax.add_patch(Rectangle((x0 + 20.5, y0 + 5.8), 2.5, 0.0, fc=BLK))
    ax.add_patch(Rectangle((x0 + 19.5, y0 + 5.8), 4.5, 1.0, fc=BLK, ec="none"))           # actuator
    # cable
    yc = y0 + 2.6
    ax.add_patch(Rectangle((x0 + 1, yc), 19, 0.5, fc="#f3e7c9", ec="#555", lw=0.6))
    gold_y, blue_y = (yc - 0.0, yc + 0.5) if contacts_down else (yc + 0.5, yc - 0.0)
    ax.add_patch(Rectangle((x0 + 13, gold_y if contacts_down else yc + 0.5), 7, 0.35, fc=GOLD, ec="#7a5e08", lw=0.5))
    ax.add_patch(Rectangle((x0 + 13, yc + 0.5 if contacts_down else yc - 0.35), 7, 0.35, fc=BLUE, ec="none"))
    ax.text(x0 + 6, yc + 1.2, "dây", fontsize=7)
    ax.text(x0 + 6, y0 - 1.3, "board", fontsize=7)
    ax.text(x0 + 13, y0 + 8.6, title, ha="center", fontsize=8.3, weight="bold", color=GRN if ok else RED)
    tick(ax, x0 + 27.5, y0 + 4, ok)


def panel_b(ax):
    ax.set_xlim(0, 62); ax.set_ylim(-9, 30); ax.axis("off")
    ax.set_title("② Chiều tiếp điểm khi cắm  (cả 3 đầu nối đều tiếp điểm DƯỚI)", fontsize=11, weight="bold", loc="left")
    zif(ax, 1, 15, True, "Tiếp điểm vàng ÚP XUỐNG board, nẹp xanh lên trên", True)
    zif(ax, 1, 1, False, "Tiếp điểm ngửa lên → không chạm lò xo", False)
    ax.text(31, -8.5, "Cắm úp ngược chỉ làm màn không lên (không có chân nào chạm), KHÔNG làm đảo chân.\n"
            "Áp dụng cho J01H trên mainboard, J1 và J2. Lật thanh khóa đen lên → đẩy dây vào hết → đóng xuống.",
            ha="center", fontsize=8.3, va="bottom")


def panel_c(ax):
    ax.set_xlim(0, 120); ax.set_ylim(-6, 46); ax.axis("off")
    ax.set_title("③ Chân 1 ở mỗi đầu  (nhìn từ phía nắp lưng, máy đặt màn ở trên)", fontsize=11, weight="bold", loc="left")
    # mainboard connector J01H
    ax.add_patch(Rectangle((2, 2), 34, 18, fc=BOARD, ec="none"))
    ax.text(19, 3.5, "mainboard CE", ha="center", color="white", fontsize=8)
    ax.add_patch(Rectangle((6, 12), 26, 3, fc=BODY, ec="#555"))
    ax.add_patch(Rectangle((6, 9.5), 26, 2.5, fc=BLK, ec="none"))
    ax.text(19, 16.2, "J01H", ha="center", fontsize=8, color="white")
    ax.text(33.5, 13.5, "1", fontsize=11, weight="bold", color="yellow", va="center")
    ax.text(3.2, 13.5, "39", fontsize=9, weight="bold", color="white", va="center")
    ax.annotate("", xy=(33.5, 11), xytext=(33.5, 7), arrowprops=dict(arrowstyle="->", color="white", lw=1.5))
    ax.text(30, 5.6, "mũi tên in trên board", fontsize=6.5, color="white", ha="right")
    # FFC from J01H going up then to J1
    ax.add_patch(Rectangle((8, 15), 22, 14, fc="#f3e7c9", ec="#555", alpha=0.9))
    ax.text(19, 24, "dây FFC\ncùng chiều", ha="center", fontsize=8)
    # adapter
    ax.add_patch(Rectangle((48, 2), 40, 30, fc=BOARD, ec="none"))
    ax.text(68, 17, "board adapter\n(mặt linh kiện)", ha="center", color="white", fontsize=8)
    ax.add_patch(Rectangle((58, 4), 20, 3.2, fc=BODY, ec="#555")); ax.add_patch(Rectangle((58, 7.2), 20, 2, fc=BLK))
    ax.text(68, 1, "J1  (dây vào từ cạnh dưới)", ha="center", fontsize=7.5, va="top")
    ax.text(79, 5.5, "1", fontsize=11, weight="bold", color="yellow", va="center")
    ax.text(54.5, 5.5, "39", fontsize=9, weight="bold", color="white", va="center")
    ax.add_patch(Rectangle((50, 25), 36, 6.5, fc="#d9d4c7", ec="#555")); ax.add_patch(Rectangle((50, 29.5), 36, 2, fc="#8b6b4a"))
    ax.text(68, 27, "nắp khóa J2 ở mép trên", ha="center", fontsize=6.5)
    ax.text(68, 33, "J2  (cáp màn vào từ cạnh trên)", ha="center", fontsize=7.5)
    ax.text(48.8, 28.5, "1", fontsize=11, weight="bold", color="yellow", va="center")
    ax.text(86.5, 28.5, "50", fontsize=9, weight="bold", color="white", va="center")
    # KD tail U-fold
    ax.add_patch(Rectangle((56, 33.5), 24, 2.2, fc="#f3e7c9", ec="#555"))          # tail lower layer -> into J2
    ax.add_patch(Rectangle((56, 31.4), 24, 2.1, fc="none", ec="none"))
    ax.add_patch(Arc((80, 36.9), 4.2, 6.4, theta1=-90, theta2=90, color="#555", lw=2.2))
    ax.add_patch(Rectangle((60, 38.2), 20, 2.2, fc="#f3e7c9", ec="#555"))          # tail upper layer from panel
    ax.add_patch(Rectangle((40, 40.4), 50, 5.5, fc="#9aa6b2", ec="#555"))
    ax.text(65, 43.2, "màn KD028 (đuôi cáp thò ra mép này)", ha="center", fontsize=7.5)
    ax.text(92, 36.5, "đuôi cáp gập chữ U\n→ tiếp điểm úp xuống\n→ đi vào J2", fontsize=7.2, va="center")
    ax.text(2, 43, "Sơ đồ minh họa, không đúng tỉ lệ.", fontsize=7, style="italic")
    ax.text(100, 14, "Kiểm tra trước khi cắm:\n\n"
            "• J01H: 3 chân GND liền nhau\n  (35-37-39) ở bên TRÁI\n  → chân 1 bên PHẢI.\n\n"
            "• Màn: ngón ngoài cùng + ngón\n  thứ 9 kêu với nhau = đầu\n  chân 50. Đầu kia = chân 1,\n"
            "  phải nằm phía số '1' của J2.",
            fontsize=7.6, va="center", ha="center",
            bbox=dict(boxstyle="round", fc="#fff8dc", ec=GOLD))


def panel_d(ax):
    ax.axis("off")
    ax.set_title("④ Danh sách kiểm tra theo thứ tự", fontsize=11, weight="bold", loc="left")
    rows = [
        ("Trước khi đặt board", "Đo mainboard: GND 35-37-39 bên trái (trang 2 PDF)."),
        ("", "Nhận màn: đo ngón thứ 9 → biết đầu chân 1 và đầu chân 50 (trang 3 PDF)."),
        ("", "Nhận dây: thấy tiếp điểm vàng ở cả hai đầu (cùng chiều)."),
        ("Khi JLC gửi ảnh duyệt", "J1: thanh đen quay về phía J2, 20 chân trên 20 pad, không pad trống."),
        ("", "J2: nắp khóa ở cạnh trên board."),
        ("Khi lắp", "THÁO PIN. Cả 3 đầu nối: tiếp điểm úp xuống, đẩy hết, đóng khóa."),
        ("", "Chân 1 của màn nằm phía số '1' in cạnh J2."),
        ("Bật máy lần đầu", "Lắp pin, bật. Màn trắng/đen trơn → tháo pin, kiểm lại chiều tiếp điểm."),
        ("", "Hình âm bản / sai màu / lật hình → bình thường, sửa bằng phần mềm."),
    ]
    y = 0.92
    for head, txt in rows:
        if head:
            ax.text(0.0, y, head, fontsize=9, weight="bold", color=BLUE, transform=ax.transAxes)
            y -= 0.075
        ax.text(0.02, y, "☐  " + txt, fontsize=8.6, transform=ax.transAxes)
        y -= 0.075


def build(png, pdf):
    fig = plt.figure(figsize=(11.7, 16.5))
    fig.suptitle("CHỐNG NGƯỢC CHÂN – TI-84 CE + màn KD028 (board v2)", fontsize=15, weight="bold", y=0.985)
    panel_a(fig.add_axes([0.04, 0.70, 0.44, 0.25]))
    panel_b(fig.add_axes([0.52, 0.70, 0.45, 0.25]))
    panel_c(fig.add_axes([0.04, 0.36, 0.92, 0.31]))
    panel_d(fig.add_axes([0.06, 0.03, 0.88, 0.30]))
    fig.savefig(png, dpi=120)
    with PdfPages(pdf) as pp:
        pp.savefig(fig)
    plt.close(fig)


if __name__ == "__main__":
    build("out/orientation-check.png", "out/orientation-check.pdf")
    print("ok")
