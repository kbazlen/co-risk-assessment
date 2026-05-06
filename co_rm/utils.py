import matplotlib.pyplot as plt
import geopandas as gpd
import re

COUNTIES_PATH = "/Users/kylabazlen/Documents/Climate_Roadmap/co-risk-assessment/functions/supporting_data_for_hillshade/Colorado_County_Boundaries.shp"

def plt_counties(
    county_boundaries: str,
    county_color: str = "none",
    county_edgecolor: str = "black",
    county_linewidth: float = 0.7,
    figsize: tuple = (10, 8),
    ax: plt.Axes = None,
) -> tuple[plt.Figure, plt.Axes]:
    """Draw county outlines reprojected to EPSG:3857.

    Parameters
    ----------
    county_boundaries : str
        File path to the polygon layer for county outlines.
    county_color : str
        Fill color for counties. Default 'none' (no fill).
    county_edgecolor : str
        Outline color for counties.
    county_linewidth : float
        Outline width for counties.
    figsize : tuple
        Figure size if creating a new one.
    ax : matplotlib Axes, optional
        Pass an existing Axes to draw into. If None, a new Figure + Axes is created.

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
        counties = counties.set_crs("EPSG:4326")  # assume lon/lat if missing
    counties = counties.to_crs("EPSG:3857")

    counties.plot(
        ax=ax,
        color=county_color,
        edgecolor=county_edgecolor,
        linewidth=county_linewidth,
    )

    ax.set_aspect("equal")
    ax.set_axis_off()
    return fig, ax



def extract_gwl(filename):
    """Pull a GWL label like '2C' or '1.5C' out of a tif filename. Returns None if not found."""
    match = re.search(r'GWL([\d.]+)C', filename)
    if match:
        return f"{match.group(1)}°C"
    # fallback: check for other common patterns (e.g. ssp245, D2, etc.)
    return None