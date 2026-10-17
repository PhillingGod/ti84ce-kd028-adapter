# AKDFIX

A TI-84 Plus CE program that sends display-controller settings for the
KD028QVFMA027 (ST7789V, IPS) panel over the CE's LCD SPI port.

- `AKDFIX.asm`: source (spasm-ng syntax, ADL mode).
- `AKDFIX.8xp`: built program (protected program, 974 bytes).
- `sim.py`: small eZ80 interpreter covering the opcodes the program uses. It
  stubs OS calls and models the SPI port. It prints every frame sent, for
  normal and Python-edition calculators, and checks that the TI-OS SPI
  settings are restored.

```sh
spasm -E -A AKDFIX.asm AKDFIX.8xp
python3 sim.py AKDFIX.8xp
```

## Behaviour

On start (blind-safe):
1. SLPOUT, then a 120 ms wait.
2. DISPON.
3. B7 70, BB 21, C2 01, C3 0B, C4 27, D0 A4 A1, then gamma E0/E1 from the
   panel vendor's init sequence.
4. INVON.

Interface (3A/B0/RGB), MADCTL and the window registers are not touched.

| Key | Action |
| --- | --- |
| 1 | INVON |
| 2 | INVOFF |
| 3 | Vendor values + INVON |
| 4 / 5 / 6 | Toggle MADCTL bit 08 (BGR) / 40 (MX) / 80 (MY) |
| 7 | TI defaults: INVOFF, MADCTL 08, TI gamma (as in `lcd_SetDefaultGamma`) |
| CLEAR | Exit |

Settings live in the panel controller and are lost when the calculator powers
off. Run it again after each power-up, or call it from your own program.

On-screen labels are Vietnamese without diacritics.
