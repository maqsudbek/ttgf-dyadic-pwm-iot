#!/usr/bin/env python3
"""Block diagram renderers for the Dyadic PWM — all 3 approaches.
1. Mermaid (via mermaid.ink HTTP API)
2. Python/matplotlib boxes-and-arrows
3. Hand-crafted SVG
Outputs to pics/files/ directory.
"""

import os, sys, json
import urllib.request, urllib.parse
import base64, zlib

OUT_DIR = os.path.join(os.path.dirname(__file__), "files")

# ============================================================
# 1. Mermaid diagram definition
# ============================================================

MERMAID_DIAGRAM = """
graph TB
    subgraph "TinyTapeout Interface (34 pins)"
        CLK[clk] --> DPWM
        RST[rst_n] --> DPWM
        ENA[ena] --> DPWM
        UI[ui_in 7:0] --> DPWM
        DPWM --> UO[uo_out 7:0]
        DPWM --> UIO[uio_out 7:0]
    end

    subgraph "tt_um_maqsudbek_dyadic_pwm (project.v)"
        DPWM[dyadic_pwm core]
    end

    subgraph "dyadic_pwm (dyadic.v)"
        direction TB
        CONFIG[Config Register File<br/>addr 0: duty<br/>addr 1: mode+bits<br/>addr 2: dyadic_word] --> MODE
        CONFIG --> DUTY

        COUNTER[10-bit PWM Counter<br/>0–512] --> COMPARE
        COUNTER --> DYADIC

        DYADIC[7-bit Dyadic Counter<br/>+ HSB function] --> DITHER
        DITHER[Dither Logic<br/>Normal / Dyadic / Dither3] --> SCALE

        MODE[Mode Decode<br/>5/6/7/8/9-bit<br/>Normal/Dyadic/Dither] --> DITHER
        MODE --> SCALE

        DUTY[Duty Register] --> COMPARE
        COMPARE[Duty Compare] --> SCALE

        SCALE[Duty Scaling<br/>to 513-cycle period] --> PWM
        PWM[PWM Generator<br/>+ Dead-time] --> OUT[pwm_out / pwm_out_n]
    end

    style CLK fill:#3355cc,stroke:#fff,color:#fff
    style RST fill:#3355cc,stroke:#fff,color:#fff
    style ENA fill:#3355cc,stroke:#fff,color:#fff
    style UI fill:#448844,stroke:#fff,color:#fff
    style UO fill:#cc6633,stroke:#fff,color:#fff
    style UIO fill:#cc6633,stroke:#fff,color:#fff
    style OUT fill:#cc6633,stroke:#fff,color:#fff
    style DPWM fill:#aa44cc,stroke:#fff,color:#fff
    style CONFIG fill:#2d4a22,stroke:#fff,color:#fff
    style COUNTER fill:#2d4a22,stroke:#fff,color:#fff
    style DYADIC fill:#2d4a22,stroke:#fff,color:#fff
    style DITHER fill:#2d4a22,stroke:#fff,color:#fff
    style MODE fill:#2d4a22,stroke:#fff,color:#fff
    style DUTY fill:#2d4a22,stroke:#fff,color:#fff
    style COMPARE fill:#2d4a22,stroke:#fff,color:#fff
    style SCALE fill:#2d4a22,stroke:#fff,color:#fff
    style PWM fill:#2d4a22,stroke:#fff,color:#fff
"""

# ============================================================
# 1a. Mermaid → PNG via mermaid.ink
# ============================================================

def render_mermaid():
    """Render the Mermaid diagram to PNG using mermaid.ink API."""
    png_path = os.path.join(OUT_DIR, "block-diagram-mermaid.png")

    # Encode diagram for mermaid.ink
    graphbytes = MERMAID_DIAGRAM.encode("utf-8")
    compressed = zlib.compress(graphbytes, 9)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii")

    url = f"https://mermaid.ink/img/{encoded}?type=png&bgColor=!0d1117&theme=dark"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            with open(png_path, "wb") as f:
                f.write(resp.read())
        print(f"  Mermaid PNG: {png_path}")
        return png_path
    except Exception as e:
        print(f"  Mermaid render failed: {e}")
        # Fallback: save the mermaid source
        mmd_path = os.path.join(OUT_DIR, "block-diagram-mermaid.mmd")
        with open(mmd_path, "w") as f:
            f.write(MERMAID_DIAGRAM)
        print(f"  Saved Mermaid source to: {mmd_path}")
        return None


# ============================================================
# 2. Matplotlib block diagram
# ============================================================

