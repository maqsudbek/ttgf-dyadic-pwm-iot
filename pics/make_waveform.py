#!/usr/bin/env python3
"""Generate waveform plot from cocotb simulation.
Re-runs the testbench briefly to collect VCD data, then plots key signals.
"""

import subprocess, os, sys

OUT_DIR = os.path.join(os.path.dirname(__file__), "files")

# Step 1: Re-run simulation to get fresh VCD
print("Re-running simulation...")
os.chdir(os.path.join(OUT_DIR, "..", "..", "test"))
result = subprocess.run(
    ["make", "sim"],
    capture_output=True, text=True, timeout=60,
    env={**os.environ, "SIM": "icarus"}
)
print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)

# Step 2: Check for VCD file
vcd_path = "sim_build/rtl/dump.vcd"
fst_path = "../test/tb.fst"
os.chdir(os.path.join(OUT_DIR, "..", "..", "test"))

# Use fst2vcd if available
vcd_ok = False
if os.path.exists(fst_path):
    print(f"FST found: {fst_path}")
    try:
        subprocess.run(["fst2vcd", fst_path, vcd_path], capture_output=True, timeout=30)
        if os.path.exists(vcd_path):
            vcd_ok = True
            print(f"Converted FST → VCD: {vcd_path}")
    except Exception as e:
        print(f"fst2vcd failed: {e}")

# Step 3: Parse VCD and plot
if vcd_ok or os.path.exists(vcd_path):
    print("Parsing VCD...")
    # Simple VCD parser for key signals
    signals = {}
    current_time = 0
    with open(vcd_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("$var"):
                parts = line.split()
                if len(parts) >= 5:
                    code = parts[3]
                    name = parts[4]
                    signals[code] = {"name": name, "values": []}
            elif line.startswith("#") and line[1:].isdigit():
                current_time = int(line[1:])
            elif len(line) >= 2 and line[0] in "01bxz":
                val = line[0]
                code = line[1:]
                if code in signals:
                    signals[code]["values"].append((current_time, val))

    # Plot with matplotlib
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Filter to interesting signals
    interesting = ["clk", "rst_n", "uo_out[0]", "uo_out[1]", "uio_out[0]"]
    plot_sigs = {}
    for code, info in signals.items():
        name = info["name"]
        for pat in interesting:
            if pat in name or name in interesting:
                if info["values"]:
                    plot_sigs[name] = info["values"]
                break

    if not plot_sigs:
        # Fallback: plot first 4 signals with data
        for code, info in list(signals.items())[:5]:
            if info["values"]:
                plot_sigs[info["name"]] = info["values"]

    if plot_sigs:
        n = len(plot_sigs)
        fig, axes = plt.subplots(n, 1, figsize=(12, 3*n), sharex=True,
                                 facecolor="#0d1117")
        if n == 1:
            axes = [axes]

        for ax, (name, vals) in zip(axes, plot_sigs.items()):
            times = [t for t, _ in vals]
            values = [1 if v == "1" else 0 for _, v in vals]
            ax.step(times, values, where="post", color="#33aa66", linewidth=1)
            ax.set_ylabel(name, color="white", fontsize=8, family="monospace")
            ax.set_facecolor("#0d1117")
            ax.tick_params(colors="#888888", labelsize=7)
            ax.set_ylim(-0.1, 1.3)
            ax.grid(True, alpha=0.2, color="#ffffff")

        axes[-1].set_xlabel("Time (simulation units)", color="#888888", fontsize=8)
        fig.suptitle("Dyadic PWM — Simulation Waveform", color="white",
                     fontsize=12, fontweight="bold", y=0.98)
        fig.tight_layout(pad=0.5)

        out_path = os.path.join(OUT_DIR, "waveform.png")
        fig.savefig(out_path, dpi=150, facecolor="#0d1117", edgecolor="none")
        plt.close(fig)
        print(f"Waveform PNG: {out_path}")
    else:
        print("No signal data found in VCD")
else:
    print("No VCD available — creating placeholder")
    # Create a simple placeholder waveform
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots(figsize=(12, 4), facecolor="#0d1117")
    ax.set_facecolor("#0d1117")

    t = np.linspace(0, 100, 1000)
    ax.step(t, (np.sin(t/5) > 0).astype(int), where="post", color="#3355cc", label="clk")
    ax.step(t, (np.sin(t/20 + 1) > 0.3).astype(int), where="post", color="#cc6633", label="pwm_out")
    ax.set_ylim(-0.1, 1.3)
    ax.legend(loc="upper right", facecolor="#1a1a2e", labelcolor="white",
              fontsize=8)
    ax.tick_params(colors="#888888")
    ax.set_title("Waveform (placeholder — run 'cd test && make' for real data)",
                 color="white", fontsize=10)
    ax.grid(True, alpha=0.2, color="#ffffff")

    out_path = os.path.join(OUT_DIR, "waveform.png")
    fig.savefig(out_path, dpi=150, facecolor="#0d1117", edgecolor="none")
    plt.close(fig)
    print(f"Placeholder waveform: {out_path}")

print("✅ Phase 4 complete")
