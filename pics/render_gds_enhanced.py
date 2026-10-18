#!/usr/bin/env python3
"""Enhanced GDS renders — zoomed, clean, multi-panel, 3D-ish, and exploded views.
Filters fill/boundary layers for clarity. Shows transistors+wires distinctly.
"""

import os
import gdstk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
from matplotlib.patches import Polygon as MplPolygon, Patch
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

GDS_PATH = os.path.join(
    os.path.dirname(__file__), "..",
    ".claude/harden/run12/GDS_logs/runs/wokwi/final/gds/tt_um_maqsudbek_dyadic_pwm.gds"
)
OUT_DIR = os.path.join(os.path.dirname(__file__), "files")

# GF180MCU Magic-streamed GDS layer mapping (name, color, z-height-nm)
LAYER_INFO = {
    0:   ("pwell",         "#1a2a1a",  0),
    21:  ("poly2",         "#cc4444",  300),
    22:  ("poly_contact",  "#dd8844",  350),
    30:  ("contact",       "#44aadd",  400),
    31:  ("metal1",        "#3355cc",  500),
    32:  ("via1",          "#888888",  600),
    33:  ("metal2",        "#cc6633",  800),
    34:  ("via2",          "#aaaa44",  900),
    55:  ("pad",           "#ff6666",  1100),
    112: ("text",          "#ffffff",  0),
    204: ("boundary",      "#ff00ff",  0),
}

SKIP_LAYERS = {0, 112, 204}
STRUCT_LAYERS = [21, 22, 30, 31, 32, 33, 34, 55]


def load_and_collect():
    lib = gdstk.read_gds(GDS_PATH)
    top = lib.top_level()[0]
    layers = defaultdict(list)
    for cell in top.dependencies(True):
        for poly in cell.polygons:
            if poly.layer not in SKIP_LAYERS:
                layers[poly.layer].append(np.array(poly.points))
    xs, ys = [], []
    for pts_list in layers.values():
        for pts in pts_list:
            xs.extend(pts[:, 0]); ys.extend(pts[:, 1])
    bounds = (min(xs), max(xs), min(ys), max(ys)) if xs else (0, 1, 0, 1)
    return layers, bounds


def dark_ax(ax, title="", aspect="equal"):
    ax.set_facecolor("#0d1117")
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_aspect(aspect)
    if title:
        ax.set_title(title, color="white", fontsize=9, fontweight="bold", pad=6)


def draw_layer(ax, points_list, color, alpha=0.9):
    for pts in points_list:
        ax.add_patch(MplPolygon(pts, closed=True, facecolor=color, edgecolor="none", alpha=alpha))


# ============================================================
# 1. MULTI-PANEL ZOOMED — each structural layer in its own panel
# ============================================================

def render_multipanel(layers, bounds):
    xmin, xmax, ymin, ymax = bounds
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    zoom_w = (xmax - xmin) * 0.25
    zoom_h = (ymax - ymin) * 0.70
    zx = (cx - zoom_w, cx + zoom_w)
    zy = (cy - zoom_h, cy + zoom_h)

    visible = [l for l in STRUCT_LAYERS if l in layers]
    n = len(visible)
    cols = min(3, n)
    rows = (n + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(cols*3.5, rows*3.5), facecolor="#0d1117")
    axes = np.atleast_1d(axes).flatten()

    for i, layer_num in enumerate(visible):
        ax = axes[i]
        name, color, _ = LAYER_INFO[layer_num]
        draw_layer(ax, layers[layer_num], color)
        ax.set_xlim(zx); ax.set_ylim(zy)
        dark_ax(ax, f"L{layer_num}: {name}  ({len(layers[layer_num])} polygons)")

    for j in range(len(visible), len(axes)):
        axes[j].set_visible(False)

    fig.suptitle("GF180MCU — Zoomed Layer Detail (die center ~25%)", color="white",
                 fontsize=12, fontweight="bold")
    fig.tight_layout(pad=1, rect=[0, 0, 1, 0.96])
    path = os.path.join(OUT_DIR, "layout-zoomed-panels.png")
    fig.savefig(path, dpi=200, facecolor="#0d1117", edgecolor="none")
    plt.close(fig)
    print(f"  {os.path.basename(path)}")


# ============================================================
# 2. SMART METAL OVERLAY — metal stack with transparency
# ============================================================

