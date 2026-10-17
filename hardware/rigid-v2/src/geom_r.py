"""Rigid 2-layer adapter: TI-84 Plus CE LCD connector  -> store-bought FFC (39P, 0.3 mm, type B)
-> J1 = Hirose FH26W-39S-0.3SHW(60) on this board -> J2 = Hirose FH12-50S-0.5SH(55) -> KD028QVFMA027.

Coordinates in mm, top view (component side), y up. Board: x -15.6..15.6, y 0..BOARD_TOP.
  J1 sits at the BOTTOM edge, its FFC opening faces -y (the FFC comes in from below).
  J2 sits at the TOP edge, its FPC opening faces +y (the KD panel FPC comes in from above).

Pin orientation:
  FFC type B ("nguoc chieu") into a bottom-contact J1 with opening -y  ->  CE pin 1 on the LEFT.
  (invariant det[tip, contact normal, pin-1 side] = +1 at the CE end; type B keeps it at the other end)
  CE pin c lands on J1 contact position c counted from the left: x = J1X - 5.7 + 0.3 (c - 1).
  FH26 footprint: odd positions = front row (FPC side, pads 0.3 x 0.8), even = rear row (0.3 x 0.65).
  KD pin m on J2: x = (25.5 - m) * 0.5  (KD1 right, KD50 left; same as the verified flex v2).
"""
from dataclasses import dataclass, field

# ------------------------------------------------------------------ pinouts (same as flex v2)
CE = {1: "GND", 2: "TE", 3: "RESET", 4: "DB17", 5: "DB16", 6: "DB15", 7: "DB14", 8: "DB13",
      9: "DB12", 10: "DB11", 11: "DB10", 12: "DB9", 13: "DB8", 14: "DB7", 15: "DB6", 16: "DB5",
      17: "DB4", 18: "DB3", 19: "DB2", 20: "DB1", 21: "DB0", 22: "SDO", 23: "SDI", 24: "SCL",
      25: "CS", 26: "IOVCC", 27: "VCC", 28: "LED_A", 29: "LED_K1", 30: "LED_K2", 31: "LED_K3",
      32: "LED_K4", 33: "VSYNC", 34: "HSYNC", 35: "GND", 36: "DCLK", 37: "GND", 38: "ENABLE",
      39: "GND"}
KD = {1: "GND", 2: "XR(NC)", 3: "YD(NC)", 4: "XL(NC)", 5: "YU(NC)", 6: "IOVCC", 7: "IOVCC",
      8: "VCI", 9: "VCI", 10: "IM2", 11: "IM1", 12: "IM0", 13: "RESET", 14: "CS",
      15: "RS(SPI-SCL)", 16: "WR(SPI-RS)", 17: "RD", 18: "VSYNC", 19: "HSYNC", 20: "ENABLE",
      21: "DOTCLK", 22: "SDA", 41: "SDO", 42: "GND", 43: "LEDA", 44: "LEDK1", 45: "LEDK2",
      46: "LEDK3", 47: "LEDK4", 48: "LEDK5", 49: "LEDK6", 50: "GND"}
for k in range(18):
    KD[23 + k] = f"DB{k}"

NETS = {
    "GND":   ([1, 35, 37, 39], [1, 11, 16, 42, 50]),      # KD11 = IM1 (0), KD16 = WR (fixed low)
    "TE":    ([2], []),                                   # 100k pull-down R1, panel has no TE pin
    "RESET": ([3], [13]),
    "SDO":   ([22], [41]),
    "SDI":   ([23], [22]),
    "SCL":   ([24], [15]),
    "CS":    ([25], [14]),
    "IOVCC": ([26], [6, 7, 10, 12, 17]),                  # KD10 IM2=1, KD12 IM0=1, KD17 RD=1
    "VCC":   ([27], [8, 9]),
    "LEDA":  ([28], [43]),
    "LEDK":  ([29, 30, 31, 32], [44, 45, 46, 47, 48, 49]),
    "VSYNC": ([33], [18]),
    "HSYNC": ([34], [19]),
    "DCLK":  ([36], [21]),
    "EN":    ([38], [20]),
}
for k in range(18):
    NETS[f"DB{k}"] = ([21 - k], [23 + k])
