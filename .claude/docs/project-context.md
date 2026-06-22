# Project Context

## What this is
`ttgf-dyadic-pwm-iot` is a TinyTapeout submission built from the
[`ttgf-verilog-template`](https://github.com/TinyTapeout/ttgf-verilog-template) for shuttle **GF26a**.
The owner purchased a 1×1 digital tile plus a dev/demo board for this shuttle.

After the deadline, all GF26a projects are combined into
<https://github.com/TinyTapeout/tinytapeout-gf-26a>.

## Goal & scope
1. **Now:** port and adapt a **digital Dyadic PWM generator** into this template, validate with
   cocotb tests and the GDS flow.
2. **Later:** integrate a **two-wire data modulator/demodulator** for IoT into the same project
   (combined design). Out of scope until the dyadic PWM is solid.

## Lineage of the design (three generations)
1. **"Dyadic VHDL project"** — original, tested on a **DE1-SoC FPGA** in VHDL. Far larger than just
   the dyadic core (it included a digitally-controlled buck-converter PID loop and a Linux
   monitor/control framework around the DE1-SoC) — that surrounding system is **out of scope**.
   The key VHDL files are saved in `.claude/olddyadic/dyadic_vhdl/` (`dpwm.vhd`, `pwm_*.vhd`).
   This is the **behavioral source of truth** for the algorithm.
2. **"Old TinyTapeout project"** — a Verilog port for the prior **IHP26a** shuttle (from
   `ttihp-verilog-template`), verified green on CI. Saved in
   `.claude/olddyadic/digital_dyadic_pwm/`. Closest reference for the TT interface + cocotb tests.
3. **This project (GF26a)** — re-port/adapt the above into the GF180MCU template. See
   [porting-notes.md](porting-notes.md).

## Environment
- Hardware: **Orange Pi 5 Plus** SBC, **Debian 12 (bookworm) arm64**, kernel `6.1.43-rockchip-rk3588`.
- Workflow: developer's main machine is a **Windows 11 laptop** connected to the OrangePi via
  **VSCode Remote Explorer**; all work runs on the OrangePi. Both Claude Code **CLI** and the
  **VSCode extension** are used.
- `sudo` is available; installing system packages is authorized (ask for the password when needed).

## Target applications (why dyadic PWM)
DC-DC buck converter control, half-bridge motor drive (complementary outputs + dead-time),
high-resolution LED dimming, class-D audio.
