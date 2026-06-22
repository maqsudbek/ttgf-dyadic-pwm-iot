# ttgf-dyadic-pwm-iot

A **Dyadic PWM generator** for **TinyTapeout GF26a** (GlobalFoundries **GF180MCU**, 1×1 digital tile).
Later goal: integrate a **two-wire data modulator/demodulator** for IoT into the same project.

## Status
The repo is still the untouched `tt_um_example` template (`src/`, `info.yaml`, `docs/info.md`, `test/`).
The real design is **not yet ported**. A working prior port and the original source live in
[.claude/olddyadic/](olddyadic/README.md) — that is the starting point for development.

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
- MCP config is at **repo-root `.mcp.json`** (`markitdown`, `fetch`) — not `.claude/`.

## Available project skills
`run-tests` · `tt-compliance-check` · `dyadic-reference` · `local-harden`

## Where to read more (load on demand)
- [.claude/docs/project-context.md](docs/project-context.md) — background, IoT scope, environment
- [.claude/docs/gf26a-constraints.md](docs/gf26a-constraints.md) — shuttle facts, clock, links
- [.claude/docs/porting-notes.md](docs/porting-notes.md) — IHP26a→GF26a port checklist + reference index
- [.claude/docs/open-questions.md](docs/open-questions.md) — running Q&A log
- [.claude/docs/tooling-setup.md](docs/tooling-setup.md) — MCP/plugin/toolchain install steps
- [.claude/plans/](plans/) · [.claude/prompts/](prompts/) — saved plans & session handoff prompts
