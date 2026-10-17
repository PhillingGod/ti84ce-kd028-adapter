"""Tiny eZ80 (ADL) interpreter for the opcodes KDFIX uses; OS calls stubbed, SPI modelled like CEmu."""
import sys

d = open(sys.argv[1] if len(sys.argv) > 1 else "AKDFIX.8xp", "rb").read()
size = d[0x48] | d[0x49] << 8
body = d[0x4A:0x4A + size]
assert body[:2] == b"\xEF\x7B", body[:2]
ORG = 0xD1A87F
MEM0 = {ORG + i: b for i, b in enumerate(body)}
mem = {}

OS = {0x02014C: "GetCSC", 0x0207C0: "PutS", 0x0207F0: "NewLine", 0x020810: "ClrScrnFull",
      0x020828: "HomeUp", 0x020848: "RunIndicOff", 0x00030C: "GetFieldSizeFromType",
      0x000310: "FindFirstCertField", 0x000314: "FindField", 0x0003B4: "Delay10ms", 0x000654: "PyReinit"}
CUR_ROW, CUR_COL = 0xD00595, 0xD00596
SPI = 0xF80000


class CPU:
    def __init__(s, keys, python=False):
        mem.clear(); mem.update(MEM0)
        s.r = dict(a=0, b=0, c=0, d=0, e=0, h=0, l=0)
        s.z = s.cy = False
        s.pc = ORG + 2
        s.sp = 0xD1A87E
        s.keys = list(keys)
        s.python = python
        s.screen = {}
        s.spi_regs = {0: 0x0B, 4: 0x02000B, 8: 0x10C, 0x10: 0}
        s.fifo_hi = 0
        s.frames = []           # (dc, byte, spi_ctrl1, spi_ctrl2)
        s.log = []
        s.push24(0xFFFFFF)      # return address -> end

    # memory
    def rd(s, a):
        if SPI <= a < SPI + 0x20:
            o = a - SPI
            if o in (0x0C, 0x0D, 0x0E):
                return 0x02 if o == 0x0C else 0   # tx fifo empty, not busy, not full
            base = o & ~3
            return (s.spi_regs.get(base, 0) >> ((o & 3) * 8)) & 0xFF
        if a == CUR_ROW:
            return s.row
        if a == CUR_COL:
            return s.col
        return mem.get(a, 0)

    def wr(s, a, v):
        v &= 0xFF
        if SPI <= a < SPI + 0x20:
            o = a - SPI
            if o == 0x18:
                s.frames.append(((s.fifo_hi & 1), v, s.spi_regs[4], s.spi_regs[8]))
                return
            if o == 0x19:
                s.fifo_hi = v
                return
            base, sh = o & ~3, (o & 3) * 8
            s.spi_regs[base] = (s.spi_regs.get(base, 0) & ~(0xFF << sh)) | (v << sh)
            return
        if a == CUR_ROW:
            s.row = v; return
        if a == CUR_COL:
            s.col = v; return
        assert ORG - 0x400 <= a < ORG + 0x2000, hex(a)
        mem[a] = v

    def rd24(s, a): return s.rd(a) | s.rd(a + 1) << 8 | s.rd(a + 2) << 16
    def wr24(s, a, v):
        for i in range(3): s.wr(a + i, v >> (8 * i))

    def push24(s, v): s.sp -= 3; s.wr24(s.sp, v)
    def pop24(s): v = s.rd24(s.sp); s.sp += 3; return v

    def rp(s, n):
        hi, lo = n
        return s.r[lo] | s.r[hi] << 8 | s.r.get(hi + "u", 0) << 16
    def setrp(s, n, v):
        hi, lo = n
        s.r[lo] = v & 0xFF; s.r[hi] = v >> 8 & 0xFF; s.r[hi + "u"] = v >> 16 & 0xFF

    def fetch(s): v = s.rd(s.pc); s.pc += 1; return v
    def imm24(s): v = s.rd24(s.pc); s.pc += 3; return v
    def rel(s): v = s.fetch(); return v - 256 if v > 127 else v

    def flags_logic(s):
        s.z = s.r["a"] == 0; s.cy = False

    def os_call(s, name):
        s.log.append(name)
        if name == "GetCSC":
            if not s.keys: raise RuntimeError("nokeys")
            s.r["a"] = s.keys.pop(0)
        elif name == "PutS":
            hl = s.rp("hl")
            while True:
                ch = s.rd(hl); hl += 1
                if ch == 0: break
                s.screen[(s.row, s.col)] = chr(ch)
                s.col += 1
                assert s.col <= 26
                if s.col == 26: s.col = 0; s.row += 1
            assert s.row <= 9, "scrolled"
            s.setrp("hl", hl)
        elif name == "NewLine":
            s.col = 0; s.row += 1
        elif name in ("ClrScrnFull",):
            s.screen = {}
        elif name == "HomeUp":
            s.row = s.col = 0
        elif name in ("FindFirstCertField", "FindField"):
            s.z = s.python
        # Delay10ms and others: clobber a only
        if name in ("Delay10ms", "PyReinit", "GetFieldSizeFromType"):
            s.r["a"] = 0x55

    def run(s, maxsteps=200000):
        s.row = s.col = 0
        for _ in range(maxsteps):
            if s.pc == 0xFFFFFF:
                return
            op = s.fetch()
            R = "bcdehl?a"
            if op == 0xCD:
                t = s.imm24()
                if t in OS: s.os_call(OS[t])
                else: s.push24(s.pc); s.pc = t
            elif op == 0xC9: s.pc = s.pop24()
            elif op in (0xC3, 0xC2):
                t = s.imm24()
                if op == 0xC3 or not s.z: s.pc = t
            elif op in (0x18, 0x20, 0x28, 0x30, 0x38):
                o = s.rel()
                cond = {0x18: True, 0x20: not s.z, 0x28: s.z, 0x30: not s.cy, 0x38: s.cy}[op]
                if cond: s.pc += o
            elif op == 0x10:
                o = s.rel(); s.r["b"] = (s.r["b"] - 1) & 0xFF
                if s.r["b"]: s.pc += o
            elif op == 0xB7: s.flags_logic()
            elif op == 0xAF: s.r["a"] = 0; s.flags_logic()
            elif op == 0xA8: s.r["a"] ^= s.r["b"]; s.flags_logic()
            elif op == 0xE6: s.r["a"] &= s.fetch(); s.flags_logic()
            elif op == 0xFE:
                n = s.fetch(); s.z = s.r["a"] == n; s.cy = s.r["a"] < n
            elif op == 0xC6:
                v = s.r["a"] + s.fetch(); s.cy = v > 255; s.r["a"] = v & 0xFF; s.z = s.r["a"] == 0
            elif op == 0x0F:
                a = s.r["a"]; s.cy = bool(a & 1); s.r["a"] = (a >> 1) | ((a & 1) << 7)
            elif op in (0x06, 0x0E, 0x16, 0x1E, 0x26, 0x2E, 0x3E):
                s.r[R[(op >> 3) & 7]] = s.fetch()
            elif op in (0x01, 0x11, 0x21): s.setrp(["bc", "de", "hl"][op >> 4], s.imm24())
            elif op == 0x32: s.wr(s.imm24(), s.r["a"])
            elif op == 0x3A: s.r["a"] = s.rd(s.imm24())
            elif op == 0x22: s.wr24(s.imm24(), s.rp("hl"))
            elif op == 0xED:
                op2 = s.fetch()
                assert op2 == 0x53, hex(op2)
                s.wr24(s.imm24(), s.rp("de"))
            elif op == 0xCB:
                op2 = s.fetch()
                bit = (op2 >> 3) & 7
                assert 0x40 <= op2 < 0x80
                reg = op2 & 7
                v = s.rd(s.rp("hl")) if reg == 6 else s.r[R[reg]]
                s.z = not (v >> bit & 1)
            elif op in (0xC5, 0xD5, 0xE5): s.push24(s.rp(["bc", "de", "hl"][(op >> 4) - 0xC]))
            elif op in (0xC1, 0xD1, 0xE1): s.setrp(["bc", "de", "hl"][(op >> 4) - 0xC], s.pop24())
            elif op == 0xF5: s.push24(s.r["a"] << 8)
            elif op == 0xF1: s.r["a"] = s.pop24() >> 8 & 0xFF
            elif op == 0x23: s.setrp("hl", s.rp("hl") + 1)
            elif op == 0x2B: s.setrp("hl", s.rp("hl") - 1)
            elif 0x40 <= op < 0x80 and op != 0x76:
                src, dst = op & 7, (op >> 3) & 7
                v = s.rd(s.rp("hl")) if src == 6 else s.r[R[src]]
                if dst == 6: s.wr(s.rp("hl"), v)
                else: s.r[R[dst]] = v
            else:
                raise SystemExit(f"unknown opcode {op:02X} at {s.pc - 1:06X}")
        raise SystemExit("did not finish")

    def text(s):
        return "\n".join("".join(s.screen.get((r, c), " ") for c in range(26)).rstrip() for r in range(10))


