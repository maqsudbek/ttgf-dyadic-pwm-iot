# Usage guide — driving the Dyadic PWM after tapeout

This guide shows how to **operate the chip on the TinyTapeout demo board** once it comes back from
fabrication: selecting the project, setting the clock, configuring the modes, streaming a duty, and
reading the outputs — plus how to wire the PWM to real power hardware. For the internals see
[architecture.md](architecture.md); for the datasheet see [info.md](info.md).

---

## 1. What you need

- The **TinyTapeout GF26a demo board** (the PCB with the diced ASIC and an on-board **RP2040**
  manager) — TinyTapeout ships this with the shuttle.
- A **USB-C cable** to a host PC (the board draws ~180–200 mA at 5 V over USB).
- To watch the PWM: an **oscilloscope** or logic analyzer on the output PMOD; optionally an LED +
  resistor for a quick visual on a slow clock.

The RP2040 is the "management" controller: it selects which design on the die is active, generates
the `clk`, drives `rst_n`, and can drive the inputs and read the outputs. You talk to it either from
a **browser (Commander)** or a **MicroPython REPL**.

```
   ┌──────────┐  USB-C   ┌─────────┐   clk / rst_n / ui_in / uio_in   ┌──────────────┐
   │ Host PC  │ ───────► │ RP2040  │ ───────────────────────────────► │ tt_um_..._   │
   │ Commander│ ◄─────── │ manager │ ◄─────────────────────────────── │ dyadic_pwm   │
   │  or REPL │          └─────────┘     uo_out / uio_out             └──────┬───────┘
   └──────────┘                                                              │
                                                  output PMOD ───────────────┘  (scope / gate driver)
```

All I/O is **3.3 V logic**.

---

## 2. Select the project

### Option A — Commander (browser, easiest)
1. Open <https://commander.tinytapeout.com/> in Chrome/Edge/Opera/Brave.
2. Click **CONNECT TO BOARD** and pick the serial device.
3. In the project dropdown find **`tt_um_maqsudbek_dyadic_pwm`** and click **SELECT** to enable it.
4. Use the on-screen controls to set the clock, toggle inputs, and read outputs.

### Option B — MicroPython REPL
Connect a serial terminal to the board (e.g. `screen /dev/ttyACM0 115200`, or Thonny). The `tt`
object is the demo board:

```python
from machine import Pin
# tt is already available in the demo-board firmware
tt.shuttle.tt_um_maqsudbek_dyadic_pwm.enable()   # select & power this design
tt.reset_project(True)                            # hold rst_n LOW
tt.clock_project_PWM(50_000_000)                  # 50 MHz auto-clock (see §3 for corner caveat)
tt.reset_project(False)                           # release reset → design runs
```

> **Bit ordering.** In the SDK, `tt.ui_in` is the 8-bit input port, `tt.uio_in` the 8-bit
> bidirectional port (driven as inputs here), and `tt.uo_out` the 8-bit output port. You can address
> the whole byte (`tt.ui_in.value = 0x80`) or single bits (`tt.ui_in[7] = 1`).

---

## 3. Pick a clock frequency

The PWM **switching frequency is `clk / 513`**, and the design is a *synchronous* circuit clocked
entirely by `clk` from the RP2040 (1 Hz – ~66.5 MHz).

| Clock | Switching freq (`clk/513`) | Dead-time | Notes |
|---|---|---|---|
| 50 MHz | ≈ 97.5 kHz | 120 ns | Rated speed; **closes timing only at typical/fast silicon corners** |
| 30 MHz | ≈ 58 kHz | 200 ns | **Safe across all corners** (hot/cold, low voltage) |
| 1–10 kHz | a few Hz | — | Great for a *visible* LED demo / single-stepping |

```python
tt.clock_project_PWM(30_000_000)   # 30 MHz — guaranteed across all corners
# or single-step for debugging:
tt.clock_project_stop()
tt.clock_project_once()            # advance exactly one clock
```

If you over-clock at a hot/low-voltage corner the only symptom is an occasionally wrong duty for a
period (a soft glitch) — drop the clock and it recovers. See the timing section of
[architecture.md](architecture.md) for why.

---

## 4. Drive it — the simplest case (no config)

After reset the design is a plain **8-bit Normal PWM** (no configuration needed). The duty is the
**top 8 bits** of the control word, which in 8-bit mode is just `ui_in` (the 4 LSBs on `uio_in[3:0]`
are below the 8-bit window). Keep `uio_in = 0x00` so you stay in RUN mode.

```python
tt.uio_in.value = 0x00      # RUN mode (uio[7]=0), LSBs = 0
tt.ui_in.value  = 0x80      # 0x80 = 128 → ~50 % duty
print(hex(tt.uo_out.value)) # bit0=high, bit1=low, bit2=sync, bits7..3=duty debug
```

Expected on a scope (output PMOD):
- `uo_out[0]` high-side ~50 % duty at `clk/513`,
- `uo_out[1]` low-side, complementary with a 120 ns gap each edge,
- `uo_out[2]` sync clock, one square wave per switching period.

Try `ui_in = 0x00` (≈0 %), `0x40` (≈25 %), `0xC0` (≈75 %), `0xFF` (max — low-side turns off).

---

## 5. Configuring features

