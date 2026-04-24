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

VEGETATION_VAT = [
    (1,  "Agriculture",        (255, 217, 109)),
    (3,  "Grassland",          (229, 255, 229)),
    (5,  "Lodgepole Pine",     (115, 255, 191)),
    (6,  "Mixed Conifer",      (106, 60, 140)),
    (7,  "Oak Shrubland",      (250, 111, 96)),
    (8,  "Open Water",         (0, 112, 255)),
    (9,  "Pinyon-Juniper",     (179, 119, 59)),
    (10, "Ponderosa Pine",     (0, 102, 0)),
    (11, "Riparian",           (0, 0, 126)),
    (12, "Shrubland",          (236, 224, 182)),
    (13, "Spruce-Fir",         (164, 145, 243)),
    (14, "Developed",          (191, 191, 191)),
    (15, "Sparsely Vegetated", (100, 100, 100)),
    (16, "Hardwood",           (255, 255, 0)),
    (17, "Conifer-Hardwood",   (209, 255, 115)),
    (18, "Conifer",            (56, 168, 0)),
    (19, "Barren",             (255, 255, 255)),
]

def plot_raster_categorical(path, vat, title="", nodata=None, downsample=True, ax=None):
    """
    Designed for rasters from the Colorado Forest Atlas
    vat: list of (code, label, (R, G, B)) tuples
    
    """
    dst_crs = CRS.from_epsg(4326)

    # build lookup
    codes      = np.array([v[0] for v in vat])
    labels     = [v[1] for v in vat]
    colors     = np.array([v[2] for v in vat]) / 255.0
    color_dict = dict(zip(codes, colors))

    with rasterio.open(path) as src:
        nodata_val = nodata if nodata is not None else src.nodata
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds
        )

        if downsample:
            out_width  = width  // 4
            out_height = height // 4
            out_transform = transform * transform.scale(width / out_width, height / out_height)
        else:
            out_width, out_height, out_transform = width, height, transform

        out_data = np.empty((out_height, out_width), dtype=np.float32)
        reproject(
            source=rasterio.band(src, 1),
            destination=out_data,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=out_transform,
            dst_crs=dst_crs,
            resampling=Resampling.nearest,   # always nearest for categorical
            src_nodata=nodata_val,
            dst_nodata=np.nan,
        )

    left   = out_transform.c
    top    = out_transform.f
    right  = left + out_transform.a * out_width
    bottom = top  + out_transform.e * out_height

    # build RGB array
    data = out_data.astype(float)
    mask = np.isnan(data)
    rgb  = np.zeros(data.shape + (4,), dtype=float)  # RGBA so we can set alpha
    for code, col in color_dict.items():
        rgb[data == code, :3] = col
        rgb[data == code,  3] = 1.0   # opaque
    rgb[mask, 3] = 0.0  # transparent nodata

    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 10))
    else:
        fig = ax.figure

    img = ax.imshow(rgb, extent=[left, right, bottom, top], origin="upper")

    ax.set_title(title, fontsize=16)

    # legend instead of colorbar
    present_codes = np.unique(data[~mask]).astype(int)
    patches = [
        mpatches.Patch(color=color_dict[c], label=labels[list(codes).index(c)])
        for c in present_codes if c in color_dict
    ]
    ax.legend(
        handles=patches,
        loc='upper left',
        bbox_to_anchor=(1.01, 1),
        borderaxespad=0,
        fontsize=9,
        frameon=False,
    )
    fig.subplots_adjust(right=0.78)

    return fig, ax, img