def frames_str(fr):
    out, cur = [], None
    for dc, b, c1, c2 in fr:
        assert c1 == 0x080001 and c2 == 0x10D, (hex(c1), hex(c2))
        if dc == 0:
            cur = [f"{b:02X}"]; out.append(cur)
        else:
            assert cur is not None, "param before command"
            cur.append(f"{b:02X}")
    return [" ".join(x) for x in out]


if __name__ == "__main__":
    K = dict(c=0x0F, k1=0x22, k2=0x1A, k3=0x12, k4=0x23, k5=0x1B, k6=0x13, k7=0x24)
    for py in (False, True):
        cpu = CPU([0, K["k1"], 0x99, K["k3"], K["k4"], K["k5"], K["k6"], K["k4"], K["k2"], K["k7"], K["c"]], python=py)
        cpu.run()
        print("python model:" if py else "non-python model:")
        for f in frames_str(cpu.frames): print("  ", f)
        print("   SPI after:", {hex(k): hex(v) for k, v in cpu.spi_regs.items()})
        print("   OS calls:", [x for x in cpu.log if x not in ("PutS", "GetCSC", "NewLine")])
    for keys in ([], [K["k3"]], [K["k5"], K["k6"]], [K["k7"]]):
        c = CPU(keys)
        try:
            c.run()
        except RuntimeError:
            pass
        print("-" * 26); print(c.text())
