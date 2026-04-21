"""
Reusable plotting functions for consistant basemaps 
"""
 
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


DEFAULT_STYLE = {
    "county_color":     "none",
    "county_edgecolor": "black",
    "county_linewidth": 0.7,
    "city_color":       "black",
    "city_markersize":  5,
    "city_zorder":      2,
    "label_color":      "black",
    "label_fontsize":   12,
    "label_offset":     (0, 2),      # (x, y) in points
    "figsize":          (10, 8),
}

DEFAULT_PATHS = {
    "county_boundaries": "/Users/kylabazlen/Documents/Climate_Roadmap/spatial_data/Colorado_County_Boundaries/Colorado_County_Boundaries.shp",
    "cities": "/Users/kylabazlen/Documents/Climate_Roadmap/spatial_data/Colorado_Cities/co-municipalities.shp"
}

CUSTOM_OFFSETS = {
    "Denver":  "right",
    "Fort Collins": "right",
}


def make_basemap(
    county_boundaries: str = None,
    cities: str = None,
    custom_offsets: dict = None,
    style: dict = None,
    ax: plt.Axes = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    Draw the county + city base map.

    Parameters
    ----------
    county_boundaries : str, optional
        File path to the polygon layer for county outlines.
    cities : str, optional
        File path to the point layer; must have a 'Municipali' column and a geometry column.
    custom_offsets : dict, optional
        {city_name: ha_value} overrides for label horizontal alignment.
        Defaults to 'left' for every city.
    style : dict, optional
        Override any key from DEFAULT_STYLE.
    ax : matplotlib Axes, optional
        Pass an existing Axes to draw into (useful when composing subplots).
        If None, a new Figure + Axes is created.

    Returns
    -------
    fig, ax
    """
    s = {**DEFAULT_STYLE, **(style or {})}
    custom_offsets = custom_offsets or {}

    if ax is None:
        fig, ax = plt.subplots(figsize=s["figsize"])
    else:
        fig = ax.figure

    # --- Base layers ---
    if county_boundaries is not None:
        gpd.read_file(county_boundaries).plot(
            ax=ax,
            color=s["county_color"],
            edgecolor=s["county_edgecolor"],
            linewidth=s["county_linewidth"],
        )

    if cities is not None:
        cities_gdf = gpd.read_file(cities)
        cities_gdf.plot(
            ax=ax,
            color=s["city_color"],
            markersize=s["city_markersize"],
            zorder=s["city_zorder"],
        )


        for _, row in cities_gdf.iterrows():
            name = row["Municipali"]
            ha = custom_offsets.get(name, "left")
            ax.annotate(
                name,
                xy=(row.geometry.x, row.geometry.y),
                fontsize=s["label_fontsize"],
                color=s["label_color"], 
                ha=ha,
                xytext=s["label_offset"],
                textcoords="offset points",
            )

    ax.set_axis_off()

    return fig, ax

def plot_raster(path, cmap="viridis", title="", cbar_label="", vmin=None, vmax=None,
                nodata=None, ax=None):
    """
    Plot a raster file with reprojection to Web Mercator (EPSG:4326).
    
    Parameters
    ----------
    path : str
        Path to the raster file.
    cmap : str, optional
        Matplotlib colormap name (default: "viridis").
    title : str, optional
        Plot title (default: "").
    cbar_label : str, optional
        Colorbar label (default: "").
    vmin : float, optional
        Minimum value for colormap normalization. If None, uses data minimum.
    vmax : float, optional
        Maximum value for colormap normalization. If None, uses data maximum.
    nodata : float, optional
        Value to treat as missing data. If None, uses raster's nodata value.
    ax : matplotlib.axes.Axes, optional
        Axes to plot on. If None, creates a new figure.
    
    Returns
    -------
    fig : matplotlib.figure.Figure
        The figure object.
    ax : matplotlib.axes.Axes
        The axes object.
    img : matplotlib.image.AxesImage
        The image object.
    """
    dst_crs = CRS.from_epsg(4326)

    with rasterio.open(path) as src:
        print(f"Source CRS: {src.crs}")
        print(f"Target CRS: {dst_crs}")
        
        if nodata is None:
            nodata = src.nodata
        
        if src.crs == dst_crs:
            print("✓ Already in target CRS, skipping reprojection")
            out_data = src.read(1).astype(np.float32)
            transform = src.transform
            width = src.width
            height = src.height
        else:
            print("→ Reprojecting to target CRS")
            transform, width, height = calculate_default_transform(
                src.crs, dst_crs, src.width, src.height, *src.bounds
            )
            out_data = np.empty((height, width), dtype=np.float32)
            reproject(
                source=rasterio.band(src, 1),
                destination=out_data,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs=dst_crs,
                resampling=Resampling.nearest,
                src_nodata=nodata,
                dst_nodata=np.nan,
            )

    # Handle nodata values
    if nodata is not None:
        out_data[out_data == nodata] = np.nan

    # Calculate extent
    left = transform.c
    top = transform.f
    right = left + transform.a * width
    bottom = top + transform.e * height

    # Create figure if needed
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 10))
    else:
        fig = ax.figure

    # Set vmin/vmax from data if not provided
    if vmin is None:
        vmin = np.nanmin(out_data)
    if vmax is None:
        vmax = np.nanmax(out_data)

    # Plot
    img = ax.imshow(
        out_data, cmap=cmap, vmin=vmin, vmax=vmax,
        extent=[left, right, bottom, top], origin="upper",
    )

    ax.set_title(title, fontsize=16)
    cbar = plt.colorbar(img, ax=ax, fraction=0.03, pad=0.01, shrink=0.5)
    cbar.set_label(cbar_label, fontsize=12)

    return fig, ax, img