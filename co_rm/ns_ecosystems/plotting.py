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