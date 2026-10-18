<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## ⚠️ Known issues (errata) — read this first

The chip is already made. The original VHDL runs on an FPGA. A period-by-period comparison with the VHDL found
differences in the dyadic and dither modes. It also found a weakness in the config write.
**Normal PWM (5 to 9 bits) is correct.**

| ID | Problem | What to do |
|----|---------|------------|
| E1 | The dyadic `+1` periods come in blocks, not evenly spaced. The average duty is correct. The ripple is larger. | Use the host-side dyadic method (chip in Normal mode), or accept the ripple. |
| E2 | The chip reads the fraction bits from `control[m-1:0]`, not from the bits below the base duty. | Put the fraction in the **lowest** `m` control bits (`uio_in[3:0]`, then `ui_in[2:0]`). |
| E3 | Dither modes add `(lsb+1)/2^m`, not `lsb/2^m`. | Use dyadic mode, or write `value − 1` as the control word. |
| E4 | The fraction overlaps the base duty if `bits + m > 12`. | Use `m ≤ 12 − bits`. The extra resolution is `12 − bits` bits (7 for 5-bit, 4 for 8-bit). |
| E5 | A constant word with `m = 1` is used. | Keep bit 0 of the word at 0. |
| E6 | A config register is written at **every** clock edge while `uio_in[7] = 1`. | Stop the clock. Write with one clock step. Start the clock again. |

