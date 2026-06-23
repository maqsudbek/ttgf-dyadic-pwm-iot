# Architecture — Dyadic PWM generator (`tt_um_maqsudbek_dyadic_pwm`)

This document explains **how the design works internally**: the top-level wiring, every functional
block, the duty-scaling math, and where the speed limit comes from. For the pin map and a quick
datasheet read see [info.md](info.md); for how to operate the chip after tapeout see
[usage.md](usage.md).

All RTL is in two files:

| File | Module | Role |
|---|---|---|
| [`../src/project.v`](../src/project.v) | `tt_um_maqsudbek_dyadic_pwm` | TinyTapeout top wrapper — fixed pin interface, instantiates the core |
| [`../src/dyadic.v`](../src/dyadic.v) | `dyadic_pwm` | the whole design |

The wrapper does nothing but rename the standard TinyTapeout ports onto the core; **all logic lives
in `dyadic_pwm`**. Every output is driven, including `uio_oe` (all bidirectional pins are inputs, so
`uio_oe = 0x00`).

---

## 1. The big picture

A **digital PWM** works by counting clock cycles and comparing the count against a *duty threshold*:
the output is high while `counter ≤ threshold`, low otherwise. The switching frequency is
`clk / period`; the duty cycle is `threshold / period`.

This design fixes the **period at 513 clock cycles** for *all* resolutions and derives the threshold
from a **12-bit control word** plus a few static configuration registers. On top of plain ("Normal")
PWM it adds two ways to get *more effective resolution than the base counter has bits*:

- **Dyadic modulation** — deterministically nudges the duty by `+1` on a fixed, evenly-spread subset
  of switching periods.
- **Dithering** (3 variants) — a sigma-delta-style `+1` decision spread over a window.

Both average out, over a `2^m`-period window, to a fractional duty between two integer steps.

```
                 ui_in[7:0], uio_in[7:0]  (clk, rst_n, ena)
                            │
            ┌───────────────┴────────────────────────────────────────┐
            │                    dyadic_pwm                            │
            │                                                          │
            │   ┌──────────────┐   ┌──────────────┐                    │
   config ──┼──►│ Config        │   │ PWM counter  │ 0..512  ──┐       │
   (uio[7]) │   │ register file │   │ (÷513)       │           │       │
            │   │ + control-    │   └──────┬───────┘           │       │
            │   │ word capture  │          │ sw_cycle_start    │       │
            │   └──────┬────────┘          ▼                   │       │
            │          │            ┌──────────────┐           │       │
            │          │            │ Dyadic counter│ (per win) │       │
            │          │            └──────┬────────┘           │       │
            │          ▼                   ▼                    │       │
            │   ┌─────────────────────────────────────┐        │       │
            │   │ Control-word decomposition           │        │       │
            │   │  base_duty (top B bits) + lsb_value  │        │       │
            │   └──────────────┬──────────────────────┘        │       │
            │                  ▼                                │       │
            │   ┌─────────────────────────────────────┐        │       │
            │   │ Mode logic: add_bit + base_eff       │        │       │
            │   │ (Normal / Dyadic / Dither v1/v2/v3)  │        │       │
            │   └──────────────┬──────────────────────┘        │       │
            │                  ▼                                │       │
            │   ┌─────────────────────────────────────┐        │       │
            │   │ Duty scaling → 513-cycle period      │        │       │
            │   │  scaled = duty_b·2^(9−B) + offset    │        │       │
            │   └──────────────┬──────────────────────┘        │       │
            │                  ▼ (latched at period start)      │       │
            │            duty_compare ◄──────────────────────────       │
            │                  │                                        │
            │                  ▼                                        │
            │   ┌─────────────────────────────────────┐                │
            │   │ Output stage: compare + dead-time    │                │
            │   │  pwm_high, pwm_low, sync_clk, debug  │                │
            │   └──────────────┬──────────────────────┘                │
            └──────────────────┼─────────────────────────────────────┘
                               ▼
                  uo_out[0]=high  uo_out[1]=low  uo_out[2]=sync  uo_out[7:3]=duty debug
```

---

## 2. Pin interface

The TinyTapeout pin set is fixed (8 inputs, 8 outputs, 8 bidirectional). The bidirectional pins are
**all configured as inputs** here (`uio_oe = 0`).

```
 ui_in[7:0]  ─► control MSBs (run) / config write-data (config)
 uio_in[7]   ─► cfg_we   : 0 = RUN, 1 = CONFIG WRITE
 uio_in[6:4] ─► cfg_addr : config register address (config mode)
 uio_in[3:0] ─► control LSBs (run mode)
 clk         ─► from RP2040, 1 Hz .. ~66 MHz
 rst_n       ─► active-low reset
 ena         ─► 1 while powered (gates all sequential logic)

 uo_out[0]   ◄─ pwm_high   (high-side)
 uo_out[1]   ◄─ pwm_low    (low-side, complementary, dead-time)
 uo_out[2]   ◄─ sync_clk   (~clk/513 square wave)
 uo_out[7:3] ◄─ duty debug (top 5 bits of the 9-bit-normalised duty)
```

