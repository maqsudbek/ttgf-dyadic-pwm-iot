---
name: local-harden
description: Run the LibreLane/GDS hardening flow locally for this GF180MCU TinyTapeout project to validate the design before pushing. Use when asked to harden, build GDS, run the ASIC flow, or check the design passes physical implementation. Heavy/optional.
---

# Local hardening (GDS) — GF180MCU

Builds the GDS locally with the same flow GitHub Actions uses, so you catch placement/timing/DRC
issues before relying on CI. This is **heavy** (large PDK download, long runtime) and optional —
the `gds` GitHub workflow does the same on push.

Official guide: <https://www.tinytapeout.com/guides/local-hardening/>

## Prereqs
- Docker (or the TT support tools env). The PDK here is **GF180MCU** (not sky130/IHP).
- The TT support tools provide a `tt_tool.py` harden entrypoint. The `.devcontainer/` in this repo
  sets up the expected environment.

## Typical flow
```bash
# inside the TT tools env / devcontainer
./tt/tt_tool.py --harden          # runs LibreLane on src/ using info.yaml + src/config.json
./tt/tt_tool.py --create-png      # optional render
```
Outputs land under `runs/` (gitignored). Inspect logs for GPL/DRC/timing errors.

## When it fails
- `GPL-0302` global placement → raise `PL_TARGET_DENSITY_PCT` in `src/config.json` (up to ~80).
- Setup violations → raise `CLOCK_PERIOD`.
- Hold violations → raise `PL_RESIZER_HOLD_SLACK_MARGIN` / `GRT_RESIZER_HOLD_SLACK_MARGIN`.

Only `CLOCK_PERIOD` (and the density/slack knobs above) should be touched in `config.json`; do not
restructure the file. Re-run `tt-compliance-check` afterward.