def render_matplotlib():
    """Draw a clean block diagram using matplotlib patches and arrows."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    import numpy as np

    png_path = os.path.join(OUT_DIR, "block-diagram-mpl.png")

    fig, ax = plt.subplots(figsize=(14, 10), facecolor="#0d1117")
    ax.set_facecolor("#0d1117")
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")

    # Box definitions: (x, y, w, h, label, color)
    boxes = [
        # IO (top row)
        (0.3, 8.2, 1.4, 0.7, "clk", "#3355cc"),
        (2.0, 8.2, 1.4, 0.7, "rst_n", "#3355cc"),
        (3.7, 8.2, 1.4, 0.7, "ena", "#3355cc"),
        (5.4, 8.2, 2.0, 0.7, "ui_in[7:0]", "#448844"),
        # IO (bottom row)
        (0.3, 1.1, 1.4, 0.7, "uo_out[7:0]", "#cc6633"),
        (2.0, 1.1, 1.4, 0.7, "uio_out[7:0]", "#cc6633"),
        (5.4, 1.1, 2.0, 0.7, "pwm_out / pwm_n", "#cc6633"),
        # Core blocks
        (0.7, 5.5, 2.2, 1.8, "Config\nRegister File\n(duty, mode,\ndyadic_word)", "#1a3a1a"),
        (3.5, 5.5, 2.2, 1.2, "10-bit\nPWM Counter\n(0–512)", "#1a3a1a"),
        (6.2, 6.8, 2.0, 1.2, "7-bit Dyadic\nCounter\n+ HSB", "#1a3a1a"),
        (9.0, 6.8, 2.0, 1.2, "Mode\nDecode\n(5/6/7/8/9 bit)", "#1a3a1a"),
        (6.2, 4.5, 2.0, 1.0, "Dither Logic\n(N/D/D3)", "#1a3a1a"),
        (9.0, 4.5, 2.0, 1.0, "Duty\nCompare", "#1a3a1a"),
        (3.5, 3.5, 2.2, 1.0, "Duty Register", "#1a3a1a"),
        (6.2, 2.5, 2.0, 1.0, "Duty Scaling\n(to 513 cycles)", "#1a3a1a"),
        (9.0, 2.5, 2.0, 1.0, "PWM Generator\n+ Dead-time", "#1a3a1a"),
        # Wrapper
        (5.0, 7.8, 8.5, 2.0, "", None),  # outline only
    ]

    for x, y, w, h, label, color in boxes:
        if color is None:  # outline box
            rect = mpatches.Rectangle((x, y), w, h, fill=False, edgecolor="#aa44cc",
                                      linewidth=2, linestyle="--")
        else:
            rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                                  facecolor=color, edgecolor="#ffffff22", linewidth=1)
        ax.add_patch(rect)
        if label:
            ax.text(x + w/2, y + h/2, label, ha="center", va="center",
                   color="white", fontsize=8, fontweight="bold", family="monospace")

    # Title
    ax.text(7, 9.5, "Dyadic PWM — Functional Block Diagram",
            ha="center", va="center", color="white", fontsize=14, fontweight="bold")
    ax.text(7, 0.3, "GF180MCU · TinyTapeout GF-26a · tt_um_maqsudbek_dyadic_pwm",
            ha="center", va="center", color="#888888", fontsize=8, family="monospace")

    # Arrows (simplified — just a few key ones)
    arrows = [
        (1.8, 8.55, 1.8, 7.3),   # clk → core
        (3.4, 8.55, 4.5, 7.3),   # ui_in → core
        (4.5, 5.5, 8.0, 5.5),    # config → dither
        (5.7, 6.1, 5.7, 4.5),    # counter → dither
        (8.2, 6.8, 8.2, 5.5),    # dyadic → dither
        (10.0, 6.8, 10.0, 5.5),  # mode → dither
        (4.5, 4.0, 7.2, 4.0),    # duty → compare
        (11.0, 5.5, 11.0, 3.5),  # compare → scale
        (7.2, 3.5, 8.0, 4.5),    # scale → pwm
        (11.0, 3.5, 11.0, 1.8),  # pwm → out
    ]
    for x1, y1, x2, y2 in arrows:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                   arrowprops=dict(arrowstyle="->", color="#ffffff66", lw=1.2))

    plt.tight_layout(pad=0.5)
    fig.savefig(png_path, dpi=150, facecolor="#0d1117", edgecolor="none",
                bbox_inches="tight")
    plt.close(fig)
    print(f"  Matplotlib PNG: {png_path}")
    return png_path


# ============================================================
# 3. Hand-crafted SVG
# ============================================================

def render_svg():
    """Generate a hand-crafted SVG block diagram."""
    svg_path = os.path.join(OUT_DIR, "block-diagram.svg")

    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 700"
     width="1000" height="700" style="background:#0d1117;font-family:monospace">
  <defs>
    <marker id="arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
      <polygon points="0 0, 8 3, 0 6" fill="#ffffff88"/>
    </marker>
    <filter id="glow"><feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>

  <!-- Title -->
  <text x="500" y="30" text-anchor="middle" fill="white" font-size="18" font-weight="bold">
    Dyadic PWM — Functional Block Diagram</text>
  <text x="500" y="48" text-anchor="middle" fill="#888" font-size="10">
    GF180MCU · TinyTapeout GF-26a · tt_um_maqsudbek_dyadic_pwm</text>

  <!-- Boundary box: tt_um wrapper -->
  <rect x="30" y="60" width="940" height="580" rx="8" fill="none"
        stroke="#aa44cc" stroke-width="2" stroke-dasharray="8 4"/>
  <text x="45" y="80" fill="#aa44cc" font-size="11">tt_um_maqsudbek_dyadic_pwm (project.v)</text>

  <!-- Input ports -->
  <rect x="40" y="100" width="110" height="30" rx="5" fill="#3355cc"/>
  <text x="95" y="120" text-anchor="middle" fill="white" font-size="11">clk</text>
  <rect x="170" y="100" width="110" height="30" rx="5" fill="#3355cc"/>
  <text x="225" y="120" text-anchor="middle" fill="white" font-size="11">rst_n</text>
  <rect x="300" y="100" width="110" height="30" rx="5" fill="#3355cc"/>
  <text x="355" y="120" text-anchor="middle" fill="white" font-size="11">ena</text>
  <rect x="430" y="100" width="130" height="30" rx="5" fill="#448844"/>
  <text x="495" y="120" text-anchor="middle" fill="white" font-size="11">ui_in[7:0]</text>

  <!-- Output ports -->
  <rect x="40" y="600" width="130" height="30" rx="5" fill="#cc6633"/>
  <text x="105" y="620" text-anchor="middle" fill="white" font-size="11">uo_out[7:0]</text>
  <rect x="190" y="600" width="130" height="30" rx="5" fill="#cc6633"/>
  <text x="255" y="620" text-anchor="middle" fill="white" font-size="11">uio_out[7:0]</text>
  <rect x="340" y="600" width="150" height="30" rx="5" fill="#cc6633"/>
  <text x="415" y="620" text-anchor="middle" fill="white" font-size="11">pwm_out / pwm_n</text>

  <!-- dyadic_pwm core boundary -->
  <rect x="560" y="80" width="400" height="540" rx="6" fill="none"
        stroke="#33aa66" stroke-width="1.5" stroke-dasharray="4 3"/>
  <text x="575" y="98" fill="#33aa66" font-size="10">dyadic_pwm (dyadic.v)</text>

  <!-- Internal blocks -->
  <rect x="580" y="120" width="170" height="90" rx="6" fill="#1a3a1a" stroke="#ffffff22"/>
  <text x="665" y="148" text-anchor="middle" fill="white" font-size="9">Config Register File</text>
  <text x="665" y="163" text-anchor="middle" fill="#aaa" font-size="8">duty · mode · dyadic_word</text>
  <text x="665" y="178" text-anchor="middle" fill="#aaa" font-size="8">addr 0/1/2</text>

  <rect x="580" y="240" width="170" height="70" rx="6" fill="#1a3a1a" stroke="#ffffff22"/>
  <text x="665" y="268" text-anchor="middle" fill="white" font-size="9">10-bit PWM Counter</text>
  <text x="665" y="283" text-anchor="middle" fill="#aaa" font-size="8">0 → 512</text>

  <rect x="780" y="200" width="160" height="70" rx="6" fill="#1a3a1a" stroke="#ffffff22"/>
  <text x="860" y="228" text-anchor="middle" fill="white" font-size="9">7-bit Dyadic Counter</text>
  <text x="860" y="243" text-anchor="middle" fill="#aaa" font-size="8">+ HSB function</text>

  <rect x="780" y="120" width="160" height="55" rx="6" fill="#1a3a1a" stroke="#ffffff22"/>
  <text x="860" y="142" text-anchor="middle" fill="white" font-size="9">Mode Decode</text>
  <text x="860" y="157" text-anchor="middle" fill="#aaa" font-size="8">5/6/7/8/9-bit</text>

  <rect x="580" y="360" width="170" height="55" rx="6" fill="#1a3a1a" stroke="#ffffff22"/>
  <text x="665" y="382" text-anchor="middle" fill="white" font-size="9">Dither Logic</text>
  <text x="665" y="397" text-anchor="middle" fill="#aaa" font-size="8">Normal / Dyadic / Dither3</text>

  <rect x="780" y="360" width="160" height="55" rx="6" fill="#1a3a1a" stroke="#ffffff22"/>
  <text x="860" y="382" text-anchor="middle" fill="white" font-size="9">Duty Compare</text>
  <text x="860" y="397" text-anchor="middle" fill="#aaa" font-size="8">duty ≥ counter</text>

  <rect x="580" y="460" width="170" height="55" rx="6" fill="#1a3a1a" stroke="#ffffff22"/>
  <text x="665" y="482" text-anchor="middle" fill="white" font-size="9">Duty Scaling</text>
  <text x="665" y="497" text-anchor="middle" fill="#aaa" font-size="8">to 513-cycle period</text>

  <rect x="780" y="460" width="160" height="55" rx="6" fill="#1a3a1a" stroke="#ffffff22"/>
  <text x="860" y="482" text-anchor="middle" fill="white" font-size="9">PWM Generator</text>
  <text x="860" y="497" text-anchor="middle" fill="#aaa" font-size="8">+ Dead-time</text>

  <!-- Arrows -->
  <line x1="150" y1="130" x2="580" y2="150" stroke="#ffffff66" stroke-width="1.5" marker-end="url(#arrow)"/>
  <line x1="280" y1="130" x2="580" y2="250" stroke="#ffffff66" stroke-width="1.5" marker-end="url(#arrow)"/>
  <line x1="750" y1="165" x2="780" y2="148" stroke="#ffffff66" stroke-width="1.5" marker-end="url(#arrow)"/>
  <line x1="750" y1="200" x2="780" y2="235" stroke="#ffffff66" stroke-width="1.5" marker-end="url(#arrow)"/>
  <line x1="750" y1="200" x2="780" y2="148" stroke="#ffffff66" stroke-width="1.5" marker-end="url(#arrow)"/>
  <line x1="750" y1="387" x2="780" y2="387" stroke="#ffffff66" stroke-width="1.5" marker-end="url(#arrow)"/>
  <line x1="665" y1="310" x2="665" y2="360" stroke="#ffffff66" stroke-width="1.5" marker-end="url(#arrow)"/>
  <line x1="860" y1="270" x2="860" y2="360" stroke="#ffffff66" stroke-width="1.5" marker-end="url(#arrow)"/>
  <line x1="860" y1="415" x2="860" y2="460" stroke="#ffffff66" stroke-width="1.5" marker-end="url(#arrow)"/>
  <line x1="665" y1="415" x2="665" y2="460" stroke="#ffffff66" stroke-width="1.5" marker-end="url(#arrow)"/>
  <line x1="750" y1="487" x2="780" y2="487" stroke="#ffffff66" stroke-width="1.5" marker-end="url(#arrow)"/>
  <line x1="860" y1="515" x2="860" y2="600" stroke="#ffffff66" stroke-width="1.5" marker-end="url(#arrow)"/>
  <line x1="665" y1="515" x2="665" y2="600" stroke="#ffffff66" stroke-width="1.5" marker-end="url(#arrow)"/>

  <!-- Legend -->
  <rect x="40" y="200" width="140" height="120" rx="5" fill="#ffffff08" stroke="#ffffff22"/>
  <text x="110" y="218" text-anchor="middle" fill="white" font-size="10" font-weight="bold">Legend</text>
  <rect x="50" y="228" width="14" height="10" rx="2" fill="#3355cc"/>
  <text x="72" y="237" fill="#aaa" font-size="8">Input</text>
  <rect x="50" y="248" width="14" height="10" rx="2" fill="#cc6633"/>
  <text x="72" y="257" fill="#aaa" font-size="8">Output</text>
  <rect x="50" y="268" width="14" height="10" rx="2" fill="#1a3a1a"/>
  <text x="72" y="277" fill="#aaa" font-size="8">Internal block</text>
  <rect x="50" y="288" width="14" height="10" rx="2" fill="none" stroke="#aa44cc"/>
  <text x="72" y="297" fill="#aaa" font-size="8">TT wrapper</text>
</svg>"""

    with open(svg_path, "w") as f:
        f.write(svg)
    print(f"  Hand-crafted SVG: {svg_path}")
    return svg_path


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    print("=== Phase 5: Block Diagrams ===")
    render_mermaid()
    render_matplotlib()
    render_svg()
    print("\n✅ Phase 5 complete — all 3 block diagrams generated")
