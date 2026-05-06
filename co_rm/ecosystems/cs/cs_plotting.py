import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from constants import *

def plot_comap(gdf, ax=None, figsize=(14, 10), title=None,
               dpi=150, crs="EPSG:3857", edgecolor="none", linewidth=0.1):
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:26913", allow_override=True)
    gdf_plot = gdf.to_crs(crs) if crs else gdf.copy()

    colors = gdf_plot["FinalModSt"].map(FINALMODST_COLORS).fillna("#cccccc")
    order  = [k for k in FINALMODST_ORDER if k in gdf_plot["FinalModSt"].values]

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    else:
        fig = ax.figure

    gdf_plot.plot(ax=ax, color=colors, edgecolor=edgecolor, linewidth=linewidth)

    patches = [mpatches.Patch(color=FINALMODST_COLORS[k], label=FINALMODST_LABELS[k])
               for k in order]
    ax.legend(handles=patches, title=FINALMODST_LEGEND_TITLE,
              loc="upper left", bbox_to_anchor=(1, .75),
              fontsize=8, title_fontsize=9, framealpha=0.9)
    if title:
        ax.set_title(title)
    ax.set_axis_off()
    return fig, ax
