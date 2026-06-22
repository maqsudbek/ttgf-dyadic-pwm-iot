<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

This is a digital PWM generator with dyadic modulation support. It takes a 12-bit control signal (8 bits via `ui_in`, 4 bits via `uio_in[3:0]`) and generates a complementary PWM output with dead-time protection.

In **normal mode** (`uio_in[7]=0`), the upper 8 bits set the duty cycle (0–255) with standard 8-bit resolution at ~97.5 kHz switching frequency (513-cycle period at 50 MHz).

In **dyadic mode** (`uio_in[7]=1`), the lower bits modulate the base duty cycle over multiple switching periods using a dyadic (binary) sequence. The `uio_in[6:4]` field selects how many LSB bits (2–7) participate. This achieves higher effective resolution (up to ~15-bit) by distributing +1 adjustments across a counter period proportional to the LSB value.

Outputs include complementary PWM signals with 6-cycle (120 ns) dead-time, a sync clock, and the upper 5 bits of the duty cycle for debug.

## How to test

1. Set `ui_in[7:0]` to the desired 8-bit duty value (e.g., `0x80` for ~50%).
2. Leave `uio_in = 0x00` for normal mode. The PWM output appears on `uo_out[0]` (high-side) and `uo_out[1]` (low-side, complementary). `uo_out[2]` is the ~97.5 kHz sync clock.
3. For dyadic mode: set `uio_in[7]=1`, `uio_in[6:4]` to the dyadic length (e.g., `3'b100` for 4-bit), and `uio_in[3:0]` to the LSB value. Observe the average duty shift over multiple periods.

## External hardware

No external hardware required for basic testing. For power electronics applications, connect `uo_out[0]` and `uo_out[1]` to a half-bridge gate driver (e.g., for a buck converter).
