# ttgf-dyadic-pwm-iot

A **Dyadic PWM generator** for **TinyTapeout GF26a** (GlobalFoundries **GF180MCU**, 1×1 digital tile).
Later goal: integrate a **two-wire data modulator/demodulator** for IoT into the same project.

## Status
**Ported (session 02).** Full-feature Dyadic PWM is in the submission set: top module
`tt_um_maqsudbek_dyadic_pwm` ([src/project.v](../src/project.v) wrapping core
[src/dyadic.v](../src/dyadic.v)). Implements selectable 5/6/7/8/9-bit PWM, Normal + Dyadic + 3
dithering modes + constant dyadic word, loaded via a config-register interface (`uio_in[7]` = run/config
strobe). `info.yaml`, `test/`, `docs/info.md` updated. Plan: [.claude/plans/02-port-dyadic-to-gf26a-plan.md](plans/02-port-dyadic-to-gf26a-plan.md).
- **Pending verification:** `run-tests` needs `iverilog` installed (`sudo apt-get install -y iverilog
  gtkwave`); static `tt-compliance-check` passes. **Tile-fit / timing not yet confirmed** — must run
  `local-harden`; if the full feature set doesn't fit the 1×1 GF180MCU tile, fall back to the IHP
  fixed-8-bit design in [.claude/olddyadic/](olddyadic/README.md).

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
