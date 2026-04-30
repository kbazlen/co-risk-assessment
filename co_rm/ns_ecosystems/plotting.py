" Ecosystems and climate impacts plotting functions "

from itertools import count

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import rasterio
from rasterio.plot import show as rio_show
import geopandas as gpd
from pathlib import Path
import numpy as np
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.crs import CRS
from matplotlib.patches import PathPatch
import matplotlib.patches as mpatches


from matplotlib.colors import ListedColormap
from rasterio.transform import array_bounds

from matplotlib.path import Path as MplPath
from shapely.ops import unary_union

FINALMODST_COLORS = {
    "V":   "#5c8944",
    "G":   "#98bd00",
    "F":   "#b2b2b2",
    "P":   "#d7d79e",
    "U":   "#d7c29e",
    "NKP": "#f0f0f0",
}

FINALMODST_LABELS = {
    "V":   "Very Good",
    "G":   "Good",
    "F":   "Fair",
    "P":   "Poor",
    "U":   "Unknown",
    "NKP": "Private & Unmapped Lands",
}

FINALMODST_ORDER        = ["V", "G", "F", "P", "U", "NKP"]
FINALMODST_LEGEND_TITLE = "Conservation Protection Status"

# Vegetation COWRA22 VAT labels
VEG_LABELS = {
    1: "Agriculture",
    3: "Grassland",
    5: "Lodgepole Pine",
    6: "Mixed Conifer",
    7: "Oak Shrubland",
    8: "Open Water",
    9: "Pinyon-Juniper",
    10: "Ponderosa Pine",
    11: "Riparian",
    12: "Shrubland",
    13: "Spruce-Fir",
    14: "Developed",
    15: "Sparsely Vegetated",
    16: "Hardwood",
    17: "Conifer-Hardwood",
    18: "Conifer",
    19: "Barren",
}



layers = {
    "drought__D1": {
        "path": "/Users/kylabazlen/Documents/Climate_Roadmap/clim_data/pct_change_Aridity/pct_change_Aridity_*_D1_timescale_12months.tif",
        "subtype": "rel-change",
        "vmin": None,
        "vmax": None,
        "label": "Change in D1 Drought Exposure",
        "cbar_label": "Drought Exposure"
    },
    "drought__D2": {
        "path": "/Users/kylabazlen/Documents/Climate_Roadmap/clim_data/pct_change_Aridity/pct_change_Aridity_*_D2_timescale_12months.tif",
        "subtype": "rel-change",
        "vmin": None,
        "vmax": None,
        "label": "Change in D2 Drought Exposure",
        "cbar_label": "Drought Exposure"
    },
    "drought__D3": {
        "path": "/Users/kylabazlen/Documents/Climate_Roadmap/clim_data/pct_change_Aridity/pct_change_Aridity_*_D3_timescale_12months.tif",
        "subtype": "rel-change",
        "vmin": None,
        "vmax": None,
        "label": "Change in D3 Drought Exposure",
        "cbar_label": "Drought Exposure"
    },
    "drought__D4": {
        "path": "/Users/kylabazlen/Documents/Climate_Roadmap/clim_data/pct_change_Aridity/pct_change_Aridity_*_D4_timescale_12months.tif",
        "subtype": "rel-change",
        "vmin": None,
        "vmax": None,
        "label": "Change in D4 Drought Exposure",
        "cbar_label": "Drought Exposure"
    },
    "snowfall": {
        "path": "/Users/kylabazlen/Documents/Climate_Roadmap/clim_data/snow_fraction/snow_fraction_relative_apr.tif",
        "subtype": "rel-change",
        "vmin": None,
        "vmax": None,
        "label": "Difference in Percent of Precipitation Received as Snow (April)",
        "cbar_label": "Snowfall"
    },
    "Days Exceeding 95th Percentile Maximum Temperature": {
        "path": "/Users/kylabazlen/Documents/Climate_Roadmap/clim_data/severe_heat/TX95p_GWL*C_minus_REF_absoule_change_v2.tif",
        "subtype": "abs-change",
        "cmap": "Reds",
        "vmin": None,
        "vmax": None,
        "label": "Days Exceeding 95th Percentile Maximum Temperature",
        "cbar_label": "Days"
    },
    "Change in Number of Frost Days": {
        "path": "/Users/kylabazlen/Documents/Climate_Roadmap/clim_data/FD/FD_GWL*C_minus_REF_absoule_change_v2.tif",
        "subtype": "abs-change",
        "cmap": "PuBu_r",
        "vmin": None,
        "vmax": None,
        "label": "Change in Number of Frost Days",
        "cbar_label": "Days"
    },
    "Rx1day": {
        "path": "/Users/kylabazlen/Documents/Climate_Roadmap/clim_data/Rx1day/Rx1day_GWL*C_minus_REF_absoule_change_v2.tif",
        "subtype": "abs-change",
        "vmin": None,
        "vmax": None,
        "label": "Change in Maximum 1-Day Precipitation",
        "cbar_label": "mm"
    },
    "Rx1day__5day": {
        "path": "/Users/kylabazlen/Documents/Climate_Roadmap/clim_data/Rx5day/Rx5day_GWL*C_minus_REF_absoule_change_v2.tif",
        "subtype": "abs-change",
        "vmin": None,
        "vmax": None,
        "label": "Change in Maximum 5-Day Precipitation",
        "cbar_label": "mm"
    },
}
def shapely_to_mpl_path(geom):
    "Convert a Shapely geometry to a Matplotlib Path object"
    vertices, codes = [], []
    for poly in (geom.geoms if geom.geom_type == "MultiPolygon" else [geom]):
        for ring in [poly.exterior] + list(poly.interiors):
            coords = np.array(ring.coords)
            vertices.append(coords)
            codes.append([MplPath.MOVETO] + [MplPath.LINETO] * (len(coords) - 2) + [MplPath.CLOSEPOLY])
    return MplPath(np.concatenate(vertices), np.concatenate(codes))