`uio_in[7]` is the **mode strobe**: when high, the cycle is interpreted as a configuration write;
when low, the pins carry the live 12-bit control word.

---

## 3. Block-by-block

### 3.1 Config register file + control-word capture
*(`dyadic.v` lines ~70–119)*

On every clock (while `ena`), the block looks at `uio_in[7]`:

- **`uio_in[7] = 1` (config write):** decode `uio_in[6:4]` as a register address and latch `ui_in`
  into the addressed register. The control word is **held** (not updated) during config writes.
- **`uio_in[7] = 0` (run):** capture the live control word `control_word = {ui_in[7:0], uio_in[3:0]}`.

The configuration registers are static — you write them once at start-up, then leave `uio_in[7]=0`
and stream control words.

| Addr (`uio_in[6:4]`) | Register | Fields (`ui_in` write data) |
|---|---|---|
| `0` | mode / length | `[2:0]` `dyadic_len` (m, 0–7) · `[5:3]` `dpwm_mode` (0–4) · `[6]` `const_dyadic_flag` |
| `1` | width select | `[2:0]` `pwm_bits_sel` (0→5-bit … 4→9-bit) |
| `2` | constant word | `[6:0]` `dyadic_word` (constant modulation word) |

**Reset defaults:** `pwm_bits_sel = 3` (8-bit), all others 0 → the design powers up as a plain
**8-bit Normal PWM** and works with no configuration at all.

`pwm_bits_sel` is decoded to an integer `pwm_bits ∈ {5,6,7,8,9}` (combinational, clamped to 8 for
illegal codes).

### 3.2 Timing counters
*(lines ~121–158)*

```
 pwm_counter : 10-bit, counts 0 → 512 → 0 …      (the 513-cycle switching period)
   sw_cycle_start = (pwm_counter == 512)          one pulse per period

 dyadic_counter : 7-bit, increments once per period (on sw_cycle_start)
   len_mask    = (1 << dyadic_len) - 1            low m bits set
   sel_counter = dyadic_counter & len_mask        the m-bit "window position" 0..2^m-1
```

`pwm_counter` is the fine-grained counter that builds one PWM period. `dyadic_counter` is the
*coarse* counter that advances once per PWM period; its low `m` bits (`sel_counter`) tell the mode
logic *where in the `2^m`-period averaging window* we currently are. A small function `hsb7()`
returns the **highest set bit position** of `sel_counter` — this is what makes the dyadic `+1`
sequence spread out evenly (bit-reversal-like) instead of bunching up.

### 3.3 Control-word decomposition
*(lines ~160–170)*

```
 shift_amt = 12 - pwm_bits                 (3..7)
 base_duty = control_word >> shift_amt      top B bits  → the integer duty
 lsb_value = control_word[6:0] & len_mask   low m bits  → the fractional part
 word_value= dyadic_word       & len_mask
 src_word  = const_dyadic_flag ? word_value : lsb_value
```

The **top `B` bits** of the 12-bit control word are the base duty (`B` = selected resolution). The
**low `m` bits** are the fractional remainder used by the modulation. `src_word` chooses whether the
modulation sequence comes from the live control LSBs or from a fixed `dyadic_word` register.

### 3.4 Mode logic — `add_bit` and `base_eff`
*(lines ~181–206)*

This is the heart of the design. For the current window position `sel_counter`, it decides whether
to add `+1` to the base duty this period (`add_bit`), and (for one mode) which base duty to use.
When `dyadic_len = 0` it is forced to **Normal** (no modulation).

| `dpwm_mode` | Name | `add_bit` rule |
|---|---|---|
| 0 | **Normal** | `0` (base duty only) |
| 1 | **Dyadic** | `src_word[hsb7(sel_counter)]` (0 when `sel_counter==0`) |
| 2 | **Dither v1** | `lsb_value ≥ sel_counter` |
| 3 | **Dither v2** | `eff_lsb ≥ sel_counter` (LSB sampled once per window) |
| 4 | **Dither v3** | `eff_lsb ≥ sel_counter`, **and** base duty also sampled once per window |

**Dyadic vs. dither, intuitively:**

- *Dyadic* picks the `+1` periods by indexing `src_word` with the highest-set-bit of the window
  counter. Because `hsb7` spreads the indices like a bit-reversed sequence, the boosted periods are
  scattered as evenly as possible across the `2^m` window — low ripple, fully deterministic.
- *Dither v1* is a straight threshold (`lsb ≥ position`) — a first-order sigma-delta. *v2* and *v3*
  add **sample-and-hold** (`lsb_latch`, `msb_latch`, captured at `sel_counter==1`) so the control
  word is frozen for the duration of a window, preventing mid-window updates from disturbing the
  average.

