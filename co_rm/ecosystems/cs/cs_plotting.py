import json
from pathlib import Path
import numpy as np

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from utils import plt_counties, TARGET_CRS, COUNTIES_PATH
from functions.plot_hillshade import plot_hillshade
from cs_constants import VEG_LABELS
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

def plot_veg_composition(
    bivar_map,
    veg_aligned,
    bivar_colors,
    hazard_label="Hazard",
    title=None,
    veg_labels=None,
    sort_by="size",
    figsize=None,
):
    """
    Stacked horizontal bar chart showing the nonant composition of each
    vegetation class, with a companion total-pixels bar and 3x3 legend.

    Parameters
    ----------
    bivar_map : 2D np.ndarray
        Bivariate classification (0–8, -1 for NA). Same shape as veg_aligned.
    veg_aligned : 2D np.ndarray
        Vegetation class raster aligned to the same grid. NaN for invalid.
    bivar_colors : dict {int -> color}
        9-class bivariate color mapping (keys 0–8).
    hazard_label : str
        Label for the warming/hazard axis legend.
    title : str or None
        Plot title. Auto-generated if None.
    veg_labels : dict or None
        Mapping of integer class codes to label strings. Defaults to VEG_LABELS.
    sort_by : str
        One of 'refugia', 'at_risk', 'size', 'alpha'.
    figsize : tuple or None

    Returns
    -------
    fig, (ax, ax2, legend_ax)
    """
    if veg_labels is None:
        veg_labels = VEG_LABELS

    # Flatten and mask
    veg_flat = veg_aligned.flatten()
    bivar_flat = bivar_map.flatten()
    valid = np.isfinite(veg_flat) & (bivar_flat >= 0)

    veg_valid = veg_flat[valid].astype(int)
    bivar_valid = bivar_flat[valid].astype(int)

    # Cross-tabulate
    unique_veg = np.unique(veg_valid)
    n_veg = len(unique_veg)
    counts = np.zeros((n_veg, 9), dtype=int)
    for i, v in enumerate(unique_veg):
        mask_v = veg_valid == v
        for code in range(9):
            counts[i, code] = np.sum(bivar_valid[mask_v] == code)

    # Proportions (row-normalized)
    row_totals = counts.sum(axis=1, keepdims=True)
    proportions = np.where(row_totals > 0, 100.0 * counts / row_totals, 0)

    # Build label list
    cat_labels = [veg_labels.get(int(v), f"Class {int(v)}") for v in unique_veg]

    # Sort
    totals = counts.sum(axis=1)
    if sort_by == "refugia":
        sort_key = proportions[:, [0, 1, 2]].sum(axis=1)
        sort_idx = np.argsort(sort_key)[::-1]
    elif sort_by == "at_risk":
        sort_idx = np.argsort(proportions[:, 8])[::-1]
    elif sort_by == "size":
        sort_idx = np.argsort(totals)[::-1]
    elif sort_by == "alpha":
        sort_idx = np.argsort(cat_labels)
    else:
        sort_idx = np.arange(n_veg)

    sorted_props = proportions[sort_idx]
    sorted_totals = totals[sort_idx]
    sorted_labels = [cat_labels[i] for i in sort_idx]

    if figsize is None:
        figsize = (14, max(5, 0.45 * len(sorted_labels)))

    if title is None:
        title = f"Vegetation composition by nonant — {hazard_label}"

    # Plot
    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=figsize,
        gridspec_kw={"width_ratios": [4, 1], "wspace": 0.05},
        sharey=True,
    )

    y_pos = np.arange(len(sorted_labels))
    left = np.zeros(len(sorted_labels))

    for nonant in range(9):
        widths = sorted_props[:, nonant]
        ax.barh(y_pos, widths, left=left,
                color=bivar_colors[nonant],
                edgecolor="white", linewidth=0.5)
        left += widths

    ax.set_yticks(y_pos)
    ax.set_yticklabels(sorted_labels, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("% of vegetation class")
    ax.set_title(title, fontsize=12, fontweight="bold", loc="left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax2.barh(y_pos, sorted_totals, color="#555555")
    ax2.set_xlabel("Total pixels")
    ax2.set_xscale("log")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.tick_params(labelsize=8)

    plt.subplots_adjust(right=0.82)

    # 3x3 legend
    legend_ax = fig.add_axes([0.86, 0.35, 0.12, 0.3])
    for i in range(3):
        for j in range(3):
            code = i * 3 + j
            legend_ax.add_patch(plt.Rectangle(
                (j, i), 1, 1,
                facecolor=bivar_colors[code],
                edgecolor="white", linewidth=1.5,
            ))
    legend_ax.set_xlim(-0.3, 3.3)
    legend_ax.set_ylim(-0.7, 3.5)
    legend_ax.set_aspect("equal")
    legend_ax.set_xticks([])
    legend_ax.set_yticks([])
    legend_ax.spines[:].set_visible(False)
    legend_ax.annotate("", xy=(3.15, 0), xytext=(0, 0),
                       arrowprops=dict(arrowstyle="->", color="black", lw=1.4))
    legend_ax.annotate("", xy=(0, 3.15), xytext=(0, 0),
                       arrowprops=dict(arrowstyle="->", color="black", lw=1.4))
    legend_ax.text(1.5, -0.6, "Conservation →", ha="center", fontsize=9)
    legend_ax.text(-0.5, 1.5, f"{hazard_label} →", ha="center", fontsize=9, rotation=90)

    return fig, (ax, ax2, legend_ax)