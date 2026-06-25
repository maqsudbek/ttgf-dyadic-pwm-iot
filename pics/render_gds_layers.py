#!/usr/bin/env python3
"""Render each GDS layer separately for clear visualization.
GF180MCU Magic layer map:
  21=poly2, 22=poly_contact, 30=contact, 31=metal1, 32=via1,
  33=metal2, 34=via2, 55=pad, 112=text, 204=boundary
Key structural layers: metal2(33), via2(34), metal1(31), contact(30),
                       poly_contact(22), poly2(21)
"""

import os, sys
import gdstk
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

GDS_PATH = os.path.join(
    os.path.dirname(__file__), "..",
    ".claude/harden/run12/GDS_logs/runs/wokwi/final/gds/tt_um_maqsudbek_dyadic_pwm.gds"
)
OUT_DIR = os.path.join(os.path.dirname(__file__), "files")

GF180MCU_MAGIC_LAYERS = {
    0:   ("pwell",         "#1a2a1a"),
    21:  ("poly2",         "#cc4444"),
    22:  ("poly_contact",  "#dd8844"),
    30:  ("contact",       "#44aadd"),
    31:  ("metal1",        "#3355cc"),
    32:  ("via1",          "#888888"),
    33:  ("metal2",        "#cc6633"),
    34:  ("via2",          "#aaaa44"),
    55:  ("pad",           "#ff6666"),
    112: ("text_label",    "#ffffff"),
    204: ("boundary",      "#ff00ff"),
}

# Layers to render individually (most important structural layers)
KEY_LAYERS = [33, 34, 31, 30, 22, 21]  # metal2, via2, metal1, contact, poly_contact, poly2

# Layer groups for composite views
LAYER_GROUPS = {
    "metal-all": {
        "title": "All Metal Layers (M1+M2+Via)",
        "layers": [31, 32, 33, 34],
        "colors": {31: "#3355cc", 32: "#888888", 33: "#cc6633", 34: "#aaaa44"},
    },
    "frontend": {
        "title": "Front-End (Poly + Contacts)",
        "layers": [21, 22, 30],
        "colors": {21: "#cc4444", 22: "#dd8844", 30: "#44aadd"},
    },
    "backend": {
        "title": "Back-End (Metal1 + Metal2 + Vias)",
        "layers": [31, 32, 33, 34],
        "colors": {31: "#3355cc", 32: "#aa88ff", 33: "#cc6633", 34: "#aaaa44"},
    },
}


def load_gds(path):
    lib = gdstk.read_gds(path)
    top = lib.top_level()[0]
    return lib, top


def collect_polygons_by_layer(top):
    """Collect all polygons grouped by layer."""
    layers = defaultdict(list)
    for cell in top.dependencies(True):
        for poly in cell.polygons:
            layers[poly.layer].append(poly.points)
    return layers


def get_bounds(all_points):
    """Get global bounding box from all polygon points."""
    xs, ys = [], []
    for pts in all_points:
        xs.extend(pts[:, 0])
        ys.extend(pts[:, 1])
    if not xs:
        return 0, 1, 0, 1
    return min(xs), max(xs), min(ys), max(ys)


def get_all_bounds(layers_dict):
    """Get bounding box across all layers."""
    all_pts = []
    for pts_list in layers_dict.values():
        all_pts.extend(pts_list)
    xs = []
    ys = []
    for pts in all_pts:
        xs.extend(pts[:, 0])
        ys.extend(pts[:, 1])
    if not xs:
        return 0, 1, 0, 1
    return min(xs), max(xs), min(ys), max(ys)


def render_single_layer(ax, points_list, color, label, bounds):
    """Render one layer's polygons onto an axis."""
    patches = []
    for pts in points_list:
        patches.append(plt.Polygon(pts, closed=True, facecolor=color,
                                    edgecolor="none", alpha=0.9))
    for p in patches:
        ax.add_patch(p)
    return len(patches)


def make_figure(title, subtitle=""):
    """Create a dark-themed figure."""
    fig, ax = plt.subplots(figsize=(10, 10), facecolor="#0d1117")
    ax.set_facecolor("#0d1117")
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(title, color="white", fontsize=12, fontweight="bold", pad=10)
    if subtitle:
        ax.text(0.5, -0.02, subtitle, transform=ax.transAxes, ha="center",
                color="#888888", fontsize=8)
    return fig, ax


