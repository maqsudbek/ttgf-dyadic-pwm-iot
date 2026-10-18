# ttgf-dyadic-pwm-iot

A **Dyadic PWM generator** for **TinyTapeout GF26a** (GlobalFoundries **GF180MCU**, 1×1 digital tile).
Scope is the Dyadic PWM only — the previously-considered two-wire IoT modem was **dropped** (session 04).

## Status
**Silicon errata found (session 05) — design is taped out, `src/` is FROZEN.** A period-by-period
comparison with the original VHDL (GHDL vs Icarus, 420 cases) found errors E1–E7 in the dyadic/dither
modes and the config write. **Normal PWM is correct.** Workarounds (host-side), the corrected core
(`docs/errata/rtl/dyadic_fixed.v`), tests and docs live in [docs/errata/](../docs/errata/).
Agent summary + rules: [.claude/docs/errata.md](docs/errata.md); skill: `dyadic-errata`.
**Never edit `src/` to "fix" an erratum** (it cannot reach the silicon and would desync `src/` from the chip).

## Earlier status
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
**Docs finished (session 04).** The two-wire IoT milestone was **dropped** (will not be built);
IoT references removed from README/CLAUDE/live docs. Added detailed user docs:
[docs/architecture.md](../docs/architecture.md) (internals) + [docs/usage.md](../docs/usage.md)
(post-tapeout operation on the TT demo board). Plan:
[.claude/plans/04-remove-iot-and-document.md](plans/04-remove-iot-and-document.md).

## Hard constraints (TinyTapeout)
- Top module name must start with `tt_um_`; fixed interface: `ui_in[8]`, `uo_out[8]`,
  `uio_in/out/oe[8]`, `ena`, `clk`, `rst_n`. Assign **every** output (incl. `uio_oe`).
- 1×1 tile; PDK is **GF180MCU**. Clock comes from the board RP2 microcontroller (RP2350 on demo board v3), **1 Hz – ~66.5 MHz**.
- **Do not edit** `src/config.json` or `.github/workflows/*` (TT compliance).
- **`src/`, `test/`, `info.yaml` are frozen after tape-out.** Errata work goes in `docs/errata/` only.
- `info.yaml` must list `top_module` + every `source_files` entry; keep `test/Makefile` `PROJECT_SOURCES` in sync.

## Conventions
- Put `` `default_nettype none `` at the top of every Verilog source.
- cocotb 2.x: wrap signal reads in `int(...)`; use `unit=` (not `units=`); for reset checks, assert
  *during* reset, not after release.
- **AI artifacts live only in `.claude/`** (docs, notes, downloads). Never add them to the submission set.
- MCP config is at **repo-root `.mcp.json`** (`markitdown`, `fetch`) — not `.claude/`
- **Secrets:** never put credentials in tracked files. Machine-local secrets (incl. the sudo
  password) live in **`.claude/secrets.local.md`** (gitignored). Read it when a task truly needs
  sudo; never echo secret values into logs/commits/output.
- **CI is expensive:** the `gds`/`test`/`docs`/`fpga` workflows skip `.claude/**` and other
  non-design paths via `paths-ignore` — don't undo that. Changes confined to `.claude/`, README,
  or tooling must not trigger a hardening run.
- **Branch hygiene:** `main` = clean submission only (no `.claude/`). `test` = staging that may
  carry `.claude/`. Do not merge `.claude/` onto `main` (see the branch strategy in the active plan).
  `.gitignore` ignores `.claude/`; a **new** file there needs `git add -f` (tracked files are fine).
- **User-facing docs style (ASD-STE100, simplified):** short sentences (about 20 words), active voice,
  imperative steps with one action each, one term per thing, no idioms, no contractions. Keep `docs/`,
  `README.md` and `docs/info.md` consistent with the errata list (no "evenly spread", no "7 extra bits
  for every width", no "dither averages to lsb/2^m").
- **Errata checks:** `source .venv/bin/activate && cd docs/errata/test && ./run_checks.sh` (about 80 s).
  The VHDL cross-check (`docs/errata/verification/crosscheck.py`) needs `ghdl` (not installed on this host;
  it can be unpacked from the Debian `.deb` files without root — see `.claude/docs/errata.md`).

## Available project skills
`run-tests` · `tt-compliance-check` · `dyadic-reference` · `dyadic-errata` · `local-harden`

## Where to read more (load on demand)
- [.claude/docs/errata.md](docs/errata.md) — **errata summary, rules, commands** (read before touching dyadic/dither docs or tests)
- [docs/errata/README.md](../docs/errata/README.md) · [docs/errata/workaround-guide.md](../docs/errata/workaround-guide.md) — full errata + demo-board workarounds (user-facing)
- [.claude/docs/project-context.md](docs/project-context.md) — background, scope, environment
- [docs/architecture.md](../docs/architecture.md) · [docs/usage.md](../docs/usage.md) — internals + post-tapeout usage (user-facing)
- [.claude/docs/gf26a-constraints.md](docs/gf26a-constraints.md) — shuttle facts, clock, links
- [.claude/docs/porting-notes.md](docs/porting-notes.md) — IHP26a→GF26a port checklist + reference index
- [.claude/docs/open-questions.md](docs/open-questions.md) — running Q&A log
- [.claude/docs/tooling-setup.md](docs/tooling-setup.md) — MCP/plugin/toolchain install steps
- [.claude/plans/](plans/) · [.claude/prompts/](prompts/) — saved plans & session handoff prompts
