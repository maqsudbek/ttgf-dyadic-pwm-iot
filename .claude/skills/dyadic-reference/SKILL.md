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
12-bit control = `{ui_in[7:0], uio_in[3:0]}`. Base PWM is 8-bit (`control[11:4]`). In **dyadic
mode** (`uio_in[7]=1`, length `uio_in[6:4]`∈2..7), an N-bit counter increments once per switching
period; the **position of its most-significant set bit** indexes a bit of the LSB word, which is
added (+1) to the duty that period. Over a full 2^N counter cycle the average addition equals
`LSB_value / 2^N`, giving up to ~15-bit effective resolution. Counter==0 adds nothing.
Outputs: `uo_out[0]`=PWM_HIGH, `[1]`=PWM_LOW (complementary, 6-cycle dead-time), `[2]`=sync clk,
`[7:3]`=duty MSBs. 513-cycle period → ~97.5 kHz at 50 MHz.

The original VHDL (`dpwm.vhd`) additionally supports 5/6/7/8/9-bit selectable PWM and 3 dithering
modes — the TT port dropped these to fit I/O. Reconsider per `.claude/docs/open-questions.md`.
