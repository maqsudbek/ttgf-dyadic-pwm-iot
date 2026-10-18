![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg) ![](../../workflows/fpga/badge.svg)

# Dyadic PWM generator — TinyTapeout GF26a (`tt_um_maqsudbek_dyadic_pwm`)

A configurable **digital PWM (DPWM) generator** with **dyadic modulation** and **dithering**,
hardened for the **TinyTapeout GF26a** shuttle on the GlobalFoundries **GF180MCU** PDK (single
1×1 digital tile).

- **Top module:** `tt_um_maqsudbek_dyadic_pwm` ([src/project.v](src/project.v)) wrapping the core
  `dyadic_pwm` ([src/dyadic.v](src/dyadic.v)).
- **Datasheet:** [docs/info.md](docs/info.md) · **Architecture:** [docs/architecture.md](docs/architecture.md) · **Usage guide:** [docs/usage.md](docs/usage.md).
- **PDK / tile:** GF180MCU (`gf180mcuD`), 1×1 tile. **Clock:** board RP2 microcontroller, 1 Hz – ~66 MHz.

> ## ⚠️ Known silicon errata — read this before you use the chip
>
> The chip is already made. The original VHDL runs on an FPGA. A period-by-period comparison with the VHDL
> found differences in the **dyadic and dither modes**. It also found a weakness in the **config write**.
> **Plain Normal PWM (5 to 9 bits) is correct.** The workarounds are tested in simulation only.
>
> | ID | Problem | Workaround on the demo board |
> |----|---------|------------------------------|
> | **E2** | The chip reads the fraction from the **lowest** control bits. The VHDL reads the bits below the base duty. A VHDL-style wiring gives wrong values. | Put the fraction in `control[m-1:0]`. Use `m ≤ 12 − bits`. |
> | **E6** | A config register is written at **every** clock edge while `uio_in[7] = 1`. | Stop the clock. Write with one single step. |
> | **E1** | The dyadic `+1` periods come in blocks. The average is correct. The ripple is larger. | Run the dyadic modulation in the host (chip in Normal mode). |
> | **E3** | Dither modes add `(lsb+1)/2^m`. | Use dyadic mode, or write `value − 1` as the control word. |
> | E4, E5, E7 | Overlap of the fraction with the base duty, constant word with `m = 1`, small timing differences. | See the errata list. |
>
> - **Step-by-step guide for the demo board:** [docs/errata/workaround-guide.md](docs/errata/workaround-guide.md)
> - **Errata list, causes, numbers:** [docs/errata/README.md](docs/errata/README.md)
> - **Corrected design (what the chip should have been), tests and host library:** [docs/errata/](docs/errata/)
> - **For AI agents and maintainers:** `src/` is frozen (taped out). Do not "fix" it. See
>   [the rules in docs/errata/README.md](docs/errata/README.md#8-rules-for-ai-agents-and-maintainers).

## What it does

| Feature | Detail |
|---|---|
| **Selectable resolution** | 5 / 6 / 7 / 8 / 9-bit PWM, all on a uniform **513-cycle** period |
| **Modes** | Normal · Dyadic · Dither v1 / v2 / v3 · constant-dyadic-word |
| **Outputs** | complementary high/low side with **6-cycle (120 ns) dead-time**, sync clock, duty debug |
| **Config** | small register file over the pins (`uio_in[7]` = run/config strobe) |

Dyadic mode distributes the lower `m` bits of the control word as a `+1` sequence across a
`2^m`-period window, raising the *effective* resolution by up to `12 − B` bits (7 bits at 5-bit
PWM, 4 bits at 8-bit PWM) without widening the base counter. See the errata above for the exact
behaviour of the built chip.

## Documentation

| Document | What's in it |
|---|---|
| [docs/info.md](docs/info.md) | TinyTapeout **datasheet** — pin map, config registers, how-to-test, post-layout results |
| [docs/architecture.md](docs/architecture.md) | **How it works inside** — block diagram, datapath, every sub-block, the duty-scaling math, the critical path |
| [docs/usage.md](docs/usage.md) | **How to drive it after tapeout** — TinyTapeout demo board (MicroPython/Commander), config recipes, waveforms, half-bridge wiring |
| [docs/errata/README.md](docs/errata/README.md) | **Errata** — what differs from the VHDL, causes, numbers, how it was checked |
| [docs/errata/workaround-guide.md](docs/errata/workaround-guide.md) | **Workaround guide** — safe start, pin layout, host-side dyadic modulation, recipes A to D |

## Implementation status

**Ported, tested, and hardened** (sign-off via the TinyTapeout `gds` CI on x86_64).

| Check | Result |
|---|---|
| Functional sim (`run-tests`, cocotb/Icarus) | ✅ 10 / 10 (averages only — they do not find errata E1 to E6) |
| TT compliance | ✅ clean |
| `gds` Build (LibreLane, GF180MCU) — tile fit | ✅ **fits 1×1**, 45.5 % utilization |
| `precheck` (DRC / antenna / pin / boundary) | ✅ 0 violations |
| `gl_test` (gate-level functional) | ✅ pass |
| Hold timing (all corners) | ✅ +0.52 ns |
| Setup @ 50 MHz — typical / fast corner | ✅ +3.7 / +10.6 ns |
| Setup @ 50 MHz — slow corner (125 °C, 3.0 V) | ⚠️ **−13.2 ns** (see below) |

### Realistic operating expectation
The design **closes 50 MHz at the typical and fast process corners**, so silicon at normal
temperature/voltage is expected to run at the rated **50 MHz**. The longest path — the width-scaled
duty computation — does **not** meet 50 MHz at the worst-case slow corner; for operation guaranteed
across **all** corners, run at roughly **≤ 30 MHz**. The RP2 microcontroller supplies the clock and is adjustable
(1 Hz – ~66 MHz); the PWM switching frequency is `clk / 513` (≈ 97.5 kHz at 50 MHz, scaling with the
clock). Hold is met everywhere.

## Repository layout

| Path | Purpose |
|---|---|
| `src/` | RTL (`project.v` top wrapper, `dyadic.v` core) + `config.json` (LibreLane) — submission set |
| `test/` | cocotb testbench (`tb.v`, `test.py`, `Makefile`) |
| `docs/` | datasheet (`info.md`), architecture (`architecture.md`), usage guide (`usage.md`) |
| `docs/errata/` | errata, workaround guide, corrected core (`rtl/`), host library (`host/`), errata tests (`test/`), VHDL cross-check (`verification/`) |
| `docs/dyadic_vhdl/` | the original FPGA VHDL (reference) |
| `info.yaml` | TinyTapeout metadata (top module, sources, pinout, clock) |
| `.github/workflows/` | TT CI (`gds`, `test`, `docs`, `fpga`) |

## Build & test locally

```bash
# functional simulation (needs iverilog; uses the project .venv for cocotb)
source .venv/bin/activate && cd test && make

# full GDS hardening runs in CI on push (TinyTapeout/tt-gds-action, pdk gf180mcuD).
# Local hardening needs LibreLane + the GF180MCU PDK (x86_64).
```

## About TinyTapeout
TinyTapeout is an educational project that makes it cheap and easy to get a custom digital/analog
design manufactured on a real chip — <https://tinytapeout.com>. See the
[FAQ](https://tinytapeout.com/faq/) and [local-hardening guide](https://www.tinytapeout.com/guides/local-hardening/).

## License
Apache-2.0 — see [LICENSE](LICENSE).
