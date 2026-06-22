---
name: run-tests
description: Run the cocotb/Icarus Verilog simulation testbench for this TinyTapeout project. Use when asked to run tests, simulate the design, or check the testbench passes.
---

# Run the testbench

The tests are cocotb + Icarus Verilog, driven by `test/Makefile`.

## Run
Tests need the project `.venv` active (it provides `cocotb-config`, which the Makefile calls):
```bash
source .venv/bin/activate
cd test
make            # default SIM=icarus; builds with iverilog and runs test.py
```
Results: `test/results.xml` (pass/fail), waveforms in `test/tb.fst` (open with `gtkwave`).
Clean rebuild: `make clean && make`. Gate-level sim: `make GATES=yes` (needs the GF180MCU PDK).

## Prerequisites
- Python deps live in the project **`.venv`** (already created): `cocotb==2.0.1`, `pytest==8.4.2`
  from `test/requirements.txt`. Recreate with `uv venv .venv --python 3.11 && uv pip install
  --python .venv -r test/requirements.txt` if missing.
- System sim tools (need sudo, install when first running tests):
  `sudo apt-get install -y iverilog gtkwave`.

## Keep in sync
- `test/Makefile` `PROJECT_SOURCES` must list every `src/*.v` file (e.g. `project.v dyadic.v`).
- `test/tb.v` must instantiate the current top module name (the `tt_um_...` wrapper).

## cocotb 2.x gotchas (these bit the prior port — see ../../olddyadic/digital_dyadic_pwm/process.md)
- **Wrap signal reads in `int(...)`**: `int(dut.uo_out.value) & 0x01`, not `dut.uo_out.value & 0x01`
  (LogicArray has no `&`/`>>` with ints).
- **Clock unit**: `Clock(dut.clk, 10, unit="ns")` — `unit=`, not the deprecated `units=`.
- **Reset checks**: assert behavior *during* reset (`rst_n=0`). After release, `duty_compare`
  latches to 1 (formula `0*2+1`) so `pwm_high` goes high — that's correct, not a fault.
