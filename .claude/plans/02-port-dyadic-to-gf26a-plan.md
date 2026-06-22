# Session 02 Plan — Port Dyadic PWM into GF26a (full-feature)

Plan of record for the port started by `.claude/prompts/02-port-dyadic-to-gf26a.md`.
(Approved copy also at `~/.claude/plans/ok-read-and-do-misty-iverson.md`.)

## Decisions (confirmed with user)
- **Clock:** 50 MHz → 513-cycle period (~97.466 kHz), 6-cycle (120 ns) dead-time.
- **Scope:** full VHDL feature set — 5/6/7/8/9-bit selectable PWM width, 3 dithering modes,
  Normal + Dyadic, **constant-dyadic-word** feature.
- **Pin strategy:** config register file written via write-strobe + addr + data; live 12-bit
  control word in run mode (`uio_in[7]` selects run vs config).
- **Out of scope:** multi-phase / x2 clock outputs; two-wire IoT modem (later session).
- **Tile-fit caveat (user):** full feature set is conditional on fitting the 1×1 GF180MCU tile.
  Confirmed only by `local-harden` GDS flow. If it does not fit/close timing, **fall back to the
  IHP fixed-8-bit normal+dyadic design** (`.claude/olddyadic/digital_dyadic_pwm/`).

## Architecture (area-optimized vs. the literal VHDL)
- **One shared 7-bit `dyadic_counter`** (not six): `sel_counter = dyadic_counter & ((1<<m)-1)`.
- Dyadic add bit collapses to `add = (sel_counter==0)?0 : src_word[hsb(sel_counter)]`
  where `hsb` = highest set bit; `src_word` = control LSBs or the constant `dyadic_word`.
  (Mathematically identical to the VHDL priority-encoder; verified against the 101→5/8 example.)
- **Uniform 513-cycle period** for all widths: `scaled = duty_B*factor + offset`,
  `factor = 1<<(9-B)`, `offset = max(1, factor>>1)`.
- Dead-time: HIGH on `cnt∈[1,scaled]`; LOW on `cnt∈(scaled+6, 507]` only when `scaled≤495`.

## Pin / config map
- RUN (`uio_in[7]=0`): `ui_in[7:0]=ctrl[11:4]`, `uio_in[3:0]=ctrl[3:0]`.
- CONFIG (`uio_in[7]=1`): `uio_in[6:4]=addr`, `ui_in[7:0]=data`
  - addr0: `data[2:0]`=dyadic_len, `data[5:3]`=dpwm_mode(0–4), `data[6]`=const_dyadic_flag
  - addr1: `data[2:0]`=pwm_bits_sel (0→5b…4→9b)
  - addr2: `data[6:0]`=dyadic_word
- Reset defaults: mode=Normal, dyadic_len=0, pwm_bits=8b, const_flag=0, word=0.
- Outputs: `uo[0]`=pwm_high, `uo[1]`=pwm_low, `uo[2]`=sync_clk, `uo[7:3]`=duty debug (9b-norm top bits).
  `uio_oe=0x00`, `uio_out=0x00`.

## Modes (`dpwm_mode`, forced Normal when dyadic_len=0)
0 Normal · 1 Dyadic (`src[hsb]`; src=const word if flag) · 2 Dither-v1 (`lsb≥cnt`) ·
3 Dither-v2 (lsb sampled at cnt==1) · 4 Dither-v3 (lsb+msb sampled at cnt==1).

## Files (submission set)
`src/dyadic.v` (core `dyadic_pwm`), `src/project.v` (`tt_um_maqsudbek_dyadic_pwm`),
`info.yaml`, `test/Makefile` (`PROJECT_SOURCES=project.v dyadic.v`), `test/tb.v` (keep GF GL ports,
rename instance), `test/test.py` (extend), `docs/info.md`. **Never touch** `src/config.json`,
`.github/workflows/*`.

## Verification
`run-tests` green → `tt-compliance-check` clean → `local-harden` (tile fit / timing; decides fallback).

## Artifacts / docs maintenance
- Plans → `.claude/plans/`. Any generated artifacts → dedicated `.claude/` subfolders.
- On completion update: `.claude/CLAUDE.md` status, `.claude/docs/open-questions.md`,
  `.claude/docs/porting-notes.md`; write next handoff prompt to `.claude/prompts/`.
