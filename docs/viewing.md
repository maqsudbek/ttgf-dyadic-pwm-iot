# Interactive viewing — schematic, layout, and waveforms

This guide is for **inspecting the design yourself** (as opposed to the pre-generated static
images in [`../pics/`](../pics/README.md)), the way you'd browse a PCB layout layer-by-layer or a
schematic in a PCB CAD tool. Use this while writing your tapeout report/paper to explore the
design and pick the exact views/crops you want, then export screenshots from the tools below.

All tools here are already installed in this repo's **devcontainer** (`.devcontainer/`). If you are
not using the devcontainer, install them locally with the commands noted per tool.

---

## 1. Physical layout (GDS) — KLayout

**What it is:** KLayout is a free, open-source IC layout viewer/editor — the direct equivalent of
opening a PCB layout in a PCB CAD tool. It lets you toggle individual mask layers on/off, zoom and
pan freely, measure distances, and (via a plugin) render a pseudo-3D extrusion of the layer stack.

**Install (already in devcontainer):**
```bash
sudo apt-get update && sudo apt-get install -y klayout
```

**Open the hardened GDS:**
```bash
# after running the local-harden flow (tt/tt_tool.py --harden), the GDS lands under runs/
klayout runs/wokwi/final/gds/tt_um_maqsudbek_dyadic_pwm.gds
```
(If you only have the CI-built artifacts, download the `gds` output from the `gds` GitHub Actions
run and point KLayout at that `.gds` file instead.)

**Useful KLayout features for your report:**
- **Layers panel** (usually docked on the right) — check/uncheck individual layers (metal1,
  metal2, poly, contacts, vias) to isolate exactly what you want in a screenshot, same as hiding
  copper layers in a PCB tool.
- **Ruler tool** — click-drag to measure distances (e.g. die dimensions, wire pitch).
- **`Tools → 3D View`** (KLayout ≥0.28, plugin may need enabling) — extrudes the layer stack for a
  pseudo-3D cross-section render.
- **File → Export → Image** — save the current view as a PNG at any zoom level for the paper.

This complements — it does not replace — the already-generated per-layer renders in
[`../pics/files/`](../pics/README.md#-physical-layout-gds), which were produced non-interactively
by [`../pics/render_gds_layers.py`](../pics/render_gds_layers.py) for exactly this purpose. Use
KLayout when you want to explore interactively or need a crop/angle the scripted renders don't
already cover.

---

## 2. Schematic (RTL / gate-level netlist) — Yosys `show` (already used) + viewers

The RTL and gate-level schematics in `pics/files/rtl-*.png` / `gate-schematic.*` were generated with
Yosys's `show` command piped to Graphviz. To regenerate or explore a different cut of the design
yourself:

```bash
yosys -p "read_verilog src/project.v src/dyadic.v; prep -top dyadic_pwm; show -format svg -prefix /tmp/rtl -notitle"
```
Open the resulting `.svg` in any vector viewer/browser tab to pan and zoom losslessly (SVGs stay
sharp at any zoom, unlike the PNGs). The post-layout gate netlist (2,252 instances) is too dense for
Graphviz — its raw `.dot` is at [`../pics/files/gate-schematic-pnl.dot`](../pics/files/); open that
in a `.dot`-capable graph viewer if you need to browse it interactively.

---

## 3. Place & route / floorplan — OpenROAD GUI

**What it is:** OpenROAD (the engine LibreLane drives during hardening) ships an interactive GUI for
floorplanning, placement density, routing congestion, and timing-path visualization — the closest
analogue to a PCB "place & route" viewer with per-layer toggling.

This requires having run the [`local-harden`](../.claude/skills/local-harden/SKILL.md) flow first
(inside the devcontainer, since it needs LibreLane + the GF180MCU PDK), so that intermediate
OpenROAD databases exist under `runs/`.

```bash
# inside the devcontainer, after tt/tt_tool.py --harden has produced runs/wokwi/...
openroad -gui
# then, in the OpenROAD Tcl console:
read_db runs/wokwi/<latest-run>/results/final/final.odb
```
From the GUI you can toggle metal layers, inspect placement density heat-maps, click a net to
highlight its route, and overlay timing paths — useful for report figures illustrating congestion
or the critical timing path (see the critical-path discussion in
[`../.claude/harden/03-harden-report.md`](../.claude/harden/03-harden-report.md)).

---

## 4. Simulation waveforms — GTKWave

The cocotb testbench (`test/tb.v`, `test/test.py`) dumps a waveform (`test/tb.fst`) every run. A
pre-configured save file with signals already grouped is provided at
[`../test/tb.gtkw`](../test/tb.gtkw).

```bash
cd test
make            # regenerates tb.fst by re-running the cocotb tests
gtkwave tb.fst tb.gtkw
```
In GTKWave you can add/remove signals, zoom to a specific switching period, drop measurement
cursors, and export the visible window as an image (`File → Write Trace/Image`, or a screenshot)
for the paper — the same static plot workflow used by
[`../pics/make_waveform.py`](../pics/make_waveform.py), but interactive and reproducible for any
signal/time range you choose.

---

## 5. Suggested report workflow

1. Use the pre-generated images in [`pics/files/`](../pics/README.md) as your baseline figures —
   they're scripted and reproducible.
2. Open the same underlying artifacts (GDS, `.fst` waveform, `.odb` database) in the interactive
   tools above whenever you need a different crop, angle, isolated layer set, or measurement that
   the static renders don't already show.
3. Export screenshots directly from KLayout / GTKWave / the OpenROAD GUI for anything custom, and
   keep them alongside (not necessarily inside) `pics/files/` unless you want them scripted too.
