---
name: local-harden
description: Run the LibreLane/GDS hardening flow locally for this GF180MCU TinyTapeout project to validate the design before pushing. Use when asked to harden, build GDS, run the ASIC flow, or check the design passes physical implementation. Heavy/optional.
---

# Local hardening (GDS) — GF180MCU

Builds the GDS locally with the same flow GitHub Actions uses, so you catch placement/timing/DRC
issues before relying on CI. This is **heavy** (large PDK download, long runtime) and optional —
the `gds` GitHub workflow does the same on push.

Official guide: <https://www.tinytapeout.com/guides/local-hardening/>

## Prereqs (use the devcontainer)
- The intended environment is this repo's **`.devcontainer/`** (docker-in-docker, 10 GB). On start it
  runs `copy_tt_support_tools.sh`, which provides the **`tt/`** support-tools dir (so `tt/tt_tool.py`
  exists). On the bare OrangePi host there is no `tt/` until you set the support tools up.
- Local hardening needs **LibreLane** installed; PDK is **GF180MCU** (`gf180mcuD`), not sky130/IHP.

## Flow
The TT docs state: *"if you have LibreLane installed locally, you can harden the design with
`--harden`"* — confirmed flag; other `tt_tool.py` subcommands exist (datasheet/SVG/PNG renders,
config) but check `tt/tt_tool.py --help` for exact names rather than guessing.
```bash
# inside the devcontainer / TT tools env
tt/tt_tool.py --help     # discover available subcommands first
tt/tt_tool.py --harden   # runs LibreLane on src/ using info.yaml + src/config.json
```
Outputs land under `runs/` (gitignored). Inspect logs for GPL/DRC/timing errors.
On push, the `gds` GitHub workflow (`tt-gds-action@ttgf26a`, `pdk: gf180mcuD`) runs the same flow.

## When it fails
- `GPL-0302` global placement → raise `PL_TARGET_DENSITY_PCT` in `src/config.json` (up to ~80).
- Setup violations → raise `CLOCK_PERIOD`.
- Hold violations → raise `PL_RESIZER_HOLD_SLACK_MARGIN` / `GRT_RESIZER_HOLD_SLACK_MARGIN`.

Only `CLOCK_PERIOD` (and the density/slack knobs above) should be touched in `config.json`; do not
restructure the file. Re-run `tt-compliance-check` afterward.