NC_KD = [2, 3, 4, 5]


def ce_net(n):
    for name, (ce, _) in NETS.items():
        if n in ce:
            return name
    raise KeyError(n)


def kd_net(m):
    for name, (_, kd) in NETS.items():
        if m in kd:
            return name
    return None


# ------------------------------------------------------------------ geometry constants
X0, X1 = -15.6, 15.6            # board left/right edge
TR = 0.15                       # signal trace
TRP = 0.20                      # power / LED trace (where there is room)
VIA_D, VIA_DRILL = 0.50, 0.30
# J1 (FH26-39S, KiCad footprint rotated +90 deg: FPC side -> -y)
J1X, J1Y = 2.0, 3.65
J1_FRONT_Y = J1Y - 1.40         # odd pads, 0.3 x 0.8
J1_REAR_Y = J1Y + 1.475         # even pads, 0.3 x 0.65
J1_FRONT = (0.30, 0.80)
J1_REAR = (0.30, 0.65)
J1_MP = (0.40, 0.95)
J1_MP_DX, J1_MP_Y = 6.40, J1Y - 1.125
ROW_A, ROW_B = 1.35, 0.60       # front via rows (c = 1 mod 4 -> A, c = 3 mod 4 -> B)
Y0 = 6.50                       # fan start (both layers)
YL = 11.70                      # launch line (odd vias)
T = [12.50 + 0.65 * i for i in range(5)]   # channel tracks (bottom)
# J2 (FH12-50S, KiCad footprint rotated 180 deg: FPC side -> +y)
KD_PITCH = 0.50
J2P = 16.40                     # J2 pad row centre
J2_PAD = (0.30, 1.30)
YZ = J2P + 1.85                 # J2 footprint origin
J2_MP = (1.80, 2.20)
J2_MP_X, J2_MP_Y = 14.15, YZ + 1.40
STRAP = J2P - 0.95              # straps under the pad row (VCC, IOVCC, LEDK)
YSV = J2P - 1.10                # vias just below the pad row (sync group -> band)
B = [J2P + 1.05 + 0.65 * i for i in range(4)]   # band tracks under the J2 body (bottom)
GBUS = J2P + 3.65               # GND bus under the J2 body (top)
BOARD_TOP = YZ + 4.40 + 0.05    # J2 body front + 0.05
# passives
R1_XY = (-6.30, 5.70)           # horizontal, pad1 (TE) at +x side
C2_XY = (14.40, 11.40)          # vertical, pad1 (VCC) at top
C1_XY = (14.40, 13.90)          # vertical, pad1 (IOVCC) at bottom
C_PAD = (0.62, 0.56)            # 0402 pad rotated 90 deg (w, h)
C_OFF = 0.48
R_PAD = (0.54, 0.64)
R_OFF = 0.51


# The layout below is drawn for the UNMIRRORED frame and mirrored (x -> -x) at the end of build().
# Reason (re-check of the KD028 drawing, 2026-10-11): the KD FPC end has det = -1, so on a
# bottom-contact J2 (opening +y) KD pin 1 is on the LEFT.  Mirroring the whole board puts KD1 left
# and CE1 right; CE1 right at a bottom-contact J1 with opening -y needs a TYPE A (cung chieu) FFC.
MIRROR = True
SG = -1.0 if MIRROR else 1.0
J1C = SG * J1X                  # J1 centre x on the real board


def _xce(c):
    return J1X - 5.7 + 0.3 * (c - 1)


def x_ce(c):
    return SG * _xce(c)


def y_ce(c):
    return J1_FRONT_Y if c % 2 else J1_REAR_Y


def _xkd(m):
    return (25.5 - m) * KD_PITCH


def x_kd(m):
    return SG * _xkd(m)


