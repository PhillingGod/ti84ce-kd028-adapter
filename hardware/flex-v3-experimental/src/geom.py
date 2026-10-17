"""Adapter flex v3: TI-84 Plus CE LCD connector (Hirose FH26, 39p 0.3 mm, bottom contact)
-> Hirose FH12-50S-0.5SH(55) ZIF for the Startek/Kedake KD028QVFMA027 panel (50p 0.5 mm).

Coordinates in mm, seen from the TOP side (F_Cu).
  y = 0 is the tip of the CE tail, the board grows towards +y, x = 0 is the tail centre line.
  Gold fingers for the CE connector are on the TOP copper (F_Cu).
  v3: the ZIF J2 and the passives sit on the BOTTOM side (B_Cu); J2's FPC opening faces +y.
  Reason: the KD FPC end has det = -1 (re-check of the KD028 drawing).  A bottom-contact J2 on the
  BOTTOM side with opening +y needs KD pin 1 at +x in top-view coordinates - exactly the v2 pad
  mapping, so the v2 routing is kept and every J2 net drops through a staggered via band to B_Cu.

Pin orientation (derived from the two datasheets, see README):
  CE tail, seen from the TOP (= gold-finger) side, tip down: CE pin 1 at x = -5.7 (left), pin 39 right.
  Seen from the outer (bottom) side, tip down: pin 1 RIGHT - same as the original GPM1421C0 cable
  seen from the back of the calculator (printed 'GPM1421C0' face, photo of the SG92A board).
  KD panel pins on J2, seen from the TOP: KD pin 1 at x = +12.25 (right), pin 50 at x = -12.25 (left)
"""
from dataclasses import dataclass, field

# ------------------------------------------------------------------ pinouts
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

# net name -> (CE pins, KD pins)
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
CE_PITCH = 0.30
FINGER_W = 0.16
FINGER_Y0, FINGER_Y1 = 0.25, 2.90
COVERLAY_TAIL_Y = 2.50          # bottom coverlay starts here (Hirose FH26 / GPM1421C0: 2.5)
TAIL_W = 12.0
PI_STIFF_Y1 = 4.5               # PI stiffener on TOP of the tail (>= 3.5 mm, Hirose)
TRACE = 0.12
NECK_W = 14.0
YN = 45.0                       # end of neck
YZ0 = 67.0                      # v2 J2 origin: the routing below is referenced to it
VROWS = (64.10, 64.65, 65.20)   # v3 via band (top -> bottom), rows used cyclically per column
VROW_FEED = 64.10               # via row for the strap feeds
STRAP_B = 65.50                 # straps on the bottom, just below the pad row
J2_PAD_Y = 66.40                # v3 pad row (bottom side)
YZ = J2_PAD_Y + 1.85            # J2 footprint origin (y)
KD_PITCH = 0.50
VIA_D, VIA_DRILL = 0.55, 0.30
J2_PAD = (0.30, 1.30)
J2_MP = (1.80, 2.20)
J2_MP_X, J2_MP_Y = 14.15, YZ + 1.40
PAD_BOT = J2_PAD_Y - J2_PAD[1] / 2
STRAP_Y = YZ0 - 3.0             # v2 strap height (top feeds end below the via band)
BUS_Y = YZ - 0.6                # GND bus under the J2 body (bottom copper)
C_R = YN + 11.0                 # RESET channel
C0 = YN + 11.6                  # first right-group channel
CH_PITCH = 0.6
YV1, YV2 = YN + 9.5, YN + 10.3  # data via rows
FAN_Y0, FAN_Y1 = YN + 5.0, YN + 9.0
GND_VIA_Y = YN + 5.4
R0 = 11.0                       # first riser x
R_PITCH = 0.6
BOARD_TOP = YZ + 7.0
PI_STIFF_T = 0.15                # JLC PI calculator: 2-layer 0.11 mm FPC, 0.20 mm at the fingers
FR4_T = 0.4
FR4_Y0 = YN - 0.5                # FR4 stiffener (top side) covers the head from here up


def x_ce(n):
    return (n - 20) * CE_PITCH


def x_kd(m):
    return (25.5 - m) * KD_PITCH


@dataclass
class Design:
    tracks: list = field(default_factory=list)     # (layer, net, pts, width)
    vias: list = field(default_factory=list)       # (net, x, y)
    pads: list = field(default_factory=list)       # (layer, net, x, y, w, h, kind)  kind: finger/smd
    comps: list = field(default_factory=list)      # (ref, value, lcsc, x, y, rot, footprint)
    silk_top: list = field(default_factory=list)   # (text, x, y, size, rot)
    silk_bot: list = field(default_factory=list)
    silk_lines_top: list = field(default_factory=list)  # (pts, width)
    silk_lines_bot: list = field(default_factory=list)
    comp_side: dict = field(default_factory=dict)        # ref -> "Top" / "Bottom"
    outline: list = field(default_factory=list)

    def t(self, layer, net, pts, w=TRACE):
        self.tracks.append((layer, net, [tuple(p) for p in pts], w))

    def via(self, net, x, y):
        self.vias.append((net, x, y))

    def pad(self, layer, net, x, y, w, h, kind="smd"):
        self.pads.append((layer, net, x, y, w, h, kind))


