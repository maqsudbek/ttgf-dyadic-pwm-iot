# Process Log — Dyadic PWM Generator

## 1. Module Restructuring
- Renamed `tt_um_dyadic_pwm` → `dyadic_pwm` in `src/dyadic.v`
- Rewrote `src/project.v` as TT top module `tt_um_dyadic_top`, instantiating `dyadic_pwm`
- Updated `test/tb.v` to reference `tt_um_dyadic_top`
- Updated `info.yaml`: top_module, source_files, pinout descriptions
- Updated `test/Makefile`: `PROJECT_SOURCES = project.v dyadic.v`

## 2. Design Review
- Verified all Verilog combinational paths have defaults (no latches)
- Added `` `default_nettype none`` to `dyadic.v`
- Confirmed async reset compatibility with IHP SG13G2 cells
- Traced PWM timing: 513-cycle period, 6-cycle dead-time, complementary outputs

## 3. Test Fixes (`test/test.py`)
- **cocotb 2.0.1 LogicArray TypeError**: `dut.uo_out.value & 0x01` and `dut.uo_out.value >> 2` fail with `TypeError: unsupported operand type(s) for &: 'LogicArray' and 'int'`. **Fix**: Wrap all signal reads with `int()` — e.g., `int(dut.uo_out.value) & 0x01`.
- **Clock parameter**: `units="ns"` (with 's') is deprecated in cocotb 2.0. Changed to `unit="ns"`.
- **test_reset**: Check during reset (rst_n=0) instead of after release. After release and 2 clock cycles, duty_compare latches to 1 (from formula 0*2+1), so pwm_high goes high — this is correct design behavior, not a fault.

## 4. Documentation Fix (`docs/info.md`)
- Replaced template placeholder text with actual project description
- Removed leftover template line: "List external hardware used in your project..."
- Required to pass the TT docs CI workflow

## Files Modified
- `src/project.v` — TT top wrapper
- `src/dyadic.v` — module rename + `default_nettype`
- `test/tb.v` — module reference
- `test/test.py` — full test rewrite + bug fixes
- `test/Makefile` — source file list
- `info.yaml` — metadata and pinout
- `docs/info.md` — project documentation

## Files NOT Modified (as required by TT submission)
- `.github/workflows/*.yaml`
- `src/config.json`

## 5. CI Verification (All Green)
- All 3 GitHub Actions workflows pass for commit 3ba374c:
  - **test #5** — 8/8 cocotb tests pass (Icarus Verilog + cocotb 2.0.1)
  - **docs #5** — Project datasheet generated
  - **gds #5** — Full ASIC flow completed (4 jobs: gds, precheck, gl_test, viewer)
- GDS artifacts: GDS_logs (7.6 MB), gatelevel_test_results (30.1 KB), gds_render (346 KB), github-pages (640 KB), precheck_reports (5.34 KB), tt_submission (432 KB)
- Only warnings: Node.js 20 deprecation (needs update by June 2026)

## 6. Deep Design Analysis — Dyadic PWM Hardware

### PWM Counter
- 10-bit counter (0–512), 513-cycle period → ~97.5 kHz at 50 MHz
- `sw_cycle_start` pulse at counter 512 triggers dyadic counter increment

### Dyadic Modulation — Mathematical Verification
The MSB-index approach is **mathematically exact**:
- For an N-bit counter, `find_msb_index_N` returns the position of the highest set bit
- Bit[k] of the LSB word is selected exactly 2^k times per 2^N-cycle period
- Counter == 0 is explicitly skipped (no addition)
- Over one full counter period: average addition = `LSB_value / 2^N`

Verified for 3-bit example (LSB = 5 = 101b):
```
Counter 0→skip, 1→bit[0]=1, 2→bit[1]=0, 3→bit[1]=0,
4→bit[2]=1, 5→bit[2]=1, 6→bit[2]=1, 7→bit[2]=1
Total: 5 additions / 8 cycles = 5/8 ✓
```

### Duty Cycle Scaling
- `duty_scaled = duty_saturated * 2 + 1` maps 0–255 to 1–511 within 513-cycle period
- Saturation at 255 prevents overflow from dyadic +1 when MSB is already 255
- Duty latched at counter == 0 (start of each PWM period) for glitch-free operation

### Dead-Time Analysis
- PWM_HIGH: ON from cycle 1 to `duty_compare`
- PWM_LOW: ON from cycle `duty_compare + DEAD_TIME + 1` to cycle `PWM_PERIOD - DEAD_TIME`
- Rising dead-time: 6 cycles (120 ns) — between HIGH off and LOW on
- Falling dead-time: 6 cycles (120 ns) — between LOW off and HIGH on (next period)
- MAX_DUTY = 505: if duty_compare > 505, LOW stays completely OFF (insufficient room for both dead-time gaps)

### Sync Clock
- 50%-ish square wave at PWM frequency (HIGH for 257 cycles, LOW for 256 cycles)
- Suitable for synchronizing external ADCs or control loops

### Design Strengths
- Correct dyadic theory implementation with exact fractional modulation
- Clean complementary outputs with symmetric dead-time
- Glitch-free duty update (latched at period start)
- Scalable dyadic length (2–7 bits → up to ~15-bit effective resolution)
- All combinational paths have defaults (no inferred latches)
- `default_nettype none` in both source files

## 7. Template Requirements Check
All Tiny Tapeout IHP26a template requirements satisfied:
- ✅ Top module `tt_um_dyadic_top` (starts with `tt_um_`)
- ✅ Standard 8-pin interface (ui_in, uo_out, uio_in/out/oe, ena, clk, rst_n)
- ✅ Source files listed in info.yaml: project.v, dyadic.v
- ✅ info.yaml version 6, 1×1 tile, all 24 pinout entries present
- ✅ docs/info.md filled: "How it works", "How to test", "External hardware"
- ✅ uio_oe = 0 (all bidirectional pins as inputs)
- ✅ Active-low async reset on `negedge rst_n`
- ✅ `ena` signal gating all logic
- ✅ Apache-2.0 license header in project.v

## 8. README.md Update
- Replaced template boilerplate with project-specific content
- Added: project title, overview table, pin mapping summary, dyadic algorithm explanation with example, project structure, test instructions
- Preserved: Tiny Tapeout description, resource links, badge references (removed FPGA badge — not applicable)
- Kept links to docs/info.md and added link to src/dyadic_doc.md
