![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg)

# Dyadic PWM Generator — Tiny Tapeout IHP26a

A digital PWM generator with **dyadic modulation** for enhanced effective resolution, targeting the [Tiny Tapeout](https://tinytapeout.com) IHP26a shuttle (IHP SG13G2 PDK).

- [Read the project datasheet](docs/info.md)
- [Detailed design documentation](src/dyadic_doc.md)

## Overview

This design converts a 12-bit control signal into a complementary PWM output with configurable dead-time protection. In normal mode it operates as a standard 8-bit PWM. In **dyadic mode**, the lower bits modulate the duty cycle over multiple switching periods using a dyadic (binary) sequence, achieving up to ~15-bit effective resolution while maintaining the same ~97.5 kHz switching frequency.

### Key Specifications

| Parameter | Value |
|-----------|-------|
| Clock frequency | 50 MHz |
| PWM period | 513 cycles (~97.5 kHz) |
| Base resolution | 8-bit (256 levels) |
| Effective resolution | Up to ~15-bit (dyadic mode) |
| Dead-time | 6 cycles (120 ns) |
| Outputs | Complementary PWM + sync clock |

### Pin Mapping

```
  ui_in[7:0]  → Control MSB [11:4]       uo_out[0] ← PWM_HIGH
  uio_in[3:0] → Control LSB [3:0]        uo_out[1] ← PWM_LOW
  uio_in[6:4] → Dyadic length (0,2-7)    uo_out[2] ← SYNC_CLK
  uio_in[7]   → Mode (0=Normal,1=Dyadic) uo_out[7:3] ← DUTY[7:3] (debug)
```

All bidirectional pins are configured as inputs (`uio_oe = 8'b0`).

## How the Dyadic Algorithm Works

The core idea: for an N-bit LSB word, a free-running N-bit counter determines which bit of the LSB word to read on each PWM cycle. The counter's **MSB index** (position of the highest set bit) selects the LSB bit. Over one full counter period (2^N cycles), bit[k] is selected exactly 2^k times, so the average addition equals `LSB_value / 2^N` — a mathematically exact fractional duty modulation.

Example with 3-bit dyadic (LSB = `101` = 5):

| Counter | MSB Index | Selected Bit | Add |
|---------|-----------|-------------|-----|
| 0 | — (skip) | — | 0 |
| 1 | 2 | bit[0] = 1 | +1 |
| 2 | 1 | bit[1] = 0 | 0 |
| 3 | 1 | bit[1] = 0 | 0 |
| 4 | 0 | bit[2] = 1 | +1 |
| 5 | 0 | bit[2] = 1 | +1 |
| 6 | 0 | bit[2] = 1 | +1 |
| 7 | 0 | bit[2] = 1 | +1 |

Total additions: 5 out of 8 cycles → average +5/8 → matches LSB/2^N exactly.

## Project Structure

```
src/project.v     — TT top wrapper (tt_um_dyadic_top)
src/dyadic.v      — Core PWM + dyadic modulation engine
src/dyadic_doc.md — Detailed design documentation
test/test.py      — cocotb testbench (8 tests)
test/tb.v         — Verilog testbench wrapper
docs/info.md      — Project datasheet
```

## How to Test

1. Apply a 50 MHz clock. Release reset (`rst_n` high).
2. Set `ui_in = 0x80` for ~50% duty. Leave `uio_in = 0x00` (normal mode).
3. Observe `uo_out[0]` (PWM_HIGH) and `uo_out[1]` (PWM_LOW) — complementary with 120 ns dead-time.
4. For dyadic mode: `uio_in[7] = 1`, `uio_in[6:4]` = dyadic length, `uio_in[3:0]` = LSB value.

The cocotb testbench verifies reset behavior, normal-mode duty sweep, dead-time correctness, dyadic modulation, sync clock, and boundary conditions.

## What is Tiny Tapeout?

Tiny Tapeout is an educational project that aims to make it easier and cheaper than ever to get your digital and analog designs manufactured on a real chip.

To learn more and get started, visit https://tinytapeout.com.

The GitHub action automatically builds the ASIC files using [LibreLane](https://www.zerotoasiccourse.com/terminology/librelane/).

## Resources

- [FAQ](https://tinytapeout.com/faq/)
- [Digital design lessons](https://tinytapeout.com/digital_design/)
- [Learn how semiconductors work](https://tinytapeout.com/siliwiz/)
- [Join the community](https://tinytapeout.com/discord)
- [Build your design locally](https://www.tinytapeout.com/guides/local-hardening/)
- [Enabling GitHub Pages](https://tinytapeout.com/faq/#my-github-action-is-failing-on-the-pages-part)
- [Submit your design to the next shuttle](https://app.tinytapeout.com/)