def render_per_layer(layers_data, global_bounds):
    """Render each key layer individually."""
    xmin, xmax, ymin, ymax = global_bounds
    margin = 0.03 * (xmax - xmin)

    for layer_num in KEY_LAYERS:
        if layer_num not in layers_data:
            continue
        name, color = GF180MCU_MAGIC_LAYERS.get(layer_num, (f"layer{layer_num}", "#555555"))
        n_polys = len(layers_data[layer_num])

        fig, ax = make_figure(
            f"Layer {layer_num}: {name}",
            f"{n_polys} polygons · GF180MCU Magic layer"
        )
        render_single_layer(ax, layers_data[layer_num], color, name, global_bounds)
        ax.set_xlim(xmin - margin, xmax + margin)
        ax.set_ylim(ymin - margin, ymax + margin)

        fname = f"layout-layer-{layer_num:02d}-{name}.png"
        out_path = os.path.join(OUT_DIR, fname)
        fig.savefig(out_path, dpi=200, facecolor="#0d1117", edgecolor="none",
                    bbox_inches="tight")
        plt.close(fig)
        print(f"  {fname} ({n_polys} polygons)")


def render_layer_groups(layers_data, global_bounds):
    """Render composite layer group views."""
    xmin, xmax, ymin, ymax = global_bounds
    margin = 0.03 * (xmax - xmin)

    for group_name, group_info in LAYER_GROUPS.items():
        fig, ax = make_figure(group_info["title"])
        total = 0
        for layer_num in group_info["layers"]:
            if layer_num in layers_data:
                color = group_info["colors"].get(layer_num, "#555555")
                name = GF180MCU_MAGIC_LAYERS.get(layer_num, (f"L{layer_num}",))[0]
                n = render_single_layer(ax, layers_data[layer_num], color, name, global_bounds)
                total += n

        ax.set_xlim(xmin - margin, xmax + margin)
        ax.set_ylim(ymin - margin, ymax + margin)

        # Legend
        from matplotlib.patches import Patch
        legend_elements = []
        for layer_num in group_info["layers"]:
            if layer_num in layers_data:
                name, _ = GF180MCU_MAGIC_LAYERS.get(layer_num, (f"L{layer_num}", "#555555"))
                color = group_info["colors"].get(layer_num, "#555555")
                legend_elements.append(Patch(facecolor=color, label=f"L{layer_num}: {name}"))
        if legend_elements:
            ax.legend(handles=legend_elements, loc="upper right",
                     facecolor="#1a1a2e", edgecolor="#ffffff33",
                     labelcolor="white", fontsize=7)

        fname = f"layout-group-{group_name}.png"
        out_path = os.path.join(OUT_DIR, fname)
        fig.savefig(out_path, dpi=200, facecolor="#0d1117", edgecolor="none",
                    bbox_inches="tight")
        plt.close(fig)
        print(f"  {fname}")


def render_all_layers_overlay(layers_data, global_bounds):
    """Render all layers together with distinct colors."""
    xmin, xmax, ymin, ymax = global_bounds
    margin = 0.03 * (xmax - xmin)

    fig, ax = make_figure(
        "All Layers — GF180MCU GDS Layout",
        "Colored by Magic layer · tt_um_maqsudbek_dyadic_pwm"
    )

    from matplotlib.patches import Patch
    legend_elements = []

    for layer_num in sorted(layers_data.keys()):
        name, color = GF180MCU_MAGIC_LAYERS.get(layer_num, (f"layer{layer_num}", "#555555"))
        render_single_layer(ax, layers_data[layer_num], color, name, global_bounds)
        legend_elements.append(Patch(facecolor=color, label=f"L{layer_num}: {name}"))

    ax.set_xlim(xmin - margin, xmax + margin)
    ax.set_ylim(ymin - margin, ymax + margin)
    ax.legend(handles=legend_elements, loc="upper right",
             facecolor="#1a1a2e", edgecolor="#ffffff33",
             labelcolor="white", fontsize=6, ncol=2)

    out_path = os.path.join(OUT_DIR, "layout-all-layers.png")
    fig.savefig(out_path, dpi=200, facecolor="#0d1117", edgecolor="none",
                bbox_inches="tight")
    plt.close(fig)
    print(f"  layout-all-layers.png")


if __name__ == "__main__":
    print("=== Per-Layer GDS Renders ===")
    lib, top = load_gds(GDS_PATH)
    layers_data = collect_polygons_by_layer(top)

    # Convert to numpy arrays for matplotlib
    layers_np = {k: [np.array(pts) for pts in v] for k, v in layers_data.items()}
    global_bounds = get_all_bounds(layers_np)

    print(f"\nGlobal bounds: x=[{global_bounds[0]:.1f}, {global_bounds[1]:.1f}], "
          f"y=[{global_bounds[2]:.1f}, {global_bounds[3]:.1f}]")
    print(f"Die size: {global_bounds[1]-global_bounds[0]:.1f} × {global_bounds[3]-global_bounds[2]:.1f} µm")

    print("\n--- Individual Layers ---")
    render_per_layer(layers_np, global_bounds)

    print("\n--- Layer Groups ---")
    render_layer_groups(layers_np, global_bounds)

    print("\n--- All Layers Overlay ---")
    render_all_layers_overlay(layers_np, global_bounds)

    print(f"\n✅ Per-layer renders complete — {len(KEY_LAYERS)} individual + {len(LAYER_GROUPS)} group + 1 all-layer")
