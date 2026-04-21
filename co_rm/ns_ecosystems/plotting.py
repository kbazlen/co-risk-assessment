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