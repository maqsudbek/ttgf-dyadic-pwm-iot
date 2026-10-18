# Handoff Prompt 04 — Repo hygiene finish + start the two-wire IoT modem

The GF26a Dyadic PWM is **hardened and submitted from `main`** (typical-corner 50 MHz closes; slow
corner −13.2 ns accepted by the user — learning project). Session 03+ did most hygiene; this prompt
finishes it and opens the next design milestone. Plan of record:
[.claude/plans/03-finalize-hygiene-and-next-steps-plan.md](../plans/03-finalize-hygiene-and-next-steps-plan.md).

## Standing preferences (carry every session)
- **Token-efficient**: act when you have enough; don't re-derive or over-narrate.
- **Never fake test/CI results** — they're re-checked independently. Read real artifacts (`gh`).
- **`main` = clean submission only** (no `.claude/`, no `.mcp.json`). `test` = full dev superset.
- **Secrets** live only in `.claude/secrets.local.md` (gitignored). Never commit credentials.
- **CI is expensive**: keep `paths-ignore` on `gds`/`test`/`docs`; don't trigger hardening on
  `.claude/`, README, or tooling changes.
- `gh` is authenticated as `maqsudbek` (repo+workflow scope). GF180MCU, 1×1 tile, 50 MHz target.

## What was done in 03+ (verify, don't redo)
- `paths-ignore` added to gds/test/docs workflows; secret relocated; README rewritten; CLAUDE.md +
  open-questions + harden report updated; `docs/info.md` has the corner-derate + detailed results.
- Branch cleanup of `main` (remove `.claude/`+`.mcp.json`, gitignore them, port README/workflow
  improvements) — **confirm it landed on `main`** and that `main`'s tree is clean.

## Prompt to paste

> Read `.claude/CLAUDE.md` and `.claude/plans/03-finalize-hygiene-and-next-steps-plan.md`. Then:
> 1. **Verify `main` is clean**: no `.claude/` or `.mcp.json` in the `main` tree; README, workflow
>    `paths-ignore`, and `docs/info.md` detailed-results are present on `main`. Fix if not. Do **not**
>    wholesale-merge `test → main` (it drags `.claude` back) — promote submission files selectively.
> 2. **Finish docs** per plan §4 (porting-notes hardening outcome; trim/verify `test/README.md`;
>    optional datapath diagram).
> 3. **Start the two-wire IoT modem** (plan §5): propose pin budget on leftover pins, pick an encoding
>    (Manchester / UART-like / biphase), decide if it reuses the config register file, and write a
>    design plan before RTL. Confirm scope with me before implementing.
>
> Decisions to confirm with me: IoT encoding + pin map; whether to also pipeline the duty datapath
> for true all-corner 50 MHz (optional, plan "Optional future RTL").

## Definition of done
`main` tree clean and current; CI gating verified; docs complete; IoT modem scoped with a written
plan (and, if approved, RTL started with tests). Submission RTL untouched unless explicitly changed.
