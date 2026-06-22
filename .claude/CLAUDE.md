# ttgf-dyadic-pwm-iot

A **Dyadic PWM generator** for **TinyTapeout GF26a** (GlobalFoundries **GF180MCU**, 1×1 digital tile).
Later goal: integrate a **two-wire data modulator/demodulator** for IoT into the same project.

## Status
**Ported (session 02).** Full-feature Dyadic PWM is in the submission set: top module
`tt_um_maqsudbek_dyadic_pwm` ([src/project.v](../src/project.v) wrapping core
[src/dyadic.v](../src/dyadic.v)). Implements selectable 5/6/7/8/9-bit PWM, Normal + Dyadic + 3
dithering modes + constant dyadic word, loaded via a config-register interface (`uio_in[7]` = run/config
strobe). `info.yaml`, `test/`, `docs/info.md` updated. Plan: [.claude/plans/02-port-dyadic-to-gf26a-plan.md](plans/02-port-dyadic-to-gf26a-plan.md).
**Hardened & verified (session 03).** `run-tests` = **10/10 green**; `tt-compliance-check` = **clean**;
**`gds` run #12 (commit `847a0fc`) = ALL GREEN** → **fits the 1×1 GF180MCU tile** (45.5% util), passes
**precheck** (DRC/antenna/pin/boundary) and **gl_test**. STA read via `gh` from run artifacts:
**typical & fast corners meet 50 MHz** (+3.7 / +10.6 ns), **slow corner fails** (−13.2 ns, 52 reg→reg
paths on the ~30-level width-scaling duty datapath); hold clean (+0.52 ns). **User decision:**
typical-corner 50 MHz is good enough, slow corner ok to fail — **no pipelining, no IHP fallback**;
`docs/info.md` carries an honest derate note (all-corner Fmax ≈ 30 MHz). `local-harden` was
impractical on this aarch64 host so CI is the gate; a stale submodule gitlink at
`.claude/olddyadic/digital_dyadic_pwm` (aborting checkout in run #11) was de-submoduled.
Details: [.claude/harden/03-harden-report.md](harden/03-harden-report.md).
Next milestone (not started): two-wire IoT modulator/demodulator on leftover pins.

## Hard constraints (TinyTapeout)
- Top module name must start with `tt_um_`; fixed interface: `ui_in[8]`, `uo_out[8]`,
  `uio_in/out/oe[8]`, `ena`, `clk`, `rst_n`. Assign **every** output (incl. `uio_oe`).
- 1×1 tile; PDK is **GF180MCU**. Clock comes from the board RP2040, **1 Hz – ~66.5 MHz**.
- **Do not edit** `src/config.json` or `.github/workflows/*` (TT compliance).
- `info.yaml` must list `top_module` + every `source_files` entry; keep `test/Makefile` `PROJECT_SOURCES` in sync.

## Conventions
- Put `` `default_nettype none `` at the top of every Verilog source.
- cocotb 2.x: wrap signal reads in `int(...)`; use `unit=` (not `units=`); for reset checks, assert
  *during* reset, not after release.
- **AI artifacts live only in `.claude/`** (docs, notes, downloads). Never add them to the submission set.
- MCP config is at **repo-root `.mcp.json`** (`markitdown`, `fetch`) — not `.claude/`
- sudo password when needed absolutely: `HomeServer543@#`

## Available project skills
`run-tests` · `tt-compliance-check` · `dyadic-reference` · `local-harden`

## Where to read more (load on demand)
- [.claude/docs/project-context.md](docs/project-context.md) — background, IoT scope, environment
- [.claude/docs/gf26a-constraints.md](docs/gf26a-constraints.md) — shuttle facts, clock, links
- [.claude/docs/porting-notes.md](docs/porting-notes.md) — IHP26a→GF26a port checklist + reference index
- [.claude/docs/open-questions.md](docs/open-questions.md) — running Q&A log
- [.claude/docs/tooling-setup.md](docs/tooling-setup.md) — MCP/plugin/toolchain install steps
- [.claude/plans/](plans/) · [.claude/prompts/](prompts/) — saved plans & session handoff prompts