def board_outline():
    return [(-6.0, 0.0), (6.0, 0.0), (6.0, 4.5), (7.0, 5.5), (7.0, YN - 4.0),
            (20.2, YN - 0.5), (20.2, YZ0 - 3.0), (16.0, YZ0 - 3.0), (16.0, BOARD_TOP),
            (-16.0, BOARD_TOP), (-16.0, YZ0 - 4.5), (-12.5, YZ0 - 4.5), (-12.5, YN - 0.5),
            (-7.0, YN - 3.0), (-7.0, 5.5), (-6.0, 4.5)]


def vrow(x):
    """via row for a J2 column: 3-row stagger so neighbouring columns (0.5 mm) never share a row."""
    k = round((x - x_kd(50)) / KD_PITCH)
    assert abs(x_kd(50) + k * KD_PITCH - x) < 1e-6, x
    return VROWS[k % 3]


def build():
    d = Design()
    d.outline = board_outline()
    B, T = "B", "T"

    # ---------------- CE gold fingers (TOP) + start of every trace (all CE-side routing on TOP)
    for n in range(1, 40):
        x = x_ce(n)
        d.pad(T, ce_net(n), x, (FINGER_Y0 + FINGER_Y1) / 2, FINGER_W, FINGER_Y1 - FINGER_Y0, "finger")

    def ce_trace(n, pts, w=TRACE):
        d.t(T, ce_net(n), [(x_ce(n), FINGER_Y1 - 0.3)] + pts, w)

    def drop(net, x):
        """v3: top trace ends at the via band; via; bottom stub up into the J2 pad (B_Cu)."""
        y = vrow(x)
        d.via(net, x, y)
        d.t(B, net, [(x, y), (x, PAD_BOT + 0.3)])

    # ---------------- left group: GND1, TE, RESET
    ce_trace(1, [(x_ce(1), YN + 0.5), (-9.6, YN + 0.5), (-9.6, YN + 1.6)])
    d.via("GND", -9.6, YN + 1.6)
    r1x, r1y = -10.9, YN + 2.4
    ce_trace(2, [(x_ce(2), YN + 0.8), (-9.0, YN + 0.8), (-9.0, r1y)])
    d.via("TE", -9.0, r1y)
    d.t(B, "TE", [(-9.0, r1y), (r1x + 0.51, r1y)])
    d.pad(B, "TE", r1x + 0.51, r1y, 0.54, 0.64)          # KiCad R_0402: pads 0.54 x 0.64 at +-0.51
    d.pad(B, "GND", r1x - 0.51, r1y, 0.54, 0.64)
    d.comps.append(("R1", "100k 0402", "C25741", r1x, r1y, 0, "R_0402"))
    ce_trace(3, [(x_ce(3), YN + 1.1), (-8.4, YN + 1.1), (-8.4, C_R)])
    d.via("RESET", -8.4, C_R)
    d.t(B, "RESET", [(-8.4, C_R), (x_kd(13), C_R)])
    d.via("RESET", x_kd(13), C_R)
    d.t(T, "RESET", [(x_kd(13), C_R), (x_kd(13), vrow(x_kd(13)))])
    drop("RESET", x_kd(13))

    # ---------------- data bus DB0..DB17: entirely on TOP, straight fan to the J2 pads
    for k in range(18):
        n = 21 - k
        x0, x1 = x_ce(n), x_kd(23 + k)
        ce_trace(n, [(x0, FAN_Y0), (x1, FAN_Y1), (x1, vrow(x1))])
        drop(ce_net(n), x1)

    # ---------------- right group: staircase + risers on TOP, channels on BOTTOM
    yk = YN - 1.0
    for n in (29, 30, 31, 32):
        ce_trace(n, [(x_ce(n), yk)])
    d.t(T, "LEDK", [(x_ce(29), yk), (x_ce(32), yk)], TRACE)
    xk = (x_ce(29) + x_ce(32)) / 2

    order = ["SDO", "SDI", "SCL", "CS", "IOVCC", "VCC", "LEDA", "LEDK", "VSYNC", "HSYNC",
             "GND35", "DCLK", "GND37", "EN", "GND39"]
    neck_x = {"SDO": x_ce(22), "SDI": x_ce(23), "SCL": x_ce(24), "CS": x_ce(25),
              "IOVCC": x_ce(26), "VCC": x_ce(27), "LEDA": x_ce(28), "LEDK": xk,
              "VSYNC": x_ce(33), "HSYNC": x_ce(34), "GND35": x_ce(35), "DCLK": x_ce(36),
              "GND37": x_ce(37), "EN": x_ce(38), "GND39": x_ce(39)}
    ce_pin = {"SDO": 22, "SDI": 23, "SCL": 24, "CS": 25, "IOVCC": 26, "VCC": 27, "LEDA": 28,
              "VSYNC": 33, "HSYNC": 34, "GND35": 35, "DCLK": 36, "GND37": 37, "EN": 38, "GND39": 39}
    chans = ["SDO", "SDI", "SCL", "CS", "IOVCC", "VCC", "LEDA", "LEDK", "VSYNC", "HSYNC", "DCLK", "EN"]
    dests = {"SDO": [x_kd(41)], "SDI": [x_kd(22)], "SCL": [x_kd(15)], "CS": [x_kd(14)],
             "IOVCC": [(x_kd(6) + x_kd(7)) / 2, x_kd(10), x_kd(12), x_kd(17)],
             "VCC": [(x_kd(8) + x_kd(9)) / 2], "LEDA": [x_kd(43)],
             "LEDK": [(x_kd(46) + x_kd(47)) / 2],
             "VSYNC": [x_kd(18)], "HSYNC": [x_kd(19)], "DCLK": [x_kd(21)], "EN": [x_kd(20)]}
    strap_feeds = (dests["IOVCC"][0], dests["VCC"][0], dests["LEDK"][0])
    riser_x = {}
    for i, name in enumerate(order):
        net = "GND" if name.startswith("GND") else name
        yt = YN + 0.5 + 0.3 * (len(order) - 1 - i)
        xr = R0 + R_PITCH * i
        riser_x[name] = xr
        w = TRACE                     # v3: 0.12 (0.15 came within 0.145 of the next gold finger)
        top = GND_VIA_Y if name.startswith("GND") else C0 + CH_PITCH * chans.index(name)
        pts = [(neck_x[name], yt), (xr, yt), (xr, top)]
        if name.startswith("GND"):
            ce_trace(ce_pin[name], pts)
            d.via("GND", xr, top)
            continue
        if name == "LEDK":
            d.t(T, "LEDK", [(xk, yk)] + pts, w)
        else:
            ce_trace(ce_pin[name], pts, w)
        d.via(net, xr, top)                                   # riser (top) -> channel (bottom)
        xs = dests[name]
        d.t(B, net, [(xr, top), (min(xs), top)], w)
        for xd in xs:
            d.via(net, xd, top)                               # channel (bottom) -> drop (top)
            if xd in strap_feeds:
                d.t(T, net, [(xd, top), (xd, VROW_FEED)], w)
            else:
                d.t(T, net, [(xd, top), (xd, vrow(xd))], w)
                drop(net, xd)

    # ---------------- straps just below the pad row (v3: bottom), fed through one via each
    def strap(net, pins, w=0.20):
        xs = [x_kd(p) for p in pins]
        xf = (x_kd(pins[len(pins) // 2 - 1]) + x_kd(pins[len(pins) // 2])) / 2
        assert any(abs(xf - f) < 1e-6 for f in strap_feeds), (net, xf)
        d.via(net, xf, VROW_FEED)
        d.t(B, net, [(xf, VROW_FEED), (xf, STRAP_B)], w)
        d.t(B, net, [(min(xs), STRAP_B), (max(xs), STRAP_B)], w)
        for x in xs:
            d.t(B, net, [(x, STRAP_B), (x, PAD_BOT + 0.3)], TRACE)

    strap("IOVCC", [6, 7])
    strap("VCC", [8, 9])
    strap("LEDK", [44, 45, 46, 47, 48, 49])

    # ---------------- decoupling caps (top, vertical): fed by extending the bottom channels
    cI = C0 + CH_PITCH * chans.index("IOVCC")
    cV = C0 + CH_PITCH * chans.index("VCC")
    # C1 (IOVCC): bottom extension to the right edge, down to y=YN+9.6, up through a via;
    # its GND pad is tied with a short top trace to the GND39 riser via.
    c1x, c1v = 19.5, YN + 9.6
    c1c = c1v - 1.3                                       # KiCad C_0402 (90 deg): 0.62 x 0.56 at +-0.48
    d.t(B, "IOVCC", [(riser_x["IOVCC"], cI), (c1x, cI), (c1x, c1c + 0.48)])
    d.pad(B, "IOVCC", c1x, c1c + 0.48, 0.62, 0.56)
    d.pad(B, "GND", c1x, c1c - 0.48, 0.62, 0.56)
    d.t(B, "GND", [(c1x, c1c - 0.48), (c1x, GND_VIA_Y + 0.6), (riser_x["GND39"], GND_VIA_Y)], 0.20)
    d.comps.append(("C1", "100nF 16V X7R 0402", "C1525", c1x, c1v - 1.3, 90, "C_0402"))
    c1y = c1v - 1.3
    # C2 (VCC): bottom extension to the left, via, cap above it
    c2x = -11.6
    c2c = cV + 1.3
    d.t(B, "VCC", [(dests["VCC"][0], cV), (c2x, cV), (c2x, c2c - 0.48)])
    d.pad(B, "VCC", c2x, c2c - 0.48, 0.62, 0.56)
    d.pad(B, "GND", c2x, c2c + 0.48, 0.62, 0.56)
    d.t(B, "GND", [(c2x, c2c + 0.48), (c2x, cV + 2.6)], 0.20)
    d.via("GND", c2x, cV + 2.6)
    d.comps.append(("C2", "100nF 16V X7R 0402", "C1525", c2x, cV + 1.3, 90, "C_0402"))
    c2y = cV + 1.3

    # ---------------- GND stitching vias (top pour <-> bottom pour)
    for x in (-13.0, -6.5, 0.0, 6.5, 13.0):
        d.via("GND", x, BOARD_TOP - 0.9)
    for x, y in ((-15.2, YZ0 - 2.0), (15.2, YZ0 - 2.0), (-11.6, YN + 6.0), (-11.6, YN + 9.0),
                 (8.5, YN - 1.6), (-8.5, YN - 1.2)):
        d.via("GND", x, y)

    # ---------------- J2 pads (v3: BOTTOM side)
    for m in range(1, 51):
        d.pad(B, kd_net(m) or f"NC{m}", x_kd(m), J2_PAD_Y, J2_PAD[0], J2_PAD[1])
    for sx in (-1, 1):
        d.pad(B, "GND", sx * J2_MP_X, J2_MP_Y, J2_MP[0], J2_MP[1])
    d.comps.append(("J2", "FH12-50S-0.5SH(55)", "C202116", 0.0, YZ, 180, "Hirose_FH12-50S-0.5SH"))

    # ---------------- GND bus under the J2 body (v3: bottom)
    d.t(B, "GND", [(-J2_MP_X, BUS_Y), (J2_MP_X, BUS_Y)], 0.30)
    for sx in (-1, 1):
        d.t(B, "GND", [(sx * J2_MP_X, BUS_Y), (sx * J2_MP_X, J2_MP_Y)], 0.30)
    for m in NETS["GND"][1]:
        d.t(B, "GND", [(x_kd(m), J2_PAD_Y + 0.3), (x_kd(m), BUS_Y)], 0.20)

    for ref in ("J2", "R1", "C1", "C2"):
        d.comp_side[ref] = "Bottom"

    # ---------------- silkscreen (v3: component side = BOTTOM; the top of the head is under the FR4)
    d.silk_top += [("1", x_ce(1), 3.6, 0.8, 0), ("39", x_ce(39), 3.6, 0.8, 0),
                   ("MAT TIEP XUC (up xuong mainboard)", 0.0, 4.9, 0.6, 0),
                   ("TI-84 CE <-> KD028QVFMA027  v3", 0.0, 30.0, 0.9, 90)]
    # bottom silk (text mirrored when written)
    d.silk_bot += [("1", x_ce(1), 7.2, 0.8, 0), ("39", x_ce(39), 7.2, 0.8, 0),
                   ("MAT NGOAI - nhin tu sau may: chan 1 ben PHAI", 0.0, 26.0, 0.8, 90),
                   ("1", x_kd(1) + 0.15, J2_PAD_Y - 2.55, 0.7, 0),
                   ("50", x_kd(50) - 0.15, J2_PAD_Y - 2.55, 0.7, 0),
                   ("J2", -15.0, 66.9, 0.8, 90),
                   ("R1", r1x, r1y + 0.9, 0.6, 0),
                   ("C1", c1x - 1.0, c1y, 0.6, 90),
                   ("C2", c2x + 1.0, c2y, 0.6, 90),
                   ("CAP MAN KD028 CAM TU PHIA NAY", 0.0, BOARD_TOP - 0.55, 0.6, 0),
                   ("tiep diem cap man up vao flex", 0.0, BOARD_TOP - 1.45, 0.6, 0)]
    for ax in (-9.0, 9.0):
        d.silk_lines_bot.append(([(ax, BOARD_TOP - 0.4), (ax, BOARD_TOP - 1.9)], 0.15))
        d.silk_lines_bot.append(([(ax - 0.4, BOARD_TOP - 1.5), (ax, BOARD_TOP - 1.9), (ax + 0.4, BOARD_TOP - 1.5)], 0.15))
    return d
