---
name: dyadic-reference
description: Locate and summarize the Dyadic PWM design reference (algorithm, pinout, prior Verilog port, original VHDL). Use when implementing or porting the dyadic PWM, or when you need the design spec without scanning the whole reference tree.
---

# Dyadic PWM reference

All reference lives in `.claude/olddyadic/` (read-only; not part of the submission).
Indexed in `.claude/olddyadic/README.md`. Pull only the file you need.

## Where the answer usually is
| Need | File |
|------|------|
| Full design spec (modes, pins, timing, examples, block diagram) | `olddyadic/digital_dyadic_pwm/src/dyadic_doc.md` |
| Verilog implementation to port | `olddyadic/digital_dyadic_pwm/src/dyadic.v` |
| TT top wrapper pattern | `olddyadic/digital_dyadic_pwm/src/project.v` |
| Prior port change log + design analysis + compliance | `olddyadic/digital_dyadic_pwm/process.md` |
| Working cocotb tests to reuse | `olddyadic/digital_dyadic_pwm/test/` |
| Algorithm source of truth (all modes/widths) | `olddyadic/dyadic_vhdl/dpwm.vhd` |
| Port plan / IHP→GF deltas | `.claude/docs/porting-notes.md` |

## Algorithm in one paragraph
> ⚠️ **Errata.** The original VHDL picks the bit with the **lowest** set bit of the counter
> (`index = (m-1) - lowest_set_bit`). The taped-out GF chip uses the **highest** set bit (errata E1), and
> reads the fraction from other control bits than the VHDL (E2). See the `dyadic-errata` skill and
> `.claude/docs/errata.md` before you rely on this text.

The taped-out GF chip (`src/dyadic.v`): 12-bit control = `{ui_in[7:0], uio_in[3:0]}`. Selectable 5–9-bit PWM
(register 1). `uio_in[7]=1` is a **config write** (address `uio_in[6:4]`, data `ui_in`), not a mode bit.
Register 0 holds `m` (`[2:0]`), the mode (`[5:3]`: 0 Normal, 1 Dyadic, 2–4 Dither) and the constant-word flag.
In dyadic mode a window counter (`2^m` periods) selects one bit of the fraction (the low `m` control bits):
the chip uses the highest set bit of the counter, the VHDL the lowest. The bit is added (+1) to the duty of that
period. Over a window the average addition is `fraction / 2^m`. The extra resolution is `12 - B` bits. Counter 0
adds nothing. Outputs: `uo_out[0]`=PWM_HIGH, `[1]`=PWM_LOW (complementary, 6-cycle dead-time), `[2]`=sync clk,
`[7:3]`=duty MSBs. 513-cycle period → ~97.5 kHz at 50 MHz.

The legacy IHP port (`.claude/olddyadic/digital_dyadic_pwm`) had a fixed 8-bit PWM and used `uio_in[7]` as the
dyadic mode bit. The GF chip restored the 5–9-bit widths and the three dither modes.
