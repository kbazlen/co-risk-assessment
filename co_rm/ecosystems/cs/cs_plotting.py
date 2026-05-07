import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from utils import plt_counties, TARGET_CRS, COUNTIES_PATH
from functions.plot_hillshade import plot_hillshade

# ============================================================
# Plotting (your functions, unchanged)
# ============================================================

def plot_bivariate_map(bivar_map, extent, color_dict, ax, alpha=0.8, zorder=2):
    n_codes = len(color_dict)
    cmap = ListedColormap([(1, 1, 1, 0)] + [color_dict[i] for i in range(n_codes)])
    ax.imshow(
        bivar_map + 1, cmap=cmap, vmin=0, vmax=n_codes,
        extent=extent, origin="upper", interpolation="nearest",
        alpha=alpha, zorder=zorder,
    )


def add_bivariate_legend(fig, color_dict, x_label, y_label, n_classes=3,
                         position=(0.92, 0.12, 0.24, 0.34),
                         fontsize=13, arrow_lw=1.6, box_lw=1.8):
    legend_ax = fig.add_axes(list(position))
    for i in range(n_classes):
        for j in range(n_classes):
            code = i * n_classes + j
            legend_ax.add_patch(plt.Rectangle(
                (j, i), 1, 1, facecolor=color_dict[code],
                edgecolor="white", linewidth=box_lw,
            ))
    pad = 0.3
    legend_ax.set_xlim(-pad, n_classes + pad)
    legend_ax.set_ylim(-(pad + 0.4), n_classes + pad + 0.2)
    legend_ax.set_aspect("equal")
    legend_ax.set_xticks([]); legend_ax.set_yticks([])
    for s in legend_ax.spines.values():
        s.set_visible(False)
    legend_ax.annotate("", xy=(n_classes + 0.15, 0), xytext=(0, 0),
                       arrowprops=dict(arrowstyle="->", color="black", lw=arrow_lw))
    legend_ax.annotate("", xy=(0, n_classes + 0.15), xytext=(0, 0),
                       arrowprops=dict(arrowstyle="->", color="black", lw=arrow_lw))
    legend_ax.text(n_classes / 2, -0.6, x_label, ha="center", fontsize=fontsize)
    legend_ax.text(-0.55, n_classes / 2, y_label,
                   ha="center", fontsize=fontsize, rotation=90)
    return legend_ax


# ============================================================
# Save helpers — map, legend, metadata each as their own file
# ============================================================

def save_bivariate_outputs(out_dir, bivar_map, extent, color_dict,
                           x_label, y_label, n_classes,
                           x_breaks, y_breaks, meta_extra=None):
    """Save map.png, legend.png, and metadata.txt into out_dir."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- Map (with hillshade + counties; no legend baked in) ---
    fig, ax = plot_hillshade(target_crs=TARGET_CRS, topo_alpha=1, zfactor=5)
    plot_bivariate_map(bivar_map, extent, color_dict, ax=ax, alpha=0.8, zorder=2)
    plt_counties(COUNTIES_PATH, county_edgecolor="black",
                 county_linewidth=1.0, ax=ax)
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    ax.set_axis_off()
    # remove any margins so saved PNG has no whitespace around the map
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_position([0, 0, 1, 1])
    fig.savefig(
        out_dir / "map.png",
        dpi=200,
        bbox_inches="tight",
        pad_inches=0,
        transparent=True,
    )
    plt.close(fig)

    # --- Legend (standalone) ---
    legend_fig = plt.figure(figsize=(3, 3))
    add_bivariate_legend(
        legend_fig, color_dict, x_label, y_label, n_classes=n_classes,
        position=(0.15, 0.15, 0.7, 0.7),
    )
    legend_fig.savefig(out_dir / "legend.png", dpi=200, bbox_inches="tight")
    plt.close(legend_fig)

    # --- Metadata (txt) ---
    meta = {
        "x_label": x_label,
        "y_label": y_label,
        "n_classes": n_classes,
        "x_breaks": x_breaks.tolist(),
        "y_breaks": y_breaks.tolist(),
        "extent_3857_meters": list(extent),
        "valid_pixel_count": int((bivar_map >= 0).sum()),
        "class_pixel_counts": {
            int(c): int((bivar_map == c).sum()) for c in range(n_classes ** 2)
        },
    }
    if meta_extra:
        meta.update(meta_extra)
    (out_dir / "metadata.txt").write_text(json.dumps(meta, indent=2))

