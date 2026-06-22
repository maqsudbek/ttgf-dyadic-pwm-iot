# Session 03+ Plan — Finalize, repo hygiene, CI cost control, next milestone

Plan of record after the GF26a Dyadic PWM was **hardened and submitted from `main`** (deadline cut;
learning project, current state accepted). Covers the user's five asks + the IoT milestone.

## Context / decisions locked
- **Submitted** from `main` as-is (typical-corner 50 MHz closes; slow corner −13.2 ns accepted).
- **Sudo password** that was committed to the public repo has been **rotated on the board** by the
  user → the leaked value is dead. Remaining work is *cleanliness/privacy*, not incident response.
- **`main` must stay clean of Claude-only files**: no `.claude/**`, no `.mcp.json`. `test` may carry
  everything (it is the superset/dev branch). The user is fine with `.claude/` on `test`.
- **CI is expensive** → don't trigger `gds`/`test`/`docs` on changes that can't affect the design.
- **Token-efficient workflow** is a standing preference.

## 1. CI cost control — DONE (verify on next push)
- Added `paths-ignore` to `.github/workflows/{gds,test,docs}.yaml` for `.claude/**`, `README.md`,
  `LICENSE`, `.gitignore`, `.vscode/**`, `.devcontainer/**`, `.mcp.json`. `fpga.yaml` already gated
  (`branches: none`). `docs/info.md` and `info.yaml` are **not** ignored, so the datasheet still
  rebuilds. Trade-off: TT ships stock workflows; `paths-ignore` doesn't change the build when it
  runs, so a future resubmission is unaffected — but if TT tooling ever rewrites the workflows,
  re-apply this.

## 2. Secret hygiene — DONE
- Moved the sudo password out of tracked `.claude/CLAUDE.md` into **`.claude/secrets.local.md`**
  (gitignored: `.claude/secrets.local.md`, `.claude/*.local.md`, `.claude/*.local.*`). CLAUDE.md now
  points there and forbids credentials in tracked files. (Agent can still read it → autonomy kept.)
- No git-history rewrite needed (password rotated). If ever desired for tidiness, `git filter-repo`
  + force-push would be required and only partially effective (GitHub caches commits).

## 3. Keep `main` clean of `.claude/` + `.mcp.json`  — branch strategy
Goal: public `main` tree shows **only** the submission; `test` keeps the full dev set.
**Chosen approach (agent maintains it; user does not need to manage the git dance):**
1. On `main`: `git rm -r --cached .claude .mcp.json` (whatever is tracked there), ensure `main`'s
   `.gitignore` lists `.claude/` and `.mcp.json`, commit, push. (Tree-level removal — satisfies
   "public shouldn't see `.claude` in main". History still contains it; not required to purge.)
2. Bring the submission-appropriate improvements made on `test` (README rewrite, workflow
   `paths-ignore`) onto `main` as well.
3. **Stop wholesale `test → main` merges** (that is what dragged `.claude` onto `main`). Promote
   submission changes selectively (agent cherry-picks / file-syncs non-`.claude` changes), or invert
   to merge `main → test` only. The agent handles promotions on request.
- Note: `.mcp.json` is already gitignored at repo root, but was committed to `main` earlier — must
  be `git rm --cached` on `main` to actually remove it from the tree.

## 4. Documentation overhaul (best-practice, readable) — IN PROGRESS
- **DONE:** root `README.md` rewritten (project overview, status table, realistic-Fmax note, layout).
  `.claude/CLAUDE.md` status + conventions (secrets, CI-gating, branch hygiene) updated.
  `.claude/harden/03-harden-report.md`, `.claude/docs/open-questions.md` carry full STA results.
- **TODO next session (keep on `test`/in-repo as appropriate):**
  - `docs/info.md` — already has the corner-derate note; optionally add a small block diagram.
  - `.claude/docs/porting-notes.md` — append the hardening outcome + critical-path finding.
  - Confirm `test/README.md` (TT stock) is accurate or trim.
  - Consider a short `docs/` architecture note (counter/scaler/dyadic-add datapath) for future-you.

## 5. Next milestone — two-wire IoT modulator/demodulator (NOT started)
- Map onto leftover pins (most `uio[]` are currently inputs; `uo_out[7:3]` are debug). Scope a
  simple two-wire (clock+data or self-clocked) modem: framing, mod/demod, and how it shares pins
  with the PWM config interface. Decide encoding (Manchester / UART-like / biphase) and whether it
  reuses the config register file. Re-budget pins, add tests, re-harden. This is a fresh design
  effort → its own plan + session.

## Optional future RTL: true all-corner 50 MHz
Register the `scaled`/`duty_compare` datapath (it only changes per control-word update / per `2^m`
window → ~free). Would close the slow corner with full features. Not needed for the current
(accepted) submission.

## Definition of done for the hygiene pass
`main` tree has no `.claude/`/`.mcp.json`; CI skips non-design changes; README/CLAUDE/docs current;
secret out of tracked files; next-session prompt written; submission RTL untouched.