Over a full `2^m`-period window all four modulation modes average to `base + lsb/2^m` — i.e. they
recover the fractional bits that the base `B`-bit counter cannot represent directly. Example for
`m=4`, `lsb=8`: 8 of the 16 periods get `+1`, so the average duty is `base + 0.5` LSB.

### 3.5 Duty scaling onto the 513-cycle period
*(lines ~208–221)*

All resolutions share one 513-cycle period, so the `B`-bit duty must be scaled up:

```
 factor   = 1 << (9 - pwm_bits)            B=9→1, B=8→2, … B=5→16
 offset   = max(1, factor/2)               centering term
 duty_cap = (1 << pwm_bits) - 1            saturate at 2^B - 1
 base_plus= base_eff + add_bit
 duty_b   = min(base_plus, duty_cap)
 scaled   = duty_b * factor + offset       ← the value compared against pwm_counter
```

So an 8-bit duty of 128 becomes `128·2 + 1 = 257` ticks of high time out of 513 (~50 %). The
`offset` keeps the effective duty centred so the smallest codes still produce a clean pulse. A
separate `duty9` value (the duty re-normalised to a 9-bit domain) feeds the **debug** output
`uo_out[7:3]`.

### 3.6 Latched compare value
*(lines ~223–243)*

`duty_compare` (and the debug register, and the dither sample-and-hold latches) are updated **once
per period, at `pwm_counter == 0`**. Latching the threshold at the period boundary guarantees a
glitch-free pulse: the comparison value never changes *during* a period even if the control word
moves.

### 3.7 Output stage with dead-time
*(lines ~245–276)*

```
 pwm_high : counter in [1 .. duty_compare]
 pwm_low  : counter in (duty_compare+DEAD_TIME .. 507], only if duty_compare ≤ 495
            (otherwise low-side stays off — no room for safe dead-time at max duty)
 DEAD_TIME = 6 clocks (120 ns @ 50 MHz)
```

`pwm_high` and `pwm_low` are **complementary** with a 6-cycle gap on each edge so the two never
overlap — this is what lets you drive a half-bridge directly without shoot-through. At very high
duty the low-side is simply disabled (no safe dead-time window remains).

```
 one switching period (513 cycles), duty_compare = D:

 count   0    1 ............ D   D+1 .. D+6   D+7 ........ 507  508 .. 512
 high    _|‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾|___________________________________________
 low     ____________________|________________|‾‾‾‾‾‾‾‾‾‾‾‾‾‾|___________
                              └── dead-time ──┘              └─ dead-time
```

The **sync clock** `uo_out[2]` is set high at `pwm_counter==0` and low at the period midpoint
(`513/2`), giving one `~clk/513` square wave per switching period — handy as a scope trigger or to
clock downstream logic in lock-step with the PWM.

---

## 4. Numbers at a glance

| Quantity | Value |
|---|---|
| Switching period | **513 clocks** (fixed) for every resolution |
| Switching frequency | `clk / 513` → ≈ **97.5 kHz @ 50 MHz**, ≈ 58 kHz @ 30 MHz |
| Resolutions | 5 / 6 / 7 / 8 / 9-bit (base), up to ~+7 effective bits via dyadic/dither |
| Dead-time | 6 clocks = **120 ns @ 50 MHz** |
| Control word | 12 bits = `{ui_in[7:0], uio_in[3:0]}` |
| Config registers | 3 (mode/len, width, constant word) |

---

## 5. The speed limit (critical path)

The longest combinational path is the **width-scaled duty computation** that produces
`duty_compare`: starting at the `dyadic_len` register, through the mode logic, the multiply
`duty_b * factor`, the `+offset`, the saturate, and the compare — roughly **30 logic levels** deep.

Post-layout multi-corner STA (GF180MCU, 1×1 tile) shows:

| Corner | Setup slack @ 50 MHz | Verdict |
|---|---|---|
| Typical (25 °C, 3.30 V) | **+3.7 ns** | meets 50 MHz |
| Fast (−40 °C, 3.60 V) | **+10.6 ns** | meets, large margin |
| Slow (125 °C, 3.00 V) | **−13.2 ns** | does **not** meet 50 MHz |

Hold is met at every corner (+0.52 ns). So: **typical silicon runs at 50 MHz**; for guaranteed
operation across *all* corners use **≤ ~30 MHz**. Because the RP2040 sets the clock, you simply pick
a frequency that suits your corner/temperature. Over-clocking at a bad corner only corrupts the duty
of individual periods (a soft, recoverable glitch) — it does not hang, and dead-time is preserved
(it is short and off the critical path). Full numbers are in [info.md](info.md).

A future revision could register (pipeline) the `scaled`/`duty_compare` computation to close 50 MHz
at all corners with the full feature set; this build deliberately keeps the datapath single-cycle to
stay small (45.5 % tile utilization).
