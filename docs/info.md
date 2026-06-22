<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

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
  *effective* resolution by up to ~7 bits without extra base width.
- **Dithering v1/v2/v3** — a sigma-delta-style `+1` decision (`lsb ≥ counter`); v2 samples the LSB
  once per 2^m window, v3 also samples the base duty once per window.
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
corners use roughly **≤ 30 MHz** (the RP2040 supplies the clock and is adjustable 1 Hz–~66 MHz).
The PWM switching frequency is `clk / 513`, so it scales with whatever clock you choose.

## How to test

1. Hold `rst_n` low for several clocks, then release. With no configuration the design is an 8-bit
   PWM: drive `ui_in` with the duty (e.g. `0x80` ≈ 50 %), keep `uio_in = 0x00`, and observe
   `uo_out[0]`/`uo_out[1]` (complementary) and the ~97.5 kHz sync clock on `uo_out[2]`.
2. **Configure** features by pulsing the config interface: set `uio_in[7]=1`, put the register
   address on `uio_in[6:4]` and the data on `ui_in`, clock once, then drop `uio_in[7]` back to 0.
   - *Select 5-bit width:* write addr 1 = `0x00`.
   - *Dyadic, 4-bit:* write addr 0 = `0x0C` (mode=1, dyadic_len=4); then run with `uio_in[3:0]` as
     the LSB word — the average duty shifts by `lsb/16` over 16 periods.
   - *Dithering v1:* write addr 0 = `0x14` (mode=2, dyadic_len=4).
   - *Constant dyadic word:* write addr 0 = `0x4C` (const flag + dyadic mode, len 4) and addr 2 =
     the 7-bit word; the modulation then ignores the control LSBs.
3. The cocotb testbench (`test/test.py`) exercises reset, all five widths, max-duty/dead-time, the
   sync clock, dyadic mode, the three dithering modes and the constant-word path.

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
  dyadic word. All `uio` pins read as inputs.
- **Critical path (the thing that limits Fmax):** the registered duty threshold `duty_compare` is
  computed combinationally as `scaled = duty·2^(9−B) + offset` followed by the dyadic/dither `+1`
  decision and the period comparison. This is ~30 logic levels deep (start: a `dyadic_len` register;
  end: `duty_compare`). At the slow corner it needs ≈34 ns, hence the −13 ns miss at 20 ns.
- **Expected operating envelope:**
  - At **normal temperature/voltage (typical silicon): 50 MHz works** (+3.7 ns margin).
  - For **guaranteed operation across all corners (hot 125 °C and/or low 3.0 V): use ≤ ~30 MHz.**
  - Switching frequency is always `clk / 513` (≈ 97.5 kHz at 50 MHz; ≈ 58 kHz at 30 MHz).
  - **Hold is met at every corner**, so there is no fast-corner/hold failure mode — only the
    setup-vs-frequency trade-off above.
- **Failure mode if over-clocked at a bad corner:** the duty threshold can be sampled before it
  settles, producing an incorrect duty/edge for that period (functional glitch), not a hard hang —
  drop the clock to recover. The dead-time logic is short and is not on the critical path, so
  complementary-output non-overlap is preserved.

> These limits are inherent to this (area-optimised, single-cycle datapath) build. A future revision
> can register the `scaled`/`duty_compare` computation to close 50 MHz across all corners with the
> full feature set.
