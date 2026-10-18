# Reference Material Index (`.claude/olddyadic/`)

Read-only reference for porting the Dyadic PWM into this GF26a project. **Nothing here is part of
the TT submission.** Pull the single file you need rather than scanning the whole tree.
See also the `dyadic-reference` skill and [../docs/porting-notes.md](../docs/porting-notes.md).

## `digital_dyadic_pwm/` — prior IHP26a Verilog port (CI-green)
Closest reference for the TT interface and tests.
- `src/dyadic.v` — **main Verilog source** of the dyadic PWM core (module `dyadic_pwm`).
- `src/project.v` — TT top wrapper (`tt_um_dyadic_top`) instantiating `dyadic_pwm`.
- `src/dyadic_doc.md` — **full design doc**: algorithm, pin map, modes, timing, examples, block diagram.
- `src/tiny_tapeout_info.md` — TT top-module interface + demoboard explainer.
- `process.md` — change log from the IHP port: module restructuring, cocotb 2.x test fixes,
  design analysis, and the template-compliance checklist (very useful for redoing the port).
- `test/` — working cocotb testbench (`tb.v`, `test.py`), `Makefile`, requirements.
- `info.yaml`, `docs/info.md`, `README.md` — filled-in IHP versions to mirror for GF26a.
- `.github/workflows/`, `.devcontainer/` — IHP build setup (reference only; GF repo has its own).

## `dyadic_vhdl/` — original DE1-SoC VHDL (behavioral source of truth)
- `dpwm.vhd` — top dyadic/dithering controller: 5/6/7/8/9-bit selectable PWM, normal + dyadic +
  3 dithering modes, constant-vs-control dyadic word. The TT port simplified this.
- `pwm_97466hz.vhd`, `pwm_500khz.vhd`, `pwm_1mhz.vhd` — complementary PWM generators at various
  switching frequencies (multi-phase/early clock outputs).

## Generation lineage
DE1-SoC VHDL (`dyadic_vhdl/`) → IHP26a Verilog port (`digital_dyadic_pwm/`) → **this GF26a project**.
