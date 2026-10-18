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

## Result — gds run #12 (commit `847a0fc`, pushed by user): ALL GREEN
Run <https://github.com/maqsudbek/ttgf-dyadic-pwm-iot/actions/runs/27978501118>
- **gds (Build GDS)** ✓ — LibreLane placed, routed & wrote a valid GDS → **fits the 1×1 GF180MCU
  tile** (the flow errors on global-placement/congestion overflow if it does not).
- **precheck** ✓ — manufacturability gates pass: Magic/KLayout **DRC**, antenna, boundary, pin,
  power-pin, layer, cell-name, Verilog-syntax. (Verified the precheck source in `tt/precheck/
  precheck.py`: for `gf180mcuD` **there is no timing check in precheck** — it is purely physical.)
- **gl_test** ✓ — post-layout **gate-level netlist is functionally correct** vs the cocotb tb
  (functional/logical equivalence; TT GL test is not SDF-back-annotated, so it is not a timing check).
- **viewer / docs / test** ✓.

### What is NOT yet independently confirmed: STA timing slack at 50 MHz
- Official TT flow does **not hard-fail** the build on setup/hold violations — they are reported as
  warnings (`tt/tt_tool.py --print-warnings`); `src/config.json` even tells you to raise
  `CLOCK_PERIOD` "in case you are getting setup time violations." So a green Build GDS does **not by
  itself prove zero timing violations**. TT accepts the design regardless; the board clock is
  adjustable 1 Hz–66 MHz, so a marginal violation just means running below 50 MHz.
- The actual worst-slack numbers live in the **`GDS_logs`** (STA reports) and **`tt_submission`**
  (metrics) artifacts of run #12. Downloading GH artifacts needs auth even on a public repo, and the
  user chose the no-credentials path → **not inspected yet.** To verify truthfully, either the user
  downloads `GDS_logs`/`tt_submission` from the run page (one click, no token) and we read the STA
  summary / `tt_tool.py --print-warnings`, or grants `gh` read access. **Do not claim "timing
  closed" until this is read.**

## STA results — read from run #12 artifacts (gh auth, `GDS_logs/runs/wokwi/final/metrics.json`)
Post-PnR multi-corner STA (8 corners), clock period 20 ns (50 MHz):

| Item | Value |
|------|-------|
| Tile utilization | **45.5 %** (1146 std cells, die 55712 µm²) — fits 1×1 comfortably |
| Hold worst slack | **+0.52 ns**, 0 violations (all corners) |
| Setup — typical (nom_tt 25C/3.3V) | **+3.73 ns** ✓ meets 50 MHz |
| Setup — fast (nom_ff) | **+10.62 ns** ✓ |
| Setup — slow (nom_ss 125C/3.0V) | **−12.78 ns** ✗ (worst corner max_ss: **−13.22 ns**) |
| Setup violations | **52** reg→reg paths, **only in ss corners** (tt/ff = 0) |
| Max-slew / max-cap / max-fanout | 52 / 1 / 1 — slew vios all in ss corner, feed the same path |
| DRC / antenna / power-grid / LVS-pin | **0** violations |

**Critical path:** `dyadic_len[2]` reg → ~30 logic levels (the `scaled = duty·2^(9−B)+offset`
width-scaling datapath + dyadic-add + duty comparator) → `duty_compare` reg. Arrival 33.96 ns vs
20.74 ns required at the slow corner. It is a logic-**depth** problem, not a fit problem; the slow
corner + small-drive cells (slew) add the rest.

## Decision (user, session 03): accept typical-corner closure — do NOT pipeline
User's call: *"normal cases ok — good enough; very strange cases ok to fail."* The **normal case
(typical corner) closes 50 MHz with +3.7 ns margin**, so real silicon at room temp / nominal
voltage runs at 50 MHz; the slow-corner (125 °C, 3.0 V) failure is the accepted "strange case."
No RTL pipelining / feature trimming; **no fallback to the IHP fixed-8-bit design** (fit & features
are fine — only worst-corner Fmax is reduced). Submission RTL/`info.yaml` unchanged at 50 MHz; an
honest corner-derate note added to `docs/info.md` (guaranteed-all-corners Fmax ≈ 30 MHz).

## Bottom line
**Submission-ready.** TT's acceptance gate (fit + DRC + GL-functional) is green; the design runs
50 MHz under normal conditions and ≈30 MHz guaranteed across all corners. The only thing that was
*not* timing-clean is worst-corner setup, which is documented and, per the user, acceptable. If a
future session wants true all-corner 50 MHz: register the `scaled`/`duty_compare` datapath (it only
changes per control-word update / per 2^m window, so a 1–2 stage pipeline is functionally free).
