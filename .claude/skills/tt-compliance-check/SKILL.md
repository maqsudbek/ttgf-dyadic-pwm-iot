---
name: tt-compliance-check
description: Verify the project meets TinyTapeout submission requirements before committing or pushing. Use before commits, before pushing, or when asked if the design is submission-ready.
---

# TinyTapeout compliance checklist

Run through this before any commit/push. Fail = fix before proceeding.

## RTL / top module
- [ ] Top module name starts with `tt_um_` and is unique (include a username/project tag).
- [ ] Exact interface present: `ui_in[7:0]`, `uo_out[7:0]`, `uio_in[7:0]`, `uio_out[7:0]`,
      `uio_oe[7:0]`, `ena`, `clk`, `rst_n`.
- [ ] **Every** output assigned, including `uio_oe` and `uio_out` (drive unused to 0).
- [ ] `` `default_nettype none `` at the top of each `src/*.v`.
- [ ] No inferred latches (all combinational branches assign defaults).
- [ ] Apache-2.0 SPDX header in source files.

## Metadata / files
- [ ] `info.yaml`: `top_module` matches RTL; `source_files` lists every `src/*.v`; `tiles` set;
      `clock_hz` set; `yaml_version: 6`; pinout descriptions filled.
- [ ] `test/Makefile` `PROJECT_SOURCES` matches `info.yaml` `source_files`.
- [ ] `docs/info.md`: "How it works", "How to test", "External hardware" all filled (no template
      placeholder text).

## Do NOT edit (auto-fail / breaks the flow)
- [ ] `src/config.json` left as provided (only `CLOCK_PERIOD` may be tuned if justified).
- [ ] `.github/workflows/*.yaml` unchanged.

## Quick checks
```bash
grep -n "module tt_um_" src/*.v
git status --short src/ test/ docs/ info.yaml
git diff --stat src/config.json .github/   # expect: no output
```
Then run the `run-tests` skill — tests must pass.