def render_metal_overlay(layers, bounds):
    xmin, xmax, ymin, ymax = bounds
    margin = 0.02 * (xmax - xmin)
    fig, ax = plt.subplots(figsize=(10, 4), facecolor="#0d1117")
    dark_ax(ax, "Metal Stack Overlay (M1 + V1 + M2 + V2) — Full Die")

    order = [(31, 1.0), (32, 0.6), (33, 0.7), (34, 0.5)]
    legend_handles = []
    for layer_num, alpha in order:
        if layer_num in layers:
            name, color, _ = LAYER_INFO[layer_num]
            draw_layer(ax, layers[layer_num], color, alpha)
            legend_handles.append(Patch(facecolor=color, alpha=0.8, label=f"L{layer_num}: {name}"))

    ax.set_xlim(xmin - margin, xmax + margin)
    ax.set_ylim(ymin - margin, ymax + margin)
    ax.legend(handles=legend_handles, loc="upper right", facecolor="#1a1a2e",
              edgecolor="#ffffff33", labelcolor="white", fontsize=7)

    path = os.path.join(OUT_DIR, "layout-metal-overlay.png")
    fig.savefig(path, dpi=250, facecolor="#0d1117", edgecolor="none", bbox_inches="tight")
    plt.close(fig)
    print(f"  {os.path.basename(path)}")


# ============================================================
# 3. FRONTEND vs BACKEND — transistors (left) vs wires (right)
# ============================================================

def render_fe_be_split(layers, bounds):
    xmin, xmax, ymin, ymax = bounds
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    zoom_w = (xmax - xmin) * 0.30
    zoom_h = (ymax - ymin) * 0.80
    zx = (cx - zoom_w, cx + zoom_w)
    zy = (cy - zoom_h, cy + zoom_h)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 6), facecolor="#0d1117")

    # Frontend
    dark_ax(ax1, "Front-End: Transistors (Poly + Contacts)")
    for lnum in [21, 22, 30]:
        if lnum in layers:
            draw_layer(ax1, layers[lnum], LAYER_INFO[lnum][1])
    ax1.set_xlim(zx); ax1.set_ylim(zy)

    # Backend
    dark_ax(ax2, "Back-End: Routing (M1 + M2 + Vias)")
    for lnum in [31, 32, 33, 34]:
        if lnum in layers:
            draw_layer(ax2, layers[lnum], LAYER_INFO[lnum][1], 0.85)
    ax2.set_xlim(zx); ax2.set_ylim(zy)

    be_legend = [Patch(facecolor=LAYER_INFO[l][1], alpha=0.85, label=LAYER_INFO[l][0])
                 for l in [31, 32, 33, 34] if l in layers]
    ax2.legend(handles=be_legend, loc="upper right", facecolor="#1a1a2e",
              edgecolor="#ffffff33", labelcolor="white", fontsize=6)

    fig.suptitle("GF180MCU — Transistors vs. Routing (zoomed die center)",
                 color="white", fontsize=11, fontweight="bold")
    fig.tight_layout(pad=1.5, rect=[0, 0, 1, 0.94])
    path = os.path.join(OUT_DIR, "layout-fe-be-split.png")
    fig.savefig(path, dpi=200, facecolor="#0d1117", edgecolor="none")
    plt.close(fig)
    print(f"  {os.path.basename(path)}")


# ============================================================
# 4. 3D ISOMETRIC — layers extruded at actual Z-heights
# ============================================================