def plot_comap(gdf, figsize=(14, 10), title=None,
               dpi=150, crs="EPSG:4326", edgecolor="none", linewidth=0.1):
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    gdf_plot = gdf.to_crs(crs) if crs else gdf.copy()
    colors   = gdf_plot["FinalModSt"].map(FINALMODST_COLORS).fillna("#cccccc")
    order    = [k for k in FINALMODST_ORDER if k in gdf_plot["FinalModSt"].values]

    fig, ax = plt.subplots(figsize=figsize)
    gdf_plot.plot(ax=ax, color=colors, edgecolor=edgecolor, linewidth=linewidth)

    patches = [mpatches.Patch(color=FINALMODST_COLORS[k], label=FINALMODST_LABELS[k])
            for k in order]
    ax.legend(handles=patches, title=FINALMODST_LEGEND_TITLE,
            loc="upper left", bbox_to_anchor=(1, .75),
            fontsize=8, title_fontsize=9, framealpha=0.9)
    ax.set_axis_off()
    plt.tight_layout()

    return fig, ax


def compute_extent(transform, width, height):
    """
    Compute matplotlib imshow extent [left, right, bottom, top] from a
    rasterio transform and grid dimensions.
    """
    left, bottom, right, top = array_bounds(height, width, transform)
    return [left, right, bottom, top]

def plot_bivariate_map(bivar_map, extent, color_dict, ax, alpha=0.8, zorder=2):
    """
    Overlay a bivariate class raster on an existing axes.

    `bivar_map` should contain class codes 0..N-1 for valid pixels and a
    sentinel (e.g. -1) for invalid pixels. The sentinel is rendered
    transparent.

    Parameters
    ----------
    bivar_map : 2D np.ndarray of ints
    extent : [left, right, bottom, top]
    color_dict : dict {int code -> color}
        Must cover every valid class code.
    ax : matplotlib Axes
    alpha : float
    zorder : int
    """
    n_codes = len(color_dict)
    # Transparent slot at index 0, then class colors at 1..n_codes
    cmap = ListedColormap([(1, 1, 1, 0)] + [color_dict[i] for i in range(n_codes)])

    ax.imshow(
        bivar_map + 1,               # shift so -1 (invalid) -> 0 (transparent)
        cmap=cmap,
        vmin=0, vmax=n_codes,
        extent=extent,
        origin="upper",
        interpolation="nearest",
        alpha=alpha,
        zorder=zorder,
    )


def add_bivariate_legend(
    fig,
    color_dict,
    x_label,
    y_label,
    n_classes=3,
    position=(0.92, 0.12, 0.24, 0.34),
    fontsize=13,
    arrow_lw=1.6,
    box_lw=1.8,
):
    """
    Add an n x n bivariate legend inset to a figure.

    Columns = x variable (low -> high, left -> right).
    Rows    = y variable (low -> high, bottom -> top).

    Parameters
    ----------
    fig : matplotlib Figure
    color_dict : dict {code -> color}, code = row * n_classes + col
    x_label, y_label : str
        Axis labels for the legend (typically "<var> →").
    n_classes : int
    position : (left, bottom, width, height) in figure coords
    """
    legend_ax = fig.add_axes(list(position))

    for i in range(n_classes):       # rows (y, bottom = low)
        for j in range(n_classes):   # cols (x, left = low)
            code = i * n_classes + j
            legend_ax.add_patch(plt.Rectangle(
                (j, i), 1, 1,
                facecolor=color_dict[code],
                edgecolor="white", linewidth=box_lw,
            ))

    pad = 0.3
    legend_ax.set_xlim(-pad, n_classes + pad)
    legend_ax.set_ylim(-(pad + 0.4), n_classes + pad + 0.2)
    legend_ax.set_aspect("equal")
    legend_ax.set_xticks([])
    legend_ax.set_yticks([])
    legend_ax.spines[:].set_visible(False)

    # Arrows along the bottom and left edges
    legend_ax.annotate("", xy=(n_classes + 0.15, 0), xytext=(0, 0),
                       arrowprops=dict(arrowstyle="->", color="black", lw=arrow_lw))
    legend_ax.annotate("", xy=(0, n_classes + 0.15), xytext=(0, 0),
                       arrowprops=dict(arrowstyle="->", color="black", lw=arrow_lw))

    legend_ax.text(n_classes / 2, -0.6, x_label, ha="center", fontsize=fontsize)
    legend_ax.text(-0.55, n_classes / 2, y_label,
                   ha="center", fontsize=fontsize, rotation=90)

    return legend_ax