Configuration is a **single-clock write**: raise `uio_in[7]`, put the register **address** on
`uio_in[6:4]` and the **data** on `ui_in`, clock once, then drop `uio_in[7]` back to 0. The control
word is frozen during the write, so it's safe to reconfigure on the fly.

```python
def write_cfg(addr, data):
    tt.uio_in.value = 0x80 | ((addr & 0x7) << 4)   # uio[7]=1 (config), uio[6:4]=addr
    tt.ui_in.value  = data & 0xFF                   # write data
    tt.clock_project_once()                         # latch it
    tt.uio_in.value = 0x00                          # back to RUN mode
    tt.ui_in.value  = 0x00
```

Registers (see [architecture.md §3.1](architecture.md)):

| Addr | Meaning | Data bits |
|---|---|---|
| 0 | mode + length | `[2:0]` dyadic_len (m) · `[5:3]` mode (0=Normal,1=Dyadic,2/3/4=Dither v1/v2/v3) · `[6]` const-word flag |
| 1 | width select | `[2:0]` 0→5-bit, 1→6-bit, 2→7-bit, 3→8-bit, 4→9-bit |
| 2 | constant word | `[6:0]` constant modulation word |

### Recipes

```python
# 5-bit PWM
write_cfg(1, 0x00)            # width sel = 0 → 5-bit

# 9-bit PWM
write_cfg(1, 0x04)           # width sel = 4 → 9-bit

# Dyadic modulation, m=4 (effective +4 bits of resolution)
write_cfg(0, (1 << 3) | 4)   # mode=1 (dyadic), dyadic_len=4
# then run: the low 4 bits of the control word (uio_in[3:0]) set the fractional duty,
# averaged over 16 switching periods.
tt.uio_in.value = 0x08       # LSB nibble = 8  → +0.5 LSB average; RUN mode (uio[7]=0)
tt.ui_in.value  = 0x64       # base duty

# Dithering v1, m=4
write_cfg(0, (2 << 3) | 4)   # mode=2 (dither v1), dyadic_len=4

# Constant dyadic word (modulation independent of the live control LSBs)
write_cfg(0, (1 << 6) | (1 << 3) | 4)   # const flag + dyadic mode + len=4
write_cfg(2, 8)                          # constant word = 8
```

To see the fractional effect, average the high-time of `uo_out[0]` over many periods (16 for `m=4`):
a dyadic LSB of 8 raises the *average* duty by half a base step relative to LSB 0.

---

## 6. Reading the outputs

| Bit | Signal | How to observe |
|---|---|---|
| `uo_out[0]` | PWM high-side | scope; or average for duty (`high_cycles / 513`) |
| `uo_out[1]` | PWM low-side | scope — verify it never overlaps `uo_out[0]` |
| `uo_out[2]` | sync clock | scope trigger; counts switching periods |
| `uo_out[7:3]` | duty debug (top 5 bits, 9-bit-normalised) | `(tt.uo_out.value >> 3) & 0x1F` |

```python
val = tt.uo_out.value
high  = val & 1
low   = (val >> 1) & 1
sync  = (val >> 2) & 1
dutyd = (val >> 3) & 0x1F
```

At fast clocks you can't read individual PWM edges over USB — use a scope/logic analyzer on the
PMOD. To *read* with the RP2040, slow the clock right down (`tt.clock_project_PWM(1000)` or single
-step) and sample `tt.uo_out` each step.

---

## 7. Wiring to power hardware

The complementary high/low outputs with built-in dead-time are meant to drive a **half-bridge**:

```
            ┌──────── Vbus
            │
          ┌─┴─┐  high-side FET
 uo_out[0]┤   │
 (HS) ───►│  ─┤├─┐
          └─┬─┘  │
            ├────┼──► switch node  ──► L/C filter, motor phase, speaker, …
          ┌─┴─┐  │
 uo_out[1]┤   │  │
 (LS) ───►│  ─┤├─┘
          └─┬─┘  low-side FET
            │
           GND
```

- Route `uo_out[0]`/`uo_out[1]` through a proper **gate-driver IC** (the ASIC pins are 3.3 V logic
  and cannot drive power FETs directly). The 120 ns dead-time (@50 MHz) prevents shoot-through; at
  lower clocks the dead-time is proportionally longer (`6 / clk`).
- Typical uses: **synchronous buck/boost** DC-DC, **half-bridge motor drive**, **class-D audio**,
  high-resolution **LED dimming** (the dyadic/dither modes give sub-LSB brightness steps).
- At maximum duty the low-side is automatically disabled (no safe dead-time window) — design your
  driver to tolerate the high-side staying on.

> ⚠️ **Safety:** this is an educational chip. Validate gate-driver timing and add the usual
> protection (current limit, fusing, isolation) before connecting any real power stage. Start on the
> bench with a scope, not a live converter.

---

## 8. Quick bring-up checklist

1. Plug in USB-C; confirm the factory test counter runs on the 7-seg.
2. `tt.shuttle.tt_um_maqsudbek_dyadic_pwm.enable()`.
3. `tt.reset_project(True)` → `tt.clock_project_PWM(30_000_000)` → `tt.reset_project(False)`.
4. `tt.uio_in.value = 0`, `tt.ui_in.value = 0x80` → scope `uo_out[0]` for a ~50 % square wave.
5. Sweep `ui_in`; confirm duty tracks. Then try the config recipes in §5.