@dataclass
class Design:
    tracks: list = field(default_factory=list)     # (layer, net, pts, width)
    vias: list = field(default_factory=list)       # (net, x, y)
    pads: list = field(default_factory=list)       # (layer, net, x, y, w, h, kind)
    comps: list = field(default_factory=list)      # (ref, value, lcsc, x, y, rot, footprint)
    silk_top: list = field(default_factory=list)   # (text, x, y, size, rot)
    silk_bot: list = field(default_factory=list)
    silk_lines_top: list = field(default_factory=list)
    outline: list = field(default_factory=list)
    keepout_pour: list = field(default_factory=list)   # (layer, shapely-geom-args)

    def t(self, layer, net, pts, w=TR):
        self.tracks.append((layer, net, [tuple(p) for p in pts], w))

    def via(self, net, x, y):
        self.vias.append((net, x, y))

    def pad(self, layer, net, x, y, w, h, kind="smd"):
        self.pads.append((layer, net, x, y, w, h, kind))


def fan(xa, ya, xb, yb, y0=Y0):
    """vertical from (xa, ya) to y0, 45 deg diagonal to x = xb, vertical to yb."""
    s = abs(xb - xa)
    pts = [(xa, ya)]
    if abs(y0 - ya) > 1e-9:
        pts.append((xa, y0))
    if s > 1e-9:
        pts.append((xb, y0 + s))
    pts.append((xb, yb))
    return pts


