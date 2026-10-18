# Workaround guide — use the chip on the Tiny Tapeout demo board

This guide shows how to get correct results from the taped-out chip `tt_um_maqsudbek_dyadic_pwm`
in spite of the known errors. The errors are listed in [README.md](README.md) (E1 to E7).

> **Status.** The procedures are tested in simulation against the submitted RTL.
> They are **not** tested on real silicon or on a real demo board. The board commands follow the
> source code of the Tiny Tapeout MicroPython SDK (v3.1.1). Check each step on the first chip you receive.

## 1. Choose a recipe

| You want | Recipe | Errors that remain |
|----------|--------|--------------------|
| Plain PWM, 5 to 9 bits | [A](#recipe-a--plain-pwm) | None. |
| Extra resolution. Simple. Higher ripple. | [B](#recipe-b--the-chips-dyadic-mode) | E1 (ripple). |
| Extra resolution. Same ripple as the FPGA. | [C](#recipe-c--host-side-dyadic-modulation-fpga-equal) | None. A host loop is necessary. |
| Dithering (modes 2, 3, 4) | [D](#recipe-d--dither-modes) | The value 0 (see E3). |

## 2. Rules for all recipes

1. Use `m <= 12 - bits` (E4). The limits are in the table in [section 5](#5-pin-map-of-the-control-word).
2. Put the fraction bits in the **lowest** bits of the control word (E2).
3. Write a config register **only while the clock is stopped** (E6).
4. In run mode keep `uio_in[7] = 0`.
5. Use only the width codes 0 to 4 in register 1 (5-bit to 9-bit).
6. With a constant word and `m = 1`, keep bit 0 of the word at 0 (E5).
7. Use a project clock of 25 MHz or lower, if the chip must work in all temperature and voltage corners.
   The slow corner needs about 33 ns per clock. See the timing section in [../info.md](../info.md).
8. Never write `uio_in` with bit 7 set, except in a config write.

> **CAUTION.** Stopping the clock freezes the outputs. If PWM_HIGH is high when the clock stops, it stays high.
> Disable the gate driver or disconnect the power stage before you write a config register, and before you
> run a script that can stop the clock. After a reset, wait for the second sync pulse before you enable the
> power stage (E7).

## 3. What you need

| Item | Note |
|------|------|
| Tiny Tapeout demo board with the shuttle chip | The current board (v3) has an RP2350. Older boards have an RP2040. |
| USB-C cable and a PC | Use a serial terminal, Thonny or `mpremote`. |
| Oscilloscope or logic analyzer | Look at `uo_out[0]` (PWM_HIGH), `uo_out[1]` (PWM_LOW) and `uo_out[2]` (sync). |
| Board firmware that knows the shuttle `ttgf26a` | If `tt.shuttle.tt_um_maqsudbek_dyadic_pwm` is not found, update the firmware. See <https://github.com/TinyTapeout/tt-micropython-firmware>. |
| [host/dyadic_host.py](host/dyadic_host.py) on the board | `mpremote fs cp docs/errata/host/dyadic_host.py :dyadic_host.py` |

## 4. Start the chip (what `Chip.start()` does)

`Chip.start()` does all steps below. Do the steps by hand if you do not use the library.

1. Select the project: `tt.shuttle.tt_um_maqsudbek_dyadic_pwm.enable()`.
   The board can now start the project clock at **50 MHz** (the `clock_hz` of `info.yaml`).
2. Let the RP2 drive the inputs: `tt.mode = RPMode.ASIC_RP_CONTROL`
   (`from ttboard.mode import RPMode`).
3. Stop the clock: `tt.clock_project_stop()`.
4. Let the RP2 drive the `uio` pins: `tt.uio_oe_pico.value = 0xFF`.
   After `enable()` the RP2 may not drive the `uio` pins. Do not rely on a default value.
   The chip uses all `uio` pins as inputs (`uio_oe = 0`), so there is no conflict with the chip.
   Do not connect an external driver to the `uio` pins.
5. Set `tt.ui_in.value = 0` and `tt.uio_in.value = 0`.
6. Reset the chip: `tt.reset_project(True)`.
7. Wait 2 ms. Release the reset: `tt.reset_project(False)`.
   The reset is necessary. Between `enable()` and step 5, the chip can run with an undriven `uio_in[7]`.
   It can then write a random config.
8. Write the config registers (next block).
9. Start the clock: `tt.clock_project_PWM(frequency)`.

**Safe config write (E6).** Use this function for each register. The clock is stopped, so no clock edge
can see a mixed pin state.

```python
def write_cfg(addr, data):
    tt.clock_project_stop()
    tt.ui_in.value = data                    # data on ui_in
    tt.uio_in.value = 0x80 | (addr << 4)     # strobe uio_in[7] = 1 and address on uio_in[6:4]
    tt.clock_project_once()                  # one rising edge writes the register
    tt.uio_in.value = 0                      # back to run mode
    tt.ui_in.value = 0                       # (put your control word here)
    tt.clock_project_PWM(CLOCK_HZ)           # clock_project_once() stopped the clock. Start it again.
```

After `clock_project_stop()`, the SDK releases the `clk` pin of the RP2 (high impedance) until the next
`clock_project_once()`. During a config write, do not press the clock button of the board. On board v3.3
and later, you can disable the button with `tt.manual_project_clock.monitoring = False`.
Check with a scope that `clk` stays low while the clock is stopped.

Write register 1 (width) first. Write register 0 (mode and length) last. The modulation then starts
when all other settings are ready.

| Register (`uio_in[6:4]`) | Data (`ui_in`) |
|--------------------------|----------------|
| 0 | `[2:0]` = m, `[5:3]` = mode (0 Normal, 1 Dyadic, 2 to 4 Dither v1 to v3), `[6]` = constant word flag |
| 1 | `[2:0]` = 0 (5-bit), 1 (6-bit), 2 (7-bit), 3 (8-bit), 4 (9-bit) |
| 2 | `[6:0]` = constant word |

After a reset the chip is an 8-bit PWM in Normal mode.

## 5. Pin map of the control word

The control word has 12 bits. Bit `n` of the word is on a pin as follows:

| Control bits | Pins |
|--------------|------|
| 11 to 4 | `ui_in[7]` to `ui_in[0]` |
| 3 to 0 | `uio_in[3]` to `uio_in[0]` |

The base duty uses the top `B` bits. The fraction uses the lowest `m` bits.

| Width `B` | Base duty (control bits) | Base duty pins | Largest `m` | Fraction pins at the largest `m` |
|-----------|--------------------------|----------------|-------------|----------------------------------|
| 5 | 11 to 7 | `ui_in[7:3]` | 7 | `ui_in[2:0]`, `uio_in[3:0]` |
| 6 | 11 to 6 | `ui_in[7:2]` | 6 | `ui_in[1:0]`, `uio_in[3:0]` |
| 7 | 11 to 5 | `ui_in[7:1]` | 5 | `ui_in[0]`, `uio_in[3:0]` |
| 8 | 11 to 4 | `ui_in[7:0]` | 4 | `uio_in[3:0]` |
| 9 | 11 to 3 | `ui_in[7:0]`, `uio_in[3]` | 3 | `uio_in[2:0]` |

For a smaller `m`, the fraction uses only the lowest `m` pins. Example: 8-bit and `m = 2` use `uio_in[1:0]`.
Do not use the pins between the base duty and the fraction. Set them to 0.
`control_word(value, bits, m)` calculates the word. `split_pins(word)` gives the pin values.

## Recipe A — Plain PWM

No error applies. Normal mode, 5 to 9 bits.

```python
import dyadic_host as h
chip = h.Chip(tt, clock_hz=1000000)
chip.start(bits=8)                 # Normal mode
chip.set_word(0x80 << 4)           # duty 128 of 256. PWM_HIGH = 2 * 128 + 1 = 257 cycles
```

PWM_HIGH has `duty * 2^(9-B) + max(1, 2^(8-B))` cycles in a period of 513 cycles.

## Recipe B — The chip's dyadic mode

Use this recipe when you need extra resolution and a higher ripple is acceptable (E1).
The average duty is correct. Use it if the output filter is slow compared with `2^m` periods.

```python
chip = h.Chip(tt, clock_hz=1000000)
chip.start(bits=8, m=4, mode=h.MODE_DYADIC)
chip.set_word(h.control_word(1234, bits=8, m=4))   # 1234 / 16 = 77.125 base steps
```

Result for this example (PWM_HIGH cycles in the 16 periods of one window; both sequences repeat in every window):

| Design | Sequence |
|--------|----------|
| Chip | 155, 155, **157, 157**, 155 ×12 |
| VHDL (FPGA) | 155 ×4, **157**, 155 ×7, **157**, 155 ×3 |

Both sequences have the same average (155.25 cycles).

If you change the control word while the clock runs, the chip can use a mixed old and new word in one
period. The two pin ports (`ui_in` and `uio_in`) are not written at the same time.

## Recipe C — Host-side dyadic modulation (FPGA-equal)

Use this recipe when you need the same ripple as the FPGA. The chip stays in **Normal mode**.
The host adds the `+1` in each period in the VHDL order and writes the new control word.
In simulation, the result is equal to `dpwm.vhd`, period by period.
The host writes right after the sync edge. This is far from the next latch, so a mixed word cannot reach the chip.

```python
import dyadic_host as h
chip = h.Chip(tt, clock_hz=100000)
chip.start(bits=8)                                  # Normal mode
loop_us = chip.measure_loop_us()
print(loop_us, h.safe_clock_hz(loop_us))            # the clock must be at or below this value
chip.run_soft_dyadic(lambda: 1234, m=4, periods=1000)   # lambda returns the value for the next period
print(chip.late_periods)                            # must be 0
```

How it works:

1. The chip latches the duty at the start of each period.
2. The sync output `uo_out[2]` rises at the start of the period.
3. The host sees the rise. It writes the control word for the **next** period.
4. The host must finish before the period ends. About 509 of the 513 clock cycles are usable.

How to choose the clock:

* A pass of the loop (one read and one write) takes `loop_us`. The host can need two passes: one to see the
  edge and one to write. `safe_clock_hz(loop_us)` includes these two passes and a safety factor of 4.
* Measure the loop with `measure_loop_us()`. Start with 100 kHz (switching frequency 195 Hz). Increase the clock
  only when `late_periods` stays 0.
* A switching frequency of 97 kHz (50 MHz clock) needs a host that writes once in 10 µs. The speed of the RP2
  with MicroPython is not measured. It probably cannot do this. Use a faster controller.
* If `late_periods` is not 0, the host missed a period and the dyadic sequence is wrong. Lower the clock.

## Recipe D — Dither modes

The dither modes add `(lsb + 1) / 2^m` (E3). Write `value - 1` as the control word to get `value`.

```python
chip = h.Chip(tt, clock_hz=1000000)
chip.start(bits=8, m=4, mode=h.MODE_DITHER_V1)      # mode 2. Modes 3 and 4 work the same way.
chip.set_word(h.dither_control_word(1234, bits=8, m=4))
```

The value 0 cannot be reached in the dither modes. The chip gives `1 / 2^m`. For an exact 0, write register 0 = 0
(Normal mode) and set the base duty to 0.

## 6. What the workarounds cannot do

* The block order of the chip's dyadic mode (E1) cannot be changed with pins. Only Recipe C removes it.
* Recipe C needs a host loop. The chip cannot do the modulation alone.
* The slow-corner timing limit does not change. Use 25 MHz or lower for guaranteed operation.
* The width codes 5, 6 and 7 are not available (E7).

## 7. If something is wrong

| Symptom | Possible cause | Action |
|---------|----------------|--------|
| No PWM output | Clock stopped, chip in reset, or `uio_oe_pico` not set | Check `tt.is_auto_clocking`. Call `tt.reset_project(False)`. Set `tt.uio_oe_pico.value = 0xFF`. |
| PWM runs at 50 MHz | `enable()` can start the clock | Call `clock_project_stop()`, then `clock_project_PWM(your_clock)`. |
| The fraction has no effect | Fraction on the wrong pins (E2), or `dyadic_len = 0` | Use `control_word()`. Check register 0. |
| Width or mode changes by itself | Config written while the clock runs (E6) | Use `Chip.write_cfg()`. |
| `late_periods` is not 0 | Host loop too slow | Lower the clock. Measure with `measure_loop_us()`. |
| `tt.shuttle.tt_um_maqsudbek_dyadic_pwm` is not found | The firmware has no index for the shuttle | Update the firmware. |
| Duty is 1/2^m too high in a dither mode | E3 | Use `dither_control_word()`. |
