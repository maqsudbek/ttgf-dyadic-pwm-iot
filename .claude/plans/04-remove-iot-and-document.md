# Plan 04 — Drop the IoT milestone + write detailed user/architecture docs

**Date:** 2026-06-23 · **Branch flow:** work on `test`, then promote submission files to `main`
(no `.claude/` on `main`).

## Why
The owner has decided **not** to implement the future "two-wire data modulator/demodulator for IoT"
feature. The project is, and will remain, the **Dyadic PWM generator** only. We also want
thorough, standalone documentation of how the design works (block + detail level) and how to drive
it after tapeout on the TinyTapeout demo board.

## Asks (from the user)
1. Remove the two-wire / IoT milestone from README, docs, and CLAUDE.md(s).
2. Write good, detailed docs (multiple md files OK) covering both the *internals* (how each block
   works) and *usage* (how to operate it post-tapeout with the TT PCB dev board). Include diagrams.
3. Don't break anything TinyTapeout's shuttle expects (`config.json`, workflows, `info.yaml`
   `top_module`/`source_files`, `docs/info.md` as the datasheet).
4. Write this plan to a file.
5. Commit + push to `test`, then merge/promote to `main`, resolving conflicts; keep `.claude/` off
   `main`.
6. For vague choices, take the recommended TinyTapeout-official option; research official TT docs
   online where local knowledge is thin.

## Decisions taken (recommended defaults, no user round-trip needed)
- **Keep the git repo name** `ttgf-dyadic-pwm-iot` as-is — renaming the GitHub repo/remote is
  disruptive and out of scope; only *content* is scrubbed of the IoT milestone.
- **New docs live in `docs/`** (so they ship on `main` with the submission), not `.claude/`. They
  are user-facing.
  - `docs/info.md` stays the **TinyTapeout datasheet** (required; rendered by the `docs` workflow).
    Lightly cross-link to the new files; no IoT text (it already has none).
  - `docs/architecture.md` — internals: block diagram, datapath, every sub-block, the math, timing.
  - `docs/usage.md` — operating the chip on the TT demo board (MicroPython SDK / Commander),
    pin map, configuration walk-throughs, waveforms, half-bridge wiring.
- **Diagrams:** ASCII art (universally rendered on GitHub + the TT datasheet PDF). Mermaid is GitHub-
  only and may not render in the datasheet PDF, so prefer ASCII for portability.
- **Historical `.claude/` session artifacts** (prompts 01–04, plans 02–03, harden report) are dated
  records — left intact. Only the *live/forward-looking* `.claude` docs (CLAUDE.md, project-context,
  open-questions, porting-notes) get the IoT scope removed.

## Steps
1. **Research** official TT demo-board usage (done — get-started-demoboard + tt-micropython-firmware).
2. **Scrub IoT** from submission set: README.md (drop the "later milestone" sentence; point to docs).
3. **Scrub IoT** from live `.claude` docs: CLAUDE.md status/header/links, project-context goal/scope,
   open-questions, porting-notes "future two-wire" bullet.
4. **Write `docs/architecture.md`** — full internal description with ASCII diagrams.
5. **Write `docs/usage.md`** — post-tapeout operation with the TT demo board + bench/power wiring.
6. **Update README.md** — remove IoT, add a "Documentation" section linking architecture + usage.
7. **Sanity:** `run-tests` (unchanged RTL, should stay 10/10) + `tt-compliance-check`.
8. **Commit + push `test`.**
9. **Promote to `main`:** check out the submission files (README, docs/, info.yaml, src, test) from
   `test` onto `main` via a worktree/branch op — *not* a full merge (which would drag `.claude/`).
   Verify `main` tree has no `.claude/` / `.mcp.json`. Push `main`.

## Guardrails
- Do **not** edit `src/config.json` or `.github/workflows/*`.
- RTL (`src/*.v`) is unchanged — this is docs-only, so no `gds` re-harden is needed (and `gds`
  ignores `docs/**` + `README.md`).
- `info.yaml` `top_module` + `source_files` untouched.

## Definition of done
No IoT/two-wire promise anywhere in the live docs; `docs/architecture.md` + `docs/usage.md` present
and thorough with diagrams; tests still 10/10; compliance clean; `test` pushed; `main` updated with
the same submission docs and still free of `.claude/`.
