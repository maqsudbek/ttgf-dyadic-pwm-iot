# Handoff Prompt 03 — Harden, verify tile-fit, and finalize the GF26a Dyadic PWM

Session 02 **ported the full-feature Dyadic PWM** into the GF26a template and got the cocotb suite
**10/10 green**. This session is about **physical validation** (does it fit/close timing?) and
finalizing the submission. Plan of record:
[.claude/plans/02-port-dyadic-to-gf26a-plan.md](../plans/02-port-dyadic-to-gf26a-plan.md).

## Recommended session config
- **Model:** Opus 4.8 (`claude-opus-4-8`). **Thinking:** ON. **Effort:** High.
- **Mode:** normal/Auto edit. Approve project MCP servers (`markitdown`, `fetch`, `superpowers`) if prompted.
- `iverilog`/`gtkwave` are now installed; tests run via the `run-tests` skill (activates `.venv`).

## What exists now (session 02 result)
- Top module **`tt_um_maqsudbek_dyadic_pwm`** ([src/project.v](../../src/project.v)) wrapping core
  [src/dyadic.v](../../src/dyadic.v) (module `dyadic_pwm`).
- Features: selectable **5/6/7/8/9-bit** PWM; modes **Normal / Dyadic / Dither v1–v3**; **constant
  dyadic word**. Static config via a register file: `uio_in[7]`=run/config strobe, `uio_in[6:4]`=addr,
  `ui_in`=data (addr0=len+mode+const_flag, addr1=pwm_bits_sel, addr2=dyadic_word). 50 MHz, 513-cycle
  period, 6-cycle dead-time. All `uio` are inputs.
- `info.yaml`, `test/` (Makefile + tb.v + test.py), `docs/info.md` all updated and consistent.
  `src/config.json` and `.github/workflows/*` untouched.

## Prompt to paste

> Read `.claude/CLAUDE.md`, `.claude/plans/02-port-dyadic-to-gf26a-plan.md` and
> `.claude/docs/open-questions.md`. The full-feature Dyadic PWM is ported and `run-tests` is 10/10
> green. Now **validate it physically and finalize**:
>
> 1. Run the `local-harden` skill (LibreLane/GDS, GF180MCU). Confirm the design **fits the 1×1 tile**
>    and **closes timing at 50 MHz**, and re-confirm async-reset behaviour on GF cells.
> 2. **If it does NOT fit or close timing:** fall back to the **IHP fixed-8-bit normal+dyadic** design
>    (`.claude/olddyadic/digital_dyadic_pwm/`) — re-port it as `tt_um_maqsudbek_dyadic_pwm`, keep the
>    config interface only if it still fits, update tests/docs/info.yaml accordingly, and record the
>    decision. Ask me before trimming features if the call is close.
> 3. Re-run `run-tests` (and optionally gate-level `make GATES=yes` after hardening) and
>    `tt-compliance-check`. Everything must be green/clean.
> 4. Keep docs/artifacts organized under `.claude/`: save any hardening logs/reports into a dedicated
>    `.claude/` subfolder (e.g. `.claude/harden/`), update `.claude/CLAUDE.md` status,
>    `.claude/docs/open-questions.md`, and the plan. AI artifacts never enter the submission set.
> 5. Confirm with me the GitHub username in the top-module name before any push. When ready and I
>    approve, commit on a branch (not `main`) and push.
>
> Decisions to confirm with me: any feature trimming forced by tile-fit/timing; whether to start the
> **two-wire IoT modulator/demodulator** on leftover pins as the next milestone.

## Definition of done for session 03
- `local-harden` passes (1×1 fit + timing) **or** a documented, test-green fallback is in place.
- `run-tests` green; `tt-compliance-check` clean; submission set consistent; `config.json`/workflows
  untouched. Status + open-questions + plan updated; next handoff prompt written if work remains.
