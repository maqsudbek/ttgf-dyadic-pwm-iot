# Session 03 — Harden / verify report (GF26a Dyadic PWM)

Goal: physically validate `tt_um_maqsudbek_dyadic_pwm` (tile-fit + timing) and finalize.

## Baseline (re-confirmed)
- `run-tests`: **10/10 PASS** (cocotb + Icarus), HEAD `0298d58`.
- `tt-compliance-check`: **clean** — top module `tt_um_maqsudbek_dyadic_pwm`, full 24-pin map,
  `uio_oe=0x00`/`uio_out=0x00` driven, `default_nettype none` + Apache SPDX in both srcs,
  `info.yaml` (top_module/source_files/tiles 1x1/clock_hz 50e6/yaml_version 6) consistent with
  `test/Makefile PROJECT_SOURCES`, tb instantiates the renamed top. `src/config.json` and
  `.github/workflows/*` untouched. (Soft nit only: the stock `<!--- ... -->` template comment
  block remains atop `docs/info.md`; harmless HTML comment, does not fail precheck.)

## Local hardening: not the right path on this host
- `local-harden` expects the devcontainer (`tt/` support-tools + LibreLane + GF180MCU PDK).
  On the bare OrangePi host none of that is installed and the host is **aarch64**, while the
  LibreLane/OpenROAD EDA stack is x86_64-first (the tool image *does* publish an arm64 variant,
  so it is technically runnable, but it is officially unsupported, multi-GB, and slow).
- Per the user's steer ("use the GitHub Action if it's better"), pivoted to the canonical
  **`gds` GitHub workflow** (`tt-gds-action@ttgf26a`, `pdk: gf180mcuD`, ubuntu-24.04 x86_64),
  which runs the *same* flow plus `precheck` and `gl_test` (gate-level timing). This is the
  authoritative tile-fit/timing gate for the shuttle.

## CI finding: gds workflow was failing BEFORE it ever hardened
- The repo is public; `gds` already ran on HEAD `0298d58` as run **#11** → **failure in ~12 s**.
- Job breakdown: `gds` job failed at the **"checkout repo"** step (`submodules: recursive`);
  `Build GDS` was **skipped**; `precheck`/`gl_test`/`viewer` skipped.
- Root cause: a stale **submodule gitlink** (mode `160000`, commit `65602b96…`) recorded in the
  index at `.claude/olddyadic/digital_dyadic_pwm` with **no `.gitmodules`**. `actions/checkout`
  tries to init the submodule, finds no URL, and aborts the whole checkout. The 27 real files
  exist on disk; the path had simply been committed as a nested repo in an earlier session.
  → **Not a design problem.** Tile-fit/timing were never actually exercised.

## Fix applied (this session, `.claude/`-only — submission set untouched)
- `git rm --cached .claude/olddyadic/digital_dyadic_pwm` then re-`git add` the directory so its
  27 files are tracked as normal files (gitlink gone, no more `160000` entries).
- Added `/tt/` to root `.gitignore` (locally-cloned TT support-tools, provided by devcontainer/CI).
- No change to `src/`, `info.yaml`, `test/`, `docs/`, `src/config.json`, or `.github/workflows/*`.

## Status / next step
- **Pending:** push the fix to `origin/test` to trigger a fresh `gds` run that can actually
  check out and harden. Then read run #12 (or later) for true 1×1 tile-fit + 50 MHz timing +
  `gl_test`. Local host has **no push credentials** (no `gh` auth, no token) — awaiting the
  user's auth method.
- Watch URL after push: <https://github.com/maqsudbek/ttgf-dyadic-pwm-iot/actions/workflows/gds.yaml>