def plot_elevation_scatter(
    cs_arr,
    hazard_arr,
    elev_arr,
    bivar_colors,
    hazard_label="Hazard",
    title=None,
    n_classes=3,
    point_size=8,
    alpha=0.8,
    max_points=50_000,
    figsize=(10, 7),
):
    """
    Scatter plot of elevation vs. Conservation × Hazard product, colored by
    bivariate nonant class.

    Parameters
    ----------
    cs_arr, hazard_arr, elev_arr : 2D np.ndarray
        Aligned arrays (same shape). Can contain NaN for invalid pixels.
    bivar_colors : dict {int -> color}
        9-class bivariate color mapping.
    hazard_label : str
        Label for the hazard axis/legend.
    title : str or None
        Plot title. Auto-generated if None.
    n_classes : int
        Number of classes per axis (default 3 → 9 nonants).
    max_points : int
        Subsample to this many points for faster rendering.
    figsize : tuple

    Returns
    -------
    fig, (ax, legend_ax)
    """
    # Flatten and mask to valid
    cs_flat = cs_arr.flatten()
    haz_flat = hazard_arr.flatten()
    elev_flat = elev_arr.flatten()

    mask = np.isfinite(cs_flat) & np.isfinite(haz_flat) & np.isfinite(elev_flat)
    cs_v = cs_flat[mask]
    haz_v = haz_flat[mask]
    elev_v = elev_flat[mask]

    # Compute product and bivariate class codes
    product = cs_v * haz_v
    qs = np.linspace(0, 1, n_classes + 1)[1:-1]
    cs_breaks = np.quantile(cs_v, qs)
    haz_breaks = np.quantile(haz_v, qs)
    codes = np.digitize(haz_v, haz_breaks) * n_classes + np.digitize(cs_v, cs_breaks)

    # Subsample if needed
    if len(product) > max_points:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(product), size=max_points, replace=False)
        product = product[idx]
        elev_v = elev_v[idx]
        codes = codes[idx]

    colors = np.array([bivar_colors[c] for c in codes])

    if title is None:
        title = f"Elevation vs. Conservation × {hazard_label}, colored by nonant"

    fig, ax = plt.subplots(figsize=figsize)
    ax.scatter(product, elev_v, c=colors, s=point_size, alpha=alpha, edgecolors="none")
    ax.set_xlabel(f"Conservation score × {hazard_label.lower()}", fontsize=12)
    ax.set_ylabel("Elevation (m)", fontsize=12)
    ax.set_title(title, fontsize=13, fontweight="bold")

    plt.subplots_adjust(right=0.78)

    legend_ax = fig.add_axes([0.82, 0.25, 0.15, 0.28])
    for i in range(n_classes):
        for j in range(n_classes):
            code = i * n_classes + j
            legend_ax.add_patch(plt.Rectangle(
                (j, i), 1, 1,
                facecolor=bivar_colors[code],
                edgecolor="white", linewidth=1.5,
            ))
    legend_ax.set_xlim(-0.3, n_classes + 0.3)
    legend_ax.set_ylim(-0.7, n_classes + 0.5)
    legend_ax.set_aspect("equal")
    legend_ax.set_xticks([])
    legend_ax.set_yticks([])
    legend_ax.spines[:].set_visible(False)
    legend_ax.annotate("", xy=(n_classes + 0.15, 0), xytext=(0, 0),
                       arrowprops=dict(arrowstyle="->", color="black", lw=1.4))
    legend_ax.annotate("", xy=(0, n_classes + 0.15), xytext=(0, 0),
                       arrowprops=dict(arrowstyle="->", color="black", lw=1.4))
    legend_ax.text(n_classes / 2, -0.6, "Conservation →", ha="center", fontsize=9)
    legend_ax.text(-0.5, n_classes / 2, f"{hazard_label} →", ha="center", fontsize=9, rotation=90)

    return fig, (ax, legend_ax)


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