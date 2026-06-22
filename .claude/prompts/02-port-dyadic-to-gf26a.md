# Handoff Prompt 02 — Port Dyadic PWM into the GF26a template

This prompt starts the **first real development session**: port the Dyadic PWM generator into the
TinyTapeout GF26a template. The `.claude/` scaffolding (CLAUDE.md, docs, skills, MCP, settings,
reference index) was prepared in session 01 (see `.claude/plans/make-this-claude-valiant-forest.md`).

## Recommended session config
- **Model:** Opus 4.8 (`claude-opus-4-8`) — HDL porting + timing reasoning.
- **Thinking:** ON.
- **Effort/reasoning:** High.
- **Mode:** Start in **Plan mode** (produce a port plan from `.claude/docs/porting-notes.md`, save it
  to `.claude/plans/`), then switch to normal/Auto edit mode to implement.
- **Interface:** Claude Code CLI or VSCode extension — on first launch **approve the project MCP
  servers** (`markitdown`, `fetch`, `superpowers`) when prompted.

## Before you start (one-time, if not already done)
- Approve the MCP servers. Optionally confirm with `claude mcp list`.
- **Superpowers** is already wired as an MCP server in `.mcp.json` — no install needed. (Only if you
  also want the slash-command *plugin*: `/plugin marketplace add obra/superpowers-marketplace` then
  `/plugin install superpowers@superpowers-marketplace`.)
- Python test deps are already in the project **`.venv`** (`cocotb==2.0.1`, `pytest==8.4.2`); the
  only system install still needed for local sim is the simulator:
  `sudo apt-get install -y iverilog gtkwave`. Run tests via the `run-tests` skill (it activates
  `.venv` first). See `.claude/docs/tooling-setup.md` for details.

---

## Prompt to paste

> Read `.claude/CLAUDE.md` and `.claude/docs/porting-notes.md` first. We are now porting the
> **Dyadic PWM generator** into this **GF26a (GF180MCU)** TinyTapeout template. The working prior
> **IHP26a** Verilog port and the original **VHDL** source of truth are in `.claude/olddyadic/`
> (indexed in `.claude/olddyadic/README.md`; use the `dyadic-reference` skill). This is a real
> hardware submission — follow exactly what TinyTapeout expects for this shuttle.
>
> Scope for this session — **only the Dyadic PWM** (the two-wire IoT modulator/demodulator comes
> later). Do NOT edit `src/config.json` or `.github/workflows/*`.
>
> Plan, then implement:
> 1. Bring `dyadic.v` into `src/`; write `src/project.v` as the TT top wrapper named
>    `tt_um_<unique>` (include the author/project tag), instantiating the dyadic core.
> 2. Update `info.yaml`: `top_module`, `source_files`, `clock_hz` (decide the target clock — see
>    `.claude/docs/open-questions.md`; GF26a allows up to ~66.5 MHz), and the pinout descriptions
>    from the design doc.
> 3. Keep `test/Makefile` `PROJECT_SOURCES` in sync; adapt `test/tb.v` + `test/test.py` from the
>    prior port's working cocotb tests (mind the cocotb 2.x gotchas in the `run-tests` skill).
> 4. Fill `docs/info.md` (How it works / How to test / External hardware) from `dyadic_doc.md`.
> 5. Run the `run-tests` skill until green, then the `tt-compliance-check` skill. Optionally
>    `local-harden` before pushing.
>
> Decisions to confirm with me as they come up: target clock frequency; whether to re-add the
> selectable PWM widths / dithering modes from the VHDL or keep the simplified fixed-8-bit
> normal+dyadic port; and reserving pins for the future two-wire feature.
>
> AI artifacts/notes stay in `.claude/` only. When done, append outcomes to
> `.claude/docs/open-questions.md` and write the next handoff prompt to `.claude/prompts/`.

---

## Definition of done for session 02
- `run-tests` green; `tt-compliance-check` all pass; submission files (`src/`, `info.yaml`,
  `docs/info.md`, `test/`) complete and consistent; `src/config.json` & workflows untouched.
- Port plan saved in `.claude/plans/`; open questions updated.
