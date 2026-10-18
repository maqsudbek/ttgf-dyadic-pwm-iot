# Errata and workarounds — Dyadic PWM chip

> **The chip is already made. The silicon cannot be changed.**
> This folder lists the known errors. It shows how to use the chip on the demo board in spite of them.
> It also holds the corrected design ("what the chip should have been").
>
> **Start here:** [workaround-guide.md](workaround-guide.md) (step by step for the demo board).
> **Status:** all workarounds are tested in simulation only. No test ran on real silicon.

## 1. Summary

The chip was compared with the original VHDL (`../dyadic_vhdl/dpwm.vhd`). The VHDL works on the FPGA.
The comparison used 420 test cases in a simulator. It compared the PWM_HIGH cycles of every switching
period (see [section 6](#6-how-the-errors-were-found-and-checked)).

**Normal PWM is correct.** For all five widths (5 to 9 bits) and all 4096 control words, the chip gives the
same PWM_HIGH and PWM_LOW output as the VHDL after start-up. The sync output is one clock early (E7).
The errors are in the dyadic and dither modes and in the pin handling.

| ID | Severity | What is wrong | Workaround in the chip | Fix needs |
|----|----------|---------------|------------------------|-----------|
| [E1](#e1--dyadic-order) | Medium | The dyadic `+1` periods are in a different order than in the VHDL. The average is correct. The ripple is larger. | Run the dyadic modulation in the host (Normal mode). | New silicon |
| [E2](#e2--lsb-word-comes-from-other-pins) | **High** | The chip reads the fraction bits from other control bits than the VHDL does. A VHDL-style wiring gives wrong duty values. | Put the fraction in the lowest control bits. | New silicon |
| [E3](#e3--dither-modes-add-one-step-too-much) | Low | The dither modes add `(lsb+1)/2^m`, not `lsb/2^m`. The VHDL has the same error. | Use dyadic mode, or write `value - 1` as the control word. | RTL change |
| [E4](#e4--the-fraction-overlaps-the-base-duty) | Low | The fraction overlaps the base duty when `bits + m > 12`. The VHDL has the same error. | Use `m <= 12 - bits`. | Documentation |
| [E5](#e5--constant-word-with-m--1) | Low | A constant word with `m = 1` is used. The VHDL ignores it. | Keep bit 0 of the word at 0. | RTL change |
| [E6](#e6--config-write-pin-order) | **High** | A config register takes whatever is on `ui_in` at every clock while `uio_in[7] = 1`. | Stop the clock. Write with one single step. | New silicon |
| [E7](#e7--small-differences) | Cosmetic | Small timing differences after reset. | None needed. | — |

"New silicon" means that the error is in the fabricated logic. Only a new tape-out can remove it.
The workarounds use the host. The host is the RP2 microcontroller on the demo board, or an external controller.

The extra resolution is `12 - B` bits for a `B`-bit PWM (7 bits at 5-bit, 4 bits at 8-bit).

## 2. Terms

| Term | Meaning |
|------|---------|
| `B`, `bits` | PWM width: 5, 6, 7, 8 or 9 bits. |
| `m` | Length of the fraction (1 to 7). It is register 0, bits `[2:0]`. The value 0 switches the modulation off. |
| fraction | The `m` low bits of the duty that the modulation spreads over a window. The text also calls it the LSB word. |
| base step | One step of the `B`-bit duty. |
| window | `2^m` switching periods. The modulation repeats every window. |
| value | The wanted duty with `m` fraction bits: a `(B + m)`-bit integer. `value / 2^m` is the duty in base steps. |
| control word | The 12-bit input `{ui_in[7:0], uio_in[3:0]}`. |
| constant word | The 7-bit register 2. It can replace the fraction. |
| host | The controller that drives the pins: the RP2 on the demo board, or an external controller. |
| ripple | Short-term error of the duty inside a window. |

## 3. Details

### E1 — Dyadic order

**Cause.** The chip selects the fraction bit with the *highest* set bit of the window counter
(`hsb7()` in `src/dyadic.v`). The VHDL uses the *lowest* set bit:
`index = (m - 1) - lowest_set_bit(counter)`.

**Effect.** Each bit `i` of the fraction is used in `2^i` periods in both designs. The average duty is the same.
The order is different. In the VHDL, the `+1` periods are evenly spaced. In the chip, they are in blocks.

Example: 8-bit PWM, `m = 4`, base duty 100, fraction `8`. The numbers are PWM_HIGH cycles per period.

| Design | 16 periods of one window |
|--------|--------------------------|
| VHDL | 201, 203, 201, 203, 201, 203, 201, 203, 201, 203, 201, 203, 201, 203, 201, 203 |
| Chip | 201 ×8, then 203 ×8 |

The worst running error over all fraction values (in base steps × periods; the sum of all period errors in a window):

| `m` | 3 | 4 | 5 | 7 |
|-----|---|---|---|---|
| VHDL | 0.88 | 1.06 | 1.22 | 1.55 |
| Chip | 2.0 | 4.0 | 8.0 | 32 |

The ripple matters little if the output filter is slow compared with one window. It matters if the filter is fast.

**Workaround.** Use the chip in Normal mode (register 0 = 0). The host adds the `+1` bit in each period,
in the VHDL order (`SoftDyadic` in `host/dyadic_host.py`). In simulation, the result is equal to the VHDL,
period by period, for all widths and lengths. The host must write the control word once per switching period.
See [workaround-guide.md](workaround-guide.md), recipe C.

### E2 — LSB word comes from other pins

**Cause.** The VHDL takes the `m` bits directly below the base duty:
`lsb = (control >> max(0, 12 - B - m)) & (2^m - 1)`. The chip always takes `control[m-1:0]`.

**Effect.** The two are equal only when `B + m >= 12`. Example: 8-bit PWM with `m = 2`.
The VHDL reads `control[3:2]`. The chip reads `control[1:0]`. A user who wires the pins like the FPGA
gets a wrong or zero fraction. The tests show wrong results in 16 of 20 width/length combinations
with `B + m < 12`.

**Workaround.** Put the fraction in the *lowest* `m` bits of the control word.
`control_word(value, bits, m)` in `host/dyadic_host.py` does this. The pin tables are in the workaround guide.

### E3 — Dither modes add one step too much

**Cause.** The dither modes (2, 3, 4) add `1` when `lsb >= counter`. The counter runs from 0 to `2^m - 1`.
This gives `lsb + 1` periods with `+1`, not `lsb`. The VHDL does the same.

**Effect.** The average duty is `base + (lsb + 1) / 2^m`. For `m = 4`, fraction 0 gives `+0.0625` and
fraction 15 gives `+1.0`. Dyadic mode (mode 1) has no such error.

**Workaround.** Use dyadic mode. Or write `value - 1` as the control word in dither modes
(`dither_control_word()`). The value 0 cannot be reached in dither modes. The chip then gives `1 / 2^m`.
The corrected RTL has an option for this (`-DDYADIC_UNBIASED_DITHER`).

### E4 — The fraction overlaps the base duty

**Cause.** The LSB word has up to 7 bits. The control word has 12 bits. The base duty uses the top `B` bits.
If `B + m > 12`, the fraction reads some bits of the base duty. The VHDL does the same.

**Effect.** Example: 8-bit PWM, `m = 7`. Control word `0x070` should give 7.0 base steps.
It gives 7.875. The error is up to 0.9 base step.

**Workaround.** Use `m <= 12 - B`: 5-bit up to 7, 6-bit up to 6, 7-bit up to 5, 8-bit up to 4, 9-bit up to 3.
`max_len(bits)` returns this limit.

### E5 — Constant word with m = 1

**Cause.** The VHDL ignores the constant dyadic word when `m < 2`. The chip uses bit 0 of the word.

**Workaround.** Keep bit 0 of the constant word at 0, or use `m >= 2`.

### E6 — Config write pin order

The VHDL has no config interface. E6 is a weakness of the new pin interface of the chip.

**Cause.** The chip writes a config register at *every* clock edge while `uio_in[7] = 1`. The data is the
value on `ui_in` at that edge. The demo board changes the pins one after the other.
If `ui_in` changes before `uio_in[7]` goes low, the register receives a byte of the next control word.

**Effect.** A wrong width, mode or length. The simulation shows this (`test_e6_config_pin_order`).

**Workaround.**

1. Stop the clock.
2. Set the data on `ui_in`, and the strobe and address on `uio_in`.
3. Give one clock edge.
4. Set the run-mode pins.
5. Start the clock.

`Chip.write_cfg()` does these steps.

### E7 — Small differences

* The sync output (`uo_out[2]`) rises one clock before PWM_HIGH. In the VHDL both rise at the same edge.
* The first period after reset uses duty code 0. The control register is still 0. Wait for the second sync
  pulse before you enable a power stage.
* A width code of 5, 6 or 7 selects 8-bit PWM. Use only the codes 0 to 4.
* By design, the chip has no `pre_clk` outputs, no x2 clock and no 12-bit duty output.

### Corrections to the first usage guide

These are not chip errors. They are errors in the older text. They are corrected in
[../usage.md](../usage.md).

* After `enable()`, the board can start the project clock at 50 MHz (the `clock_hz` of `info.yaml`).
  Stop this clock with `clock_project_stop()`. Then start your clock with `clock_project_PWM()`.
* After `enable()`, the RP2 may not drive the `uio` pins. Set `tt.uio_oe_pico.value = 0xFF`.
* `tt.clock_project_once()` stops the automatic clock. Start it again with `clock_project_PWM()`.
* The current demo board (v3) has an RP2350, not an RP2040.
* The timing limit: the slow corner needs about 33 ns. A 30 MHz clock has no margin there. Use 25 MHz or lower.

## 4. What the VHDL needs (FPGA design)

These findings are about the FPGA code only. They do not change the chip.

| ID | Finding |
|----|---------|
| V1 | The comments say that `pre_clk` rises 1, 2, 3 and 4 clocks early. The code gives 5, 9, 13 and 17 clocks. |
| V2 | `counter_val` and the MSB latch are not reset. In `m = 1` mode the phase depends on a variable that has no start value. It works only because the start value is the lowest integer. Set it to 0 in the reset branch. |
| V3 | `pre_clk_97466` is a derived clock that clocks a process. Use a clock enable instead, or declare it as a generated clock in the timing constraints. |
| V4 | E3 and E4 apply to the VHDL too. |
| V5 | `pwm_500khz.vhd` and `pwm_1mhz.vhd` are not used by `dpwm.vhd`. |

## 5. The corrected design

`rtl/dyadic_fixed.v` is the core as it should have been. It has the same module name and ports as
`src/dyadic.v`. `src/project.v` wraps it without any change.

| Change | Item |
|--------|------|
| Lowest-set-bit order | E1 |
| LSB word from the bits below the base duty | E2 |
| Constant word ignored for `m < 2` | E5 |
| Option `-DDYADIC_UNBIASED_DITHER` (compare with `>`) | E3 |

**Status.** Simulated only. Not hardened. A rough synthesis with Yosys gives about 14 % more generic
cells than `src/dyadic.v` (672 against 591). The new logic is on the path that already limits Fmax.
A new tape-out must register `lsb_value` and `add_bit` once per period.
Config-write handling (E6) is not changed. A new design should write a register only on the falling edge of `uio_in[7]`.

## 6. How the errors were found and checked

| Check | Result |
|-------|--------|
| Normal mode: VHDL against the submitted RTL, 5 widths, all 4096 codes (ramp), PWM_HIGH and PWM_LOW of every cycle | 0 differences |
| VHDL (GHDL) against the submitted RTL, 420 static cases (4 modes × 5 widths × 7 lengths × 3 control words) | 193 equal, 46 same values in other order, 181 different |
| VHDL against the corrected RTL, same 420 cases | 420 equal |
| Same, with constant word | 420 equal (the submitted RTL: 200 equal) |
| VHDL against the corrected RTL, control word that changes in every period (16 cases, 600 periods) | 0 differences |
| Python model (`test/vhdl_model.py`) against the VHDL | 420 of 420 equal |
| Corrected RTL against the Python model (cocotb) | 207 cases equal |
| Submitted RTL: E1 (with workaround), E2, E3, E5 and E6 (cocotb) | 6 tests pass. E4 and E7 have no test. |
| Corrected RTL with the original `test/test.py` | 10 of 10 pass |
| Host library with a mock of the board object | 14 tests pass |

**Not checked.** Nothing was run on real silicon. The board commands follow the source of the
Tiny Tapeout MicroPython SDK (v3.1.1). The speed of the MicroPython loop on the board is not measured.
The corrected RTL is not hardened. The comparison covers PWM_HIGH (all cases) and PWM_LOW (Normal mode).
It does not cover dead-time in the dyadic and dither modes.

Commands:

```bash
# Simulation tests (iverilog and the project .venv)
source .venv/bin/activate && cd docs/errata/test && ./run_checks.sh

# VHDL cross-check (needs ghdl and iverilog)
cd docs/errata/verification
python3 crosscheck.py normal                       # Normal mode, all codes. Must show 0 differences
python3 crosscheck.py static  --dut submitted      # shows the errors
python3 crosscheck.py static  --dut fixed          # must show only '='
python3 crosscheck.py dynamic --dut fixed
```

## 7. Folder contents

| Path | Content |
|------|---------|
| [workaround-guide.md](workaround-guide.md) | How to use the chip on the demo board. |
| `rtl/dyadic_fixed.v` | Corrected core (not in the submission). |
| `host/dyadic_host.py` | Host library (MicroPython and Python): pin layout, host-side dyadic, safe config write. |
| `host/example_board.py` | Four examples for the demo board. |
| `test/` | cocotb tests, Python model of the VHDL, host-library tests. |
| `verification/` | VHDL and Verilog benches and `crosscheck.py`. |

## 8. Rules for AI agents and maintainers

1. **`src/`, `test/` and `info.yaml` are frozen.** The chip is taped out. Do not change the RTL in `src/`
   to remove an error. A change cannot reach the silicon. A change would also make `src/` differ from the chip.
2. Put corrections in `rtl/dyadic_fixed.v`. Put workarounds in `host/dyadic_host.py`.
3. When you change `rtl/`, `host/` or `test/` here, run `docs/errata/test/run_checks.sh`. All checks must pass.
4. Keep the documents consistent with the errata list. Do not write that the chip "spreads the `+1` periods
   evenly", that dither modes average to `lsb/2^m`, or that the extra resolution is 7 bits for every width.
5. Do not claim that a workaround works on real silicon until a chip has been tested.
6. Do not edit `.github/workflows/*`. A change outside `docs/`, `README.md` and `.claude/` starts the
   expensive GDS and test workflows.
7. Write in simple technical English (ASD-STE100 style): short sentences, active voice, one
   instruction in each step, the same word for the same thing, no idioms.