The workarounds are tested in simulation only. No test ran on real silicon.
Details, workarounds with code for the demo board, and the corrected design are in
[errata/README.md](https://github.com/maqsudbek/ttgf-dyadic-pwm-iot/blob/main/docs/errata/README.md) and
[errata/workaround-guide.md](https://github.com/maqsudbek/ttgf-dyadic-pwm-iot/blob/main/docs/errata/workaround-guide.md).

## How it works

This is a **digital PWM (DPWM) generator** with selectable resolution, dyadic modulation and
dithering. A 12-bit control word sets the duty cycle; the design produces complementary
high-/low-side outputs with dead-time, plus a sync clock.

**Selectable width.** The PWM resolution is configurable to **5, 6, 7, 8 or 9 bits**. All widths
share the same **513-cycle switching period** (~97.5 kHz at a 50 MHz clock); the chosen B-bit duty
is scaled onto that period by `scaled = duty·2^(9−B) + max(1, 2^(8−B))`.

**Modes.** Beyond plain **Normal** PWM, the design adds:
- **Dyadic** — the lower `m` bits of the control word are distributed as a `+1` sequence across a
  2^m-period window (the bit selected each period is `lsb[highest_set_bit(counter)]`), raising the
  *effective* resolution by up to `12 − B` bits (errata E1, E2, E4).
- **Dithering v1/v2/v3** — a sigma-delta-style `+1` decision (`lsb ≥ counter`, errata E3); v2 samples
  the LSB once per 2^m window, v3 also samples the base duty once per window.
- A **constant dyadic word** can replace the control LSBs as the modulation source.

**Configuration interface.** Static settings live in a small register file written over the pins.
`uio_in[7]` selects the mode:

| `uio_in[7]` | Meaning | `ui_in[7:0]` | `uio_in[6:4]` | `uio_in[3:0]` |
|-------------|---------|--------------|---------------|---------------|
| `0` (run)   | drive control word | `ctrl[11:4]` | — | `ctrl[3:0]` |
| `1` (config)| write a register   | write data   | reg address   | — |

Config registers (written while `uio_in[7]=1`):

| Addr (`uio_in[6:4]`) | Data (`ui_in`) |
|----------------------|----------------|
| `0` | `[2:0]`=dyadic_len (0–7), `[5:3]`=mode (0=Normal,1=Dyadic,2–4=Dither v1–v3), `[6]`=const_dyadic_flag |
| `1` | `[2:0]`=pwm_bits_sel (0→5-bit … 4→9-bit) |
| `2` | `[6:0]`=dyadic_word (constant modulation word) |

After reset the design defaults to **8-bit Normal** PWM (dyadic_len=0), so it behaves as a plain
8-bit PWM until configured. Outputs: `uo_out[0]`=high-side, `uo_out[1]`=low-side (complementary,
6-cycle / 120 ns dead-time), `uo_out[2]`=sync clock, `uo_out[7:3]`=duty MSBs (debug, normalised to
the 9-bit domain). All `uio` pins are inputs.

**Clock / timing.** The design targets a **50 MHz** clock and meets timing at the typical and fast
process corners in post-layout STA (≈ +3.7 ns and +10.6 ns setup slack; hold met at all corners).
At the worst-case slow corner (125 °C, 3.0 V) the longest path — the width-scaled duty computation
that feeds the duty comparator — does not close 50 MHz, so for operation guaranteed across all
corners use roughly **≤ 25 MHz** (30 MHz has no margin; the RP2 microcontroller supplies the clock and is adjustable 1 Hz–~66 MHz).
The PWM switching frequency is `clk / 513`, so it scales with whatever clock you choose.

## How to test

1. Hold `rst_n` low for several clocks, then release. With no configuration the design is an 8-bit
   PWM: drive `ui_in` with the duty (e.g. `0x80` ≈ 50 %), keep `uio_in = 0x00`, and observe
   `uo_out[0]`/`uo_out[1]` (complementary) and the ~97.5 kHz sync clock on `uo_out[2]`.
   On the demo board, `enable()` can start a 50 MHz clock. Stop it with `tt.clock_project_stop()` and start
   your clock with `tt.clock_project_PWM(...)`. Set `tt.uio_oe_pico.value = 0xFF`. Without it the RP2 may not
   drive the `uio` pins.
2. **Configure** features with the config interface (errata E6):
   1. Stop the clock: `tt.clock_project_stop()`.
   2. Put the data on `ui_in`.
   3. Put `uio_in[7]=1` and the register address on `uio_in[6:4]`.
   4. Give **one** clock edge: `tt.clock_project_once()`.
   5. Set `uio_in[7]=0`.
   6. Start the clock again: `tt.clock_project_PWM(...)`.

   Examples (register 0 = mode and length, register 1 = width, register 2 = constant word):
   - *Select 5-bit width:* write addr 1 = `0x00`.
   - *Dyadic, 4-bit (8-bit PWM):* write addr 0 = `0x0C` (mode=1, dyadic_len=4); then run with `uio_in[3:0]`
     as the LSB word — the average duty shifts by `lsb/16` over 16 periods. For other widths and
     lengths put the fraction in the lowest `m` bits and keep `m ≤ 12 − bits` (errata E2, E4).
   - *Dithering v1:* write addr 0 = `0x14` (mode=2, dyadic_len=4). The average is `(lsb+1)/16` (errata E3).
   - *Constant dyadic word:* write addr 0 = `0x4C` (const flag + dyadic mode, len 4) and addr 2 =
     the 7-bit word; the modulation then ignores the control LSBs.
3. The cocotb testbench (`test/test.py`) exercises reset, all five widths, max-duty/dead-time, the
   sync clock, dyadic mode, the three dithering modes and the constant-word path. The errata tests
   are in `docs/errata/test/` (`./run_checks.sh`).

## External hardware

None required for bench testing. For power-electronics use, wire `uo_out[0]` (high-side) and
`uo_out[1]` (low-side) to a half-bridge gate driver — the built-in dead-time prevents shoot-through
in, e.g., a synchronous buck converter or class-D stage.

## Post-layout results, expected behaviour & limits

Hardened with LibreLane on **GF180MCU (`gf180mcuD`)**, 1×1 tile, target clock **50 MHz (20 ns)**.
All numbers below are from the post-PnR multi-corner static timing analysis (8 corners).

### Physical
| Metric | Value |
|---|---|
| Tile utilization | **45.5 %** (fits 1×1 with margin) |
| Standard cells | 1146 |
| DRC / antenna / power-grid / LVS-pin violations | **0** |
| Hold worst slack (all corners) | **+0.52 ns** — no hold risk |

### Timing by corner (setup, 50 MHz)
| Corner | Worst setup slack | Verdict |
|---|---|---|
| Typical (`tt`, 25 °C, 3.30 V) | **+3.73 ns** | meets 50 MHz |
| Fast (`ff`, −40 °C, 3.60 V) | **+10.62 ns** | meets, large margin |
| Slow (`ss`, 125 °C, 3.00 V) | **−13.22 ns** | **does not meet 50 MHz** |

There are **52 violating register→register paths, only in the slow corner** (typical/fast = 0), plus
minor drive-strength warnings in that corner (52 max-slew, 1 max-cap, 1 max-fanout). The single
max-cap/max-fanout net persists across corners but is not a functional hazard.

### What works, and where it can fail
- **Functional correctness:** verified by the cocotb suite (10/10) and by the **gate-level** netlist
  test (`gl_test`) on the post-layout cells — reset, all five widths (5–9-bit), max-duty saturation,
  dead-time (no shoot-through), sync clock, dyadic mode, all three dithering modes, and the constant
  dyadic word. All `uio` pins read as inputs. These tests check the *average* duty for one width and
  one length (8-bit, `m = 4`). They do **not** find the errata E1 to E6 at the top of this page. The
  period-by-period comparison with the VHDL found them (see [errata/README.md](https://github.com/maqsudbek/ttgf-dyadic-pwm-iot/blob/main/docs/errata/README.md)).
- **Critical path (the thing that limits Fmax):** the registered duty threshold `duty_compare` is
  computed combinationally as `scaled = duty·2^(9−B) + offset` followed by the dyadic/dither `+1`
  decision and the period comparison. This is ~30 logic levels deep (start: a `dyadic_len` register;
  end: `duty_compare`). At the slow corner it needs ≈34 ns, hence the −13 ns miss at 20 ns.
- **Expected operating envelope:**
  - At **normal temperature/voltage (typical silicon): 50 MHz works** (+3.7 ns margin).
  - For **guaranteed operation across all corners (hot 125 °C and/or low 3.0 V): use 25 MHz or lower.**
    The slow corner needs about 33 ns per clock, so 30 MHz has no margin.
  - Switching frequency is always `clk / 513` (≈ 97.5 kHz at 50 MHz; ≈ 49 kHz at 25 MHz).
  - **Hold is met at every corner**, so there is no fast-corner/hold failure mode — only the
    setup-vs-frequency trade-off above.
- **Failure mode if over-clocked at a bad corner:** the duty threshold can be sampled before it
  settles, producing an incorrect duty/edge for that period (functional glitch), not a hard hang —
  drop the clock to recover. The dead-time logic is short and is not on the critical path, so
  complementary-output non-overlap is preserved.

> These limits are inherent to this (area-optimised, single-cycle datapath) build. A future revision
> can register the `scaled`/`duty_compare` computation to close 50 MHz across all corners with the
> full feature set.
