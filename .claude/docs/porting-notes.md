# Porting Notes: IHP26a → GF26a

Goal: bring the working IHP26a Verilog port (`.claude/olddyadic/digital_dyadic_pwm/`) into this
GF180MCU template, keeping the algorithm from the VHDL source of truth
(`.claude/olddyadic/dyadic_vhdl/`). See [.claude/olddyadic/README.md](../olddyadic/README.md) for the file map.

> **Status (session 02): ported & test-green (10/10).** The port went *beyond* the IHP fixed-8-bit
> simplification — it re-adds the full VHDL feature set (selectable 5/6/7/8/9-bit width, 3 dithering
> modes, constant dyadic word) behind a config-register interface. Details + decisions in
> [02-port-dyadic-to-gf26a-plan.md](../plans/02-port-dyadic-to-gf26a-plan.md) and
> [open-questions.md](open-questions.md). Still to do: `local-harden` to confirm 1×1 tile fit / timing;
> fall back to fixed-8-bit if it doesn't fit. The checklist below is the original IHP→GF recipe (kept
> for reference / fallback).

## What changes between shuttles
| Aspect | IHP26a (old port) | GF26a (this project) |
|--------|-------------------|----------------------|
| PDK | IHP SG13G2 | **GF180MCU** |
| Template | `ttihp-verilog-template` | `ttgf-verilog-template` |
| `src/config.json` | IHP defaults | **GF defaults — leave as provided, only adjust `CLOCK_PERIOD` if needed** |
| `.github/workflows/*` | IHP flow | GF flow (already in repo — **do not edit**) |
| Async reset | confirmed OK on SG13G2 cells | re-confirm on GF180MCU cells during hardening |

The **Verilog logic is process-agnostic** — the dyadic core should port largely unchanged. The
deltas are in the build/PDK config and timing closure, not the RTL.

## Port checklist
1. Copy `dyadic.v` into `src/`; rewrite `src/project.v` as the TT top wrapper
   (`tt_um_<unique>` instantiating `dyadic_pwm`). Old wrapper used `tt_um_dyadic_top`.
2. `` `default_nettype none `` in every source.
3. `info.yaml`: set `top_module`, `source_files: [project.v, dyadic.v]`, `clock_hz`, pinout
   descriptions (see `dyadic_doc.md` pin table). Keep `yaml_version: 6`.
4. `test/Makefile`: `PROJECT_SOURCES = project.v dyadic.v`.
5. `test/tb.v` + `test/test.py`: reference the new top module; reuse the working cocotb tests from
   the old port. Mind cocotb 2.x gotchas (see `run-tests` skill).
6. `docs/info.md`: fill "How it works / How to test / External hardware" (port from `dyadic_doc.md`).
7. Run `run-tests`, then `tt-compliance-check`, then optionally `local-harden` before pushing.

## Design recap (full detail in dyadic_doc.md)
- 12-bit control split: `ui_in[7:0]` = MSB[11:4], `uio_in[3:0]` = LSB[3:0].
- `uio_in[6:4]` = dyadic length (0/normal, 2–7); `uio_in[7]` = mode (0 normal / 1 dyadic).
- Outputs: `uo_out[0]` PWM_HIGH, `[1]` PWM_LOW (complementary, dead-time), `[2]` sync clk, `[7:3]` duty MSBs.
- 8-bit base PWM; dyadic adds a +1 sequence (MSB-index of an N-bit counter selects an LSB bit)
  for up to ~15-bit effective resolution. 513-cycle period, 6-cycle dead-time at 50 MHz → ~97.5 kHz.
- The original VHDL also had 5/6/7/8/9-bit selectable PWM + 3 dithering modes + multi-phase clocks;
  the TT port simplified to fixed 8-bit + normal/dyadic only. Revisit if I/O budget allows.

## Open design decisions for the port
- Final `clk` frequency on GF26a (affects switching freq + `clock_hz`/`CLOCK_PERIOD`).
- Whether to re-add any dithering modes or selectable PWM width now that this is a fresh start.
- Where the future two-wire modulator/demodulator maps onto remaining pins.
