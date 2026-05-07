import matplotlib.pyplot as plt
import geopandas as gpd
import numpy as np
import rioxarray as rxr
import rasterio
from matplotlib.colors import ListedColormap, Normalize, TwoSlopeNorm

COUNTIES_PATH = "/Users/kylabazlen/Documents/Climate_Roadmap/co-risk-assessment/functions/supporting_data_for_hillshade/Colorado_County_Boundaries.shp"
TARGET_CRS = "EPSG:3857"

def plt_counties(
    county_boundaries: str,
    county_color: str = "none",
    county_edgecolor: str = "black",
    county_linewidth: float = 0.6,
    figsize: tuple = (10, 8),
    ax: plt.Axes = None,
    zorder: float = 3,
    target_crs: str = "EPSG:3857",
) -> tuple[plt.Figure, plt.Axes]:
    """Draw county outlines reprojected to `target_crs`.

    Parameters
    ----------
    county_boundaries : str
        Path to the county polygon layer.
    county_color : str
        Fill color. Default 'none' (no fill).
    county_edgecolor : str
        Outline color.
    county_linewidth : float
        Outline width.
    figsize : tuple
        Figure size if creating a new figure.
    ax : matplotlib Axes, optional
        Existing Axes to draw into. If None, a new Figure + Axes is created.
    zorder : float
        Drawing order — higher draws on top. Default 3 so counties sit above
        rasters drawn at zorder=2.
    target_crs : str
        CRS to reproject counties into before plotting.

    Returns
    -------
    fig, ax
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure

    counties = gpd.read_file(county_boundaries)
    if counties.crs is None:
        counties = counties.set_crs("EPSG:4326")
    counties = counties.to_crs(target_crs)

    counties.plot(
        ax=ax,
        color=county_color,
        edgecolor=county_edgecolor,
        linewidth=county_linewidth,
        zorder=zorder,
    )

    ax.set_aspect("equal")
    return fig, ax

def reproject_raster(src_path, dst_crs=TARGET_CRS):
    """Read a raster and reproject to dst_crs in memory. Returns (array, extent)."""
    da = rxr.open_rasterio(src_path, masked=True).squeeze().rio.reproject(dst_crs)
    left, bottom, right, top = da.rio.bounds()
    return np.ma.masked_invalid(da.values), [left, right, bottom, top]


def expand_values(values, vmin, vmax, n_colors):
    """Expand a '...' placeholder into n_colors evenly-spaced labels."""
    if values == ["..."] or values is None:
        return list(np.linspace(vmin, vmax, n_colors))
    return values

def build_cmap_norm(cfg, cbar_spec, raster_path=None):
    """Build (cmap, norm, labels) using JSON hex colors with layer-specified vmin/vmax/center."""
    spec = cbar_spec[cfg["variable"]]["subtypes"][cfg["subtype"]]
    cmap = ListedColormap(spec["colors"])
    cmap.set_bad("none")

    vmin = cfg.get("vmin")
    vmax = cfg.get("vmax")
    center = cfg.get("center")

    if vmin is None or vmax is None:
        if raster_path is None:
            raise ValueError("raster_path required when vmin/vmax aren't both set")
        with rasterio.open(raster_path) as src:
            data = src.read(1, masked=True).compressed()
        if data.size == 0:
            data_min, data_max = -1.0, 1.0
        else:
            data_min, data_max = float(np.nanmin(data)), float(np.nanmax(data))

        if center is not None:
            half = max(abs(data_max - center), abs(data_min - center))
            if vmin is None:
                vmin = center - half
            if vmax is None:
                vmax = center + half
        else:
            if vmin is None:
                vmin = data_min
            if vmax is None:
                vmax = data_max

    if center is not None:
        norm = TwoSlopeNorm(vcenter=center, vmin=vmin, vmax=vmax)
    else:
        norm = Normalize(vmin=vmin, vmax=vmax)

    # Expand "..." placeholder into evenly-spaced labels
    labels = expand_values(spec.get("values"), vmin, vmax, len(spec["colors"]))

    return cmap, norm, labels
