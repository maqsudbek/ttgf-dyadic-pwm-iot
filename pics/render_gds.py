#!/usr/bin/env python3
"""Render GDS layout → SVG, colored PNG, and detail zoom.
Reads the hardened GDS from .claude/harden/run12/ and outputs to pics/.
Uses gdstk + cairosvg + matplotlib. No project files modified.
"""

import sys, os
import gdstk
import cairosvg
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection
import numpy as np

GDS_PATH = os.path.join(
    os.path.dirname(__file__), "..",
    ".claude/harden/run12/GDS_logs/runs/wokwi/final/gds/tt_um_maqsudbek_dyadic_pwm.gds"
)
OUT_DIR = os.path.join(os.path.dirname(__file__), "files")

# GF180MCU layer mappings (approximate — for visual coloring)
LAYER_COLORS = {
    # layer: (name, color_hex)
    0:   ("background",   "#0d1117"),
    1:   ("nwell",        "#2d4a22"),
    2:   ("diff",         "#8b7355"),
    3:   ("poly",         "#cc4444"),
    4:   ("pselect",      "#448844"),
    5:   ("nselect",      "#448844"),
    6:   ("contact",      "#888888"),
    7:   ("metal1",       "#3355cc"),
    8:   ("via1",         "#888888"),
    9:   ("metal2",       "#cc6633"),
    10:  ("via2",         "#888888"),
    11:  ("metal3",       "#33aa66"),
    12:  ("via3",         "#888888"),
    13:  ("metal4",       "#aa44cc"),
    14:  ("via4",         "#888888"),
    15:  ("metal5",       "#ddcc33"),
    16:  ("pad",          "#ff6666"),
    17:  ("text",         "#ffffff"),
    32:  ("outline",      "#ffcc00"),
    33:  ("boundary",     "#ff00ff"),
}

def load_gds(path):
    lib = gdstk.read_gds(path)
    top = lib.top_level()[0]
    print(f"Loaded {path}")
    print(f"  Top cell: {top.name}")
    print(f"  Polygons: {sum(len(c.polygons) for c in top.dependencies(True)):,}")
    return lib, top

def render_svg(top):
    """Render clean SVG via gdstk's built-in write_svg."""
    svg_path = os.path.join(OUT_DIR, "layout-gds.svg")
    top.write_svg(
        svg_path,
        background="#0d1117",
        scaling=10,
    )
    print(f"  SVG written: {svg_path}")
    return svg_path

def render_colored_png(top):
    """Render a colored PNG using matplotlib for layer-aware coloring."""
    png_path = os.path.join(OUT_DIR, "layout-gds-colored.png")

    # Collect polygons by layer
    cells = list(top.dependencies(True))
    layers = {}
    for cell in cells:
        for poly in cell.polygons:
            layer = poly.layer
            if layer not in layers:
                layers[layer] = []
            layers[layer].append(poly)

    if not layers:
        print("  No polygons found — skipping colored render")
        return None

    fig, ax = plt.subplots(figsize=(12, 12), facecolor="#0d1117")
    ax.set_facecolor("#0d1117")
    ax.set_aspect("equal")

    for layer, polys in sorted(layers.items()):
        name, color = LAYER_COLORS.get(layer, (f"layer{layer}", "#555555"))
        patches = []
        for poly in polys:
            pts = np.array(poly.points)
            patches.append(MplPolygon(pts, closed=True))
        pc = PatchCollection(patches, facecolor=color, edgecolor="none", alpha=0.85)
        ax.add_collection(pc)
        if patches:
            print(f"  Layer {layer:2d} ({name:12s}): {len(patches):5d} polygons — {color}")

    # Auto-fit view
    all_x, all_y = [], []
    for polys in layers.values():
        for p in polys:
            pts = np.array(p.points)
            all_x.extend(pts[:, 0])
            all_y.extend(pts[:, 1])
    if all_x:
        margin = 0.02 * (max(all_x) - min(all_x))
        ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
        ax.set_ylim(min(all_y) - margin, max(all_y) + margin)

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("Dyadic PWM — GF180MCU GDS Layout (colored by layer)",
                 color="white", fontsize=10, pad=8)

    plt.tight_layout(pad=0)
    fig.savefig(png_path, dpi=200, facecolor="#0d1117", edgecolor="none")
    plt.close(fig)
    print(f"  Colored PNG: {png_path}")
    return png_path

def render_detail(top):
    """Render a zoomed-in detail of the central region."""
    png_path = os.path.join(OUT_DIR, "layout-gds-detail.png")

    cells = list(top.dependencies(True))
    layers = {}
    for cell in cells:
        for poly in cell.polygons:
            layer = poly.layer
            if layer not in layers:
                layers[layer] = []
            layers[layer].append(poly)

    if not layers:
        print("  No polygons — skipping detail render")
        return None

    # Find bounding box
    all_x, all_y = [], []
    for polys in layers.values():
        for p in polys:
            pts = np.array(p.points)
            all_x.extend(pts[:, 0])
            all_y.extend(pts[:, 1])
    cx, cy = np.mean(all_x), np.mean(all_y)
    half_w = (max(all_x) - min(all_x)) * 0.15  # zoom to ~30% of die

    fig, ax = plt.subplots(figsize=(12, 12), facecolor="#0d1117")
    ax.set_facecolor("#0d1117")
    ax.set_aspect("equal")

    for layer, polys in sorted(layers.items()):
        name, color = LAYER_COLORS.get(layer, (f"layer{layer}", "#555555"))
        patches = []
        for poly in polys:
            pts = np.array(poly.points)
            patches.append(MplPolygon(pts, closed=True))
        pc = PatchCollection(patches, facecolor=color, edgecolor="none", alpha=0.85)
        ax.add_collection(pc)

    ax.set_xlim(cx - half_w, cx + half_w)
    ax.set_ylim(cy - half_w, cy + half_w)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("Dyadic PWM — Die Center Detail (colored by layer)",
                 color="white", fontsize=10, pad=8)

    plt.tight_layout(pad=0)
    fig.savefig(png_path, dpi=300, facecolor="#0d1117", edgecolor="none")
    plt.close(fig)
    print(f"  Detail PNG: {png_path}")
    return png_path


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    lib, top = load_gds(GDS_PATH)
    render_svg(top)
    render_colored_png(top)
    render_detail(top)
    print("\n✅ Phase 2 complete — all GDS renders generated")