def render_3d(layers, bounds):
    xmin, xmax, ymin, ymax = bounds
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    zoom = (xmax - xmin) * 0.18
    zx = (cx - zoom, cx + zoom)
    zy = (cy - zoom * 0.6, cy + zoom * 0.6)

    fig = plt.figure(figsize=(12, 8), facecolor="#0d1117")
    ax = fig.add_subplot(111, projection='3d')
    ax.set_facecolor("#0d1117")
    for pane in [ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane]:
        pane.fill = False
        pane.set_edgecolor('#1a1a2e')
    ax.tick_params(colors='#888888', labelsize=6)
    for label in [ax.xaxis.label, ax.yaxis.label, ax.zaxis.label]:
        label.set_color('#888888')

    z_scale = 0.3
    for layer_num in STRUCT_LAYERS:
        if layer_num not in layers:
            continue
        name, color, z_base = LAYER_INFO[layer_num]
        thickness = 50
        zb = z_base * z_scale
        zt = zb + thickness * z_scale

        for poly_pts in layers[layer_num][:300]:  # cap for speed
            pxs, pys = poly_pts[:, 0], poly_pts[:, 1]
            if (pxs < zx[0]).all() or (pxs > zx[1]).all():
                continue
            if (pys < zy[0]).all() or (pys > zy[1]).all():
                continue
            verts_top = np.column_stack([pxs, pys, np.full_like(pxs, zt)])
            ax.add_collection3d(Poly3DCollection([verts_top], facecolor=color, alpha=0.85, edgecolor='none'))
            n = len(pxs)
            for i in range(n):
                j = (i + 1) % n
                side = np.array([[pxs[i], pys[i], zb], [pxs[j], pys[j], zb],
                                 [pxs[j], pys[j], zt], [pxs[i], pys[i], zt]])
                ax.add_collection3d(Poly3DCollection([side], facecolor=color, alpha=0.3, edgecolor='none'))

    ax.set_xlim(zx); ax.set_ylim(zy)
    ax.set_zlim(0, 1200 * z_scale)
    ax.set_xlabel("X (µm)"); ax.set_ylabel("Y (µm)"); ax.set_zlabel("Z (nm)")
    ax.view_init(elev=35, azim=-45)
    ax.set_title("GF180MCU — 3D Isometric (zoomed, layers extruded)",
                 color="white", fontsize=11, fontweight="bold", pad=12)

    path = os.path.join(OUT_DIR, "layout-3d-isometric.png")
    fig.savefig(path, dpi=200, facecolor="#0d1117", edgecolor="none", bbox_inches="tight")
    plt.close(fig)
    print(f"  {os.path.basename(path)}")


# ============================================================
# 5. EXPLODED OFFSET — layers shifted for depth
# ============================================================

def render_exploded(layers, bounds):
    xmin, xmax, ymin, ymax = bounds
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    zoom = (xmax - xmin) * 0.25
    zx = (cx - zoom, cx + zoom)
    zy = (cy - zoom * 0.6, cy + zoom * 0.6)

    fig, ax = plt.subplots(figsize=(10, 8), facecolor="#0d1117")
    dark_ax(ax, "Exploded Offset — layers shifted for depth perception")

    offset_step = 1.5
    for i, layer_num in enumerate(STRUCT_LAYERS):
        if layer_num not in layers:
            continue
        name, color, _ = LAYER_INFO[layer_num]
        dx, dy = i * offset_step * 0.5, i * offset_step
        for pts in layers[layer_num][:200]:
            shifted = pts + np.array([dx, dy])
            ax.add_patch(MplPolygon(shifted, closed=True, facecolor=color,
                                     edgecolor="#ffffff22", linewidth=0.3, alpha=0.85))
        ax.text(cx - zoom + dx + 0.2, cy - zoom * 0.6 + dy + 0.3,
                f"L{layer_num}: {name}", color="white", fontsize=6,
                bbox=dict(facecolor="#0d1117dd", edgecolor="none", pad=1))

    ax.set_xlim(zx[0] - 1, zx[1] + len(STRUCT_LAYERS) * offset_step)
    ax.set_ylim(zy[0] - 1, zy[1] + len(STRUCT_LAYERS) * offset_step * 1.2)

    path = os.path.join(OUT_DIR, "layout-exploded-offset.png")
    fig.savefig(path, dpi=200, facecolor="#0d1117", edgecolor="none", bbox_inches="tight")
    plt.close(fig)
    print(f"  {os.path.basename(path)}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=== Enhanced GDS Renders ===")
    layers, bounds = load_and_collect()

    kept = sum(len(v) for v in layers.values())
    print(f"Loaded {kept} polygons across {len(layers)} layers "
          f"(skipped fill/text/boundary)")
    print(f"Die: {bounds[1]-bounds[0]:.1f} × {bounds[3]-bounds[2]:.1f} µm")

    os.makedirs(OUT_DIR, exist_ok=True)

    print("\n1. Multi-panel zoomed layers...")
    render_multipanel(layers, bounds)
    print("2. Smart metal overlay...")
    render_metal_overlay(layers, bounds)
    print("3. Frontend vs Backend split...")
    render_fe_be_split(layers, bounds)
    print("4. 3D isometric view...")
    render_3d(layers, bounds)
    print("5. Exploded offset view...")
    render_exploded(layers, bounds)

    print(f"\n✅ Enhanced renders complete → {OUT_DIR}/")