def build():
    d = Design()
    d.outline = [(X0, 0.0), (X1, 0.0), (X1, BOARD_TOP), (X0, BOARD_TOP)]

    # ---------------- J1 pads
    for c in range(1, 40):
        w, h = J1_FRONT if c % 2 else J1_REAR
        d.pad("T", ce_net(c), _xce(c), y_ce(c), w, h)
    for sx in (-1, 1):
        d.pad("T", "GND", J1X + sx * J1_MP_DX, J1_MP_Y, *J1_MP)
    d.comps.append(("J1", "FH26W-39S-0.3SHW(60)", "C92280", J1X, J1Y, 0, "Hirose_FH26-39S-0.3SHW"))

    # ---------------- J2 pads
    for m in range(1, 51):
        d.pad("T", kd_net(m) or f"NC{m}", _xkd(m), J2P, *J2_PAD)
    for sx in (-1, 1):
        d.pad("T", "GND", sx * J2_MP_X, J2_MP_Y, *J2_MP)
    d.comps.append(("J2", "FH12-50S-0.5SH(55)", "C202116", 0.0, YZ, 180, "Hirose_FH12-50S-0.5SH"))

    # ---------------- front stubs + vias for the odd (front row) pads
    def front_via(c, net=None):
        net = net or ce_net(c)
        y = ROW_A if c % 4 == 1 else ROW_B
        d.t("T", net, [(_xce(c), y_ce(c)), (_xce(c), y)])
        d.via(net, _xce(c), y)
        return y

    # GND front pads 1, 35, 37, 39 -> GND vias
    for c in (1, 35, 37, 39):
        front_via(c)

    # ---------------- data bus DB17..DB0 (CE 4..21) -> KD 40..23, straight fan
    for c in range(4, 22):
        net = ce_net(c)
        xb = _xkd(44 - c)
        if c % 2 == 0:      # rear pad, top layer all the way
            d.t("T", net, fan(_xce(c), y_ce(c), xb, J2P))
        else:               # front pad -> via -> bottom fan -> via at YL -> top to J2
            y = front_via(c)
            d.t("B", net, fan(_xce(c), y, xb, YL))
            d.via(net, xb, YL)
            d.t("T", net, [(xb, YL), (xb, J2P)])

    # ---------------- RESET (CE3, front) -> bottom, left side, channel track T0 -> KD13
    y = front_via(3)
    xr = -8.0
    d.t("B", "RESET", fan(_xce(3), y, xr, T[0]) + [(_xkd(13), T[0])])
    d.via("RESET", _xkd(13), T[0])
    d.t("T", "RESET", [(_xkd(13), T[0]), (_xkd(13), J2P)])

    # ---------------- TE (CE2, rear) -> R1 (100k to GND)
    r1x, r1y = R1_XY
    d.t("T", "TE", [(_xce(2), y_ce(2)), (_xce(2), r1y), (r1x + R_OFF, r1y)])
    d.pad("T", "TE", r1x + R_OFF, r1y, *R_PAD)
    d.pad("T", "GND", r1x - R_OFF, r1y, *R_PAD)
    d.t("T", "GND", [(r1x - R_OFF, r1y), (r1x - R_OFF - 0.75, r1y)], TRP)
    d.via("GND", r1x - R_OFF - 0.75, r1y)
    d.comps.append(("R1", "100k 0402", "C25741", r1x, r1y, 180, "R_0402"))

    # ---------------- SDI (CE23, front) -> KD22, straight; via staggered below YL
    y = front_via(23)
    xs = _xkd(22)
    d.t("B", "SDI", fan(_xce(23), y, xs, YL - 0.7))
    d.via("SDI", xs, YL - 0.7)
    d.t("T", "SDI", [(xs, YL - 0.7), (xs, J2P)])

    # ---------------- CS (CE25, front) -> KD14, straight
    y = front_via(25)
    xs = _xkd(14)
    d.t("B", "CS", fan(_xce(25), y, xs, YL))
    d.via("CS", xs, YL)
    d.t("T", "CS", [(xs, YL), (xs, J2P)])

    # ---------------- SDO (CE22, rear) -> track T1 -> KD41 (left)
    xl, xd = 2.25, _xkd(41)
    d.t("T", "SDO", fan(_xce(22), y_ce(22), xl, T[1]))
    d.via("SDO", xl, T[1])
    d.t("B", "SDO", [(xl, T[1]), (xd, T[1])])
    d.via("SDO", xd, T[1])
    d.t("T", "SDO", [(xd, T[1]), (xd, J2P)])

    # ---------------- SCL (CE24, rear) -> track T4 -> KD15
    xl, xd = 2.75, _xkd(15)
    d.t("T", "SCL", fan(_xce(24), y_ce(24), xl, T[4]))
    d.via("SCL", xl, T[4])
    d.t("B", "SCL", [(xl, T[4]), (xd, T[4])])
    d.via("SCL", xd, T[4])
    d.t("T", "SCL", [(xd, T[4]), (xd, J2P)])

    # ---------------- IOVCC (CE26, rear) -> track T1 -> KD17, 12, 10, 7/6 + C1
    xl = 3.25
    d.t("T", "IOVCC", fan(_xce(26), y_ce(26), xl, T[1]), TR)
    d.via("IOVCC", xl, T[1])
    c1x, c1y = C1_XY
    xc1v = 13.30
    d.t("B", "IOVCC", [(xl, T[1]), (xc1v, T[1])], TRP)
    for m in (17, 12, 10):
        d.via("IOVCC", _xkd(m), T[1])
        d.t("T", "IOVCC", [(_xkd(m), T[1]), (_xkd(m), J2P)])
    xm = (_xkd(6) + _xkd(7)) / 2
    d.via("IOVCC", xm, T[1])
    d.t("T", "IOVCC", [(xm, T[1]), (xm, STRAP)], TRP)
    d.t("T", "IOVCC", [(_xkd(7), J2P), (_xkd(7), STRAP), (_xkd(6), STRAP), (_xkd(6), J2P)])
    d.via("IOVCC", xc1v, T[1])
    d.t("T", "IOVCC", [(xc1v, T[1]), (c1x, T[1]), (c1x, c1y - C_OFF)], TRP)
    d.pad("T", "IOVCC", c1x, c1y - C_OFF, *C_PAD)
    d.pad("T", "GND", c1x, c1y + C_OFF, *C_PAD)
    d.comps.append(("C1", "100nF 16V X7R 0402", "C1525", c1x, c1y, 90, "C_0402"))

    # ---------------- VCC (CE27, front) -> bottom fan to x=8.5 -> T0 -> KD8/9 + C2
    y = front_via(27)
    xv = (_xkd(8) + _xkd(9)) / 2
    c2x, c2y = C2_XY
    xc2v = 13.80
    d.t("B", "VCC", fan(_xce(27), y, xv, T[0]), TR)
    d.t("B", "VCC", [(xv, T[0]), (xc2v, T[0])], TRP)
    d.via("VCC", xv, T[0])
    d.t("T", "VCC", [(xv, T[0]), (xv, STRAP)], TRP)
    d.t("T", "VCC", [(_xkd(9), J2P), (_xkd(9), STRAP), (_xkd(8), STRAP), (_xkd(8), J2P)])
    d.via("VCC", xc2v, T[0])
    d.t("T", "VCC", [(xc2v, T[0]), (c2x, c2y + C_OFF)], TRP)
    d.pad("T", "VCC", c2x, c2y + C_OFF, *C_PAD)
    d.pad("T", "GND", c2x, c2y - C_OFF, *C_PAD)
    d.comps.append(("C2", "100nF 16V X7R 0402", "C1525", c2x, c2y, 270, "C_0402"))

    # ---------------- LEDA (CE28, rear) -> track T2 -> KD43
    xl, xd = 3.75, _xkd(43)
    d.t("T", "LEDA", fan(_xce(28), y_ce(28), xl, T[2]))
    d.via("LEDA", xl, T[2])
    d.t("B", "LEDA", [(xl, T[2]), (xd, T[2])], TRP)
    d.via("LEDA", xd, T[2])
    d.t("T", "LEDA", [(xd, T[2]), (xd, J2P)])

    # ---------------- LEDK: K1/K3 front strap -> via -> bottom -> merge via behind J1 with K2/K4
    xk1, xk3 = _xce(29), _xce(31)
    yk = 1.45
    d.t("T", "LEDK", [(xk1, y_ce(29)), (xk1, yk), (xk3, yk)])
    y = front_via(31)
    ym = J1_REAR_Y + 0.325 + 0.40     # merge via behind the rear row
    d.t("B", "LEDK", [(xk3, y), (xk3, ym)], TR)
    d.via("LEDK", xk3, ym)
    for c in (30, 32):
        d.t("T", "LEDK", [(_xce(c), y_ce(c)), (_xce(c), ym), (xk3, ym)])
    xl, xd = 4.75, -10.5
    d.t("T", "LEDK", fan(xk3, ym, xl, T[3]))
    d.via("LEDK", xl, T[3])
    d.t("B", "LEDK", [(xl, T[3]), (xd, T[3])], TRP)
    d.via("LEDK", xd, T[3])
    d.t("T", "LEDK", [(xd, T[3]), (xd, STRAP)], TRP)
    d.t("T", "LEDK", [(_xkd(49), STRAP), (_xkd(44), STRAP)], TRP)
    for m in range(44, 50):
        d.t("T", "LEDK", [(_xkd(m), STRAP), (_xkd(m), J2P)])

    # ---------------- sync group -> vias below the J2 pads -> band under the J2 body (bottom)
    # VSYNC (CE33, front) -> bottom fan -> via at YL -> top -> via YSV -> band B0 -> KD18
    y = front_via(33)
    xl = 10.25
    d.t("B", "VSYNC", fan(_xce(33), y, xl, YL))
    d.via("VSYNC", xl, YL)
    d.t("T", "VSYNC", [(xl, YL), (xl, YSV)])
    band = [("VSYNC", xl, _xkd(18), B[0])]
    for c, net, xl, m, yb in ((34, "HSYNC", 10.90, 19, B[1]), (36, "DCLK", 11.55, 21, B[2]),
                              (38, "EN", 12.20, 20, B[3])):
        d.t("T", net, fan(_xce(c), y_ce(c), xl, YSV))
        band.append((net, xl, _xkd(m), yb))
    for net, xl, xd, yb in band:
        d.via(net, xl, YSV)
        d.t("B", net, [(xl, YSV), (xl, yb), (xd, yb)])
        d.via(net, xd, yb)
        d.t("T", net, [(xd, yb), (xd, J2P)])

    # ---------------- GND: KD GND pads up to a bus under the J2 body, bus into the MP pads
    for m in (1, 11, 16, 42, 50):
        d.t("T", "GND", [(_xkd(m), J2P), (_xkd(m), GBUS)])
    d.t("T", "GND", [(-J2_MP_X, GBUS), (J2_MP_X, GBUS)], 0.30)
    for sx in (-1, 1):
        gx = sx * J2_MP_X
        d.t("T", "GND", [(gx, J2_MP_Y), (gx, J2_MP_Y - J2_MP[1] / 2 - 0.55)], 0.30)
        d.via("GND", gx, J2_MP_Y - J2_MP[1] / 2 - 0.55)
        d.via("GND", gx + sx * 0.0, J2_MP_Y + J2_MP[1] / 2 + 0.55)
        d.t("T", "GND", [(gx, J2_MP_Y), (gx, J2_MP_Y + J2_MP[1] / 2 + 0.55)], 0.30)
    # C1 / C2 GND pads -> vias
    d.t("T", "GND", [(c1x, c1y + C_OFF), (c1x, c1y + C_OFF + 0.65)], TRP)
    d.via("GND", c1x, c1y + C_OFF + 0.65)
    d.t("T", "GND", [(c2x, c2y - C_OFF), (c2x, c2y - C_OFF - 0.65)], TRP)
    d.via("GND", c2x, c2y - C_OFF - 0.65)
    # J1 metal fittings -> GND vias outside the connector
    for sx in (-1, 1):
        gx = J1X + sx * J1_MP_DX
        d.t("T", "GND", [(gx, J1_MP_Y), (gx + sx * 0.75, J1_MP_Y)], TRP)
        d.via("GND", gx + sx * 0.75, J1_MP_Y)

    # ---------------- silkscreen
    st = d.silk_top
    st.append(("J1", J1X + 7.9, J1Y + 1.4, 0.8, 0))
    st.append(("1", _xce(1) - 0.85, 0.75, 0.7, 0))
    st.append(("39", _xce(39) + 1.55, 0.75, 0.7, 0))
    st.append(("J2", -13.9, J2P - 2.4, 0.8, 0))
    st.append(("1", 13.05, J2P - 0.95, 0.6, 0))
    st.append(("50", -13.05, J2P - 0.95, 0.6, 0))
    st.append(("R1", r1x, r1y + 0.9, 0.6, 0))
    st.append(("C1", c1x - 0.95, c1y, 0.6, 90))
    st.append(("C2", c2x - 0.95, c2y, 0.6, 90))
    st.append(("FFC 39P 0.3mm", -10.4, 2.45, 0.75, 0))
    st.append(("CUNG CHIEU (A)", -10.4, 1.25, 0.75, 0))
    st.append(("TI84CE-KD028 v2", -10.4, 8.6, 0.75, 0))
    sb = d.silk_bot
    sb.append(("JLCJLCJLCJLC", 0.0, 4.4, 0.8, 0))
    sb.append(("TI-84 Plus CE -> KD028QVFMA027", 0.0, 21.0, 0.8, 0))
    sb.append(("FFC 39P 0.3mm CUNG CHIEU", -9.4, 8.0, 0.65, 0))
    sb.append(("tiep diem up xuong board", -9.4, 7.0, 0.65, 0))
    if MIRROR:
        mirror(d)
    return d


def mirror(d):
    d.tracks = [(L, n, [(-x, y) for x, y in pts], w) for L, n, pts, w in d.tracks]
    d.vias = [(n, -x, y) for n, x, y in d.vias]
    d.pads = [(L, n, -x, y, w, h, k) for L, n, x, y, w, h, k in d.pads]
    d.comps = [(r, v, l, -x, y, rot, fp) for r, v, l, x, y, rot, fp in d.comps]
    d.silk_top = [(s, -x, y, sz, rot) for s, x, y, sz, rot in d.silk_top]
    d.silk_bot = [(s, -x, y, sz, rot) for s, x, y, sz, rot in d.silk_bot]


if __name__ == "__main__":
    d = build()
    print(len(d.tracks), "tracks", len(d.vias), "vias", len(d.pads), "pads")
