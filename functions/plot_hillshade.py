"""Plot cities over a Whitebox hillshade of a topography NetCDF."""

import os
import tempfile

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.transform import from_bounds
import xarray as xr

from pathlib import Path

# At the top of the file (after imports)
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "supporting_data_for_hillshade"
# Colorado state bounding box (lon_min, lat_min, lon_max, lat_max), WGS84
COLORADO_BBOX = (-109.05, 36.99, -102.04, 41.01)


# Names for the 15 points in cities_of_interest.shp, in row order.
# Each was reverse-matched to the nearest canonical Colorado municipality
# (max distance 9.2 km; most under 2 km, all unambiguous).
CITY_NAMES = [
    "Aurora",            #  0  (-104.7275,  39.7084)
    "Boulder",           #  1  (-105.2515,  40.0273)
    "Colorado Springs",  #  2  (-104.7606,  38.8674)
    "Craig",             #  3  (-107.5557,  40.5170)
    "Denver",            #  4  (-104.9893,  39.7627)
    "Durango",           #  5  (-107.8703,  37.2750)
    "Fort Collins",      #  6  (-105.0657,  40.5478)
    "Glenwood Springs",  #  7  (-107.3344,  39.5454)
    "Grand Junction",    #  8  (-108.5675,  39.0878)
    "Greeley",           #  9  (-104.7707,  40.4149)
    "Gunnison",          # 10  (-106.9246,  38.5490)
    "Lamar",             # 11  (-102.6152,  38.0737)
    "Montrose",          # 12  (-107.8594,  38.4688)
    "Pueblo",            # 13  (-104.6131,  38.2706)
    "Trinidad",          # 14  (-104.4908,  37.1749)
]


def _dem_to_geotiff(elev_da, lon_name, lat_name, out_path):
    """Write an xarray DataArray DEM to a GeoTIFF (WGS84) for Whitebox."""
    arr = elev_da.values.astype("float32")
    lons = elev_da[lon_name].values
    lats = elev_da[lat_name].values

    # imshow/rasterio expect rows to go top -> bottom (descending lat)
    if lats[0] < lats[-1]:
        arr = arr[::-1, :]
        lats = lats[::-1]

    lon_min, lon_max = float(lons.min()), float(lons.max())
    lat_min, lat_max = float(lats.min()), float(lats.max())
    height, width = arr.shape
    transform = from_bounds(lon_min, lat_min, lon_max, lat_max, width, height)

    with rasterio.open(
        out_path, "w",
        driver="GTiff", height=height, width=width, count=1,
        dtype="float32", crs="EPSG:4326", transform=transform,
    ) as dst:
        dst.write(arr, 1)

    return lon_min, lon_max, lat_min, lat_max


def _whitebox_hillshade(dem_tif, hs_tif, azimuth=315.0, altitude=45.0, zfactor=1.0):
    """Run WhiteboxTools Hillshade. Downloads the binary on first use."""
    import whitebox
    wbt = whitebox.WhiteboxTools()
    wbt.verbose = False
    wbt.hillshade(
        dem=dem_tif,
        output=hs_tif,
        azimuth=azimuth,
        altitude=altitude,
        zfactor=zfactor,
    )


def _whitebox_diff_from_mean(dem_tif, out_tif, filterx=25, filtery=25):
    """Run WhiteboxTools DiffFromMeanElev. High-pass residual of the DEM:
    ridges positive, valleys negative. filterx/filtery must be odd."""
    import whitebox
    wbt = whitebox.WhiteboxTools()
    wbt.verbose = False
    if filterx % 2 == 0:
        filterx += 1
    if filtery % 2 == 0:
        filtery += 1
    wbt.diff_from_mean_elev(
        dem=dem_tif,
        output=out_tif,
        filterx=filterx,
        filtery=filtery,
    )


def plot_hillshade(
    shp_path,
    nc_path,
    elev_var="HGT",
    lon_name="longitude",
    lat_name="latitude",
    bbox=COLORADO_BBOX,
    downsample=1,
    color_map="Greys_r",
    method="diff_from_mean",
    filter_size=25,
    city_names="default",
    azimuth=315.0,
    altitude=55.0,
    zfactor=0.00001,   # degrees -> meters fudge, see docstring
    cmap=None,
    topo_alpha=0.6,
    city_color="crimson",
    city_size=50,
    label_fontsize=9,
    label_offset=(0.04, 0.04),
    figsize=(12, 8),
    ax=None,
):
    """Plot a Whitebox hillshade under city points + labels.

    Parameters
    ----------
    shp_path, nc_path : str
        Paths to the cities shapefile and the elevation NetCDF.
    elev_var, lon_name, lat_name : str
        Variable/coord names inside the NetCDF.
    bbox : (lon_min, lat_min, lon_max, lat_max) or None
        Crop window. Defaults to Colorado.
    downsample : int
        Coarsen the DEM by this integer factor before computing the terrain.
        1 (default) = full native resolution (~180m, very detailed). Use 4-8
        for a smoother, less granular look.
    method : {"diff_from_mean", "hillshade"}
        Which Whitebox terrain tool to use. "diff_from_mean" (default) runs
        DiffFromMeanElev, which subtracts a local-neighborhood mean from
        each cell — ridges come out light, valleys dark, no sun-angle needed.
        "hillshade" runs the classic shaded-relief tool using azimuth/altitude.
    filter_size : int
        Neighborhood size (cells) for DiffFromMeanElev, applied in both x
        and y. Must be odd (auto-bumped if even). Larger = coarser features
        show up; smaller = fine ridges only. Default 25. Ignored for hillshade.
    city_names : list[str], "default", or None
        Names to label each city. Must match the shapefile row order.
        "default" (the default) uses the baked-in CITY_NAMES list for the
        15 points in cities_of_interest.shp. Pass a list to override, or
        None to skip labels entirely.
    azimuth, altitude, zfactor : floats
        Whitebox Hillshade params. Sun position in degrees.
        zfactor scales elevation to match the horizontal units — when the DEM
        is in DEGREES but elevation is in METERS, you need a small zfactor
        (~1e-5) or the hillshade saturates. For a projected DEM (meters/meters),
        use zfactor=1.
    cmap : str
        Colormap for the hillshade. 'Greys_r' = dark shadows, light sun-lit faces.
    topo_alpha : float
        Transparency of the hillshade layer (0-1).
    city_color, city_size, label_fontsize : styling.
    label_offset : (dlon, dlat)
        Offset applied to each label from its point, in data coords.
    figsize : tuple
        Figure size if creating a new one.
    ax : matplotlib Axes, optional.

    Returns
    -------
    (fig, ax)
    """
    os.environ.setdefault("SHAPE_RESTORE_SHX", "YES")

    if city_names == "default":
        city_names = CITY_NAMES

    # --- Load ---
    cities = gpd.read_file(shp_path)
    ds = xr.open_dataset(nc_path)
    elev = ds[elev_var]

    # --- Crop raster ---
    if bbox is not None:
        lon_min, lat_min, lon_max, lat_max = bbox
        lat_vals = ds[lat_name].values
        lat_slice = (
            slice(lat_max, lat_min) if lat_vals[0] > lat_vals[-1]
            else slice(lat_min, lat_max)
        )
        elev = elev.sel({lon_name: slice(lon_min, lon_max), lat_name: lat_slice})

    # --- Downsample for a smoother hillshade ---
    if downsample and downsample > 1:
        elev = elev.coarsen(
            {lat_name: downsample, lon_name: downsample},
            boundary="trim",
        ).mean()

    # --- Whitebox terrain raster via temp GeoTIFFs ---
    with tempfile.TemporaryDirectory() as tmp:
        dem_tif = os.path.join(tmp, "dem.tif")
        out_tif = os.path.join(tmp, "out.tif")
        lon_min, lon_max, lat_min, lat_max = _dem_to_geotiff(
            elev, lon_name, lat_name, dem_tif,
        )
        if method == "hillshade":
            _whitebox_hillshade(dem_tif, out_tif, azimuth, altitude, zfactor)
            default_cmap = color_map
            symmetric = False
        elif method == "diff_from_mean":
            _whitebox_diff_from_mean(dem_tif, out_tif, filter_size, filter_size)
            default_cmap = color_map  # dark = below local mean, light = above
            symmetric = True
        else:
            raise ValueError(f"Unknown method: {method!r}")
        with rasterio.open(out_tif) as src:
            terrain = src.read(1).astype("float32")
            nodata = src.nodata
            if nodata is not None:
                terrain = np.where(terrain == nodata, np.nan, terrain)

    extent = (lon_min, lon_max, lat_min, lat_max)

    # --- Plot ---
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure

    # Resolve cmap: if caller left it at the default, pick a sensible one.
    active_cmap = default_cmap if cmap is None else cmap

    # For DFME, center the color scale on zero so ridges and valleys
    # are symmetric around neutral grey. Clip extremes at the 2nd/98th
    # percentile so a few outliers don't wash out the rest.
    if symmetric:
        finite = terrain[np.isfinite(terrain)]
        vlim = float(np.nanpercentile(np.abs(finite), 98)) if finite.size else 1.0
        vmin, vmax = -vlim, vlim
    else:
        vmin = vmax = None

    ax.imshow(
        terrain, extent=extent, origin="upper",
        cmap=active_cmap, alpha=topo_alpha, interpolation="bilinear",
        vmin=vmin, vmax=vmax,
    )

    # Filter cities (and names) to what's in view
    if bbox is not None:
        in_mask = cities.geometry.apply(
            lambda g: lon_min <= g.x <= lon_max and lat_min <= g.y <= lat_max
        )
        view_cities = cities[in_mask].reset_index(drop=True)
        view_names = (
            [n for n, keep in zip(city_names, in_mask) if keep]
            if city_names is not None else None
        )
    else:
        view_cities = cities
        view_names = city_names

    view_cities.plot(
        ax=ax, color=city_color, markersize=city_size,
        edgecolor="black", linewidth=0.6, zorder=5,
    )

    # Labels
    if view_names is not None:
        dx, dy = label_offset
        for (_, row), name in zip(view_cities.iterrows(), view_names):
            ax.annotate(
                name,
                xy=(row.geometry.x, row.geometry.y),
                xytext=(row.geometry.x + dx, row.geometry.y + dy),
                fontsize=label_fontsize, fontweight="bold",
                color="black", zorder=6,
                path_effects=[],  # keep simple; add stroke below if you want
            )

    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    # For lon/lat plots, 1 degree of lon != 1 degree of lat. At ~39 N,
    # 1 deg lon ~ 86 km but 1 deg lat ~ 111 km. Using aspect='equal' would
    # stretch the map horizontally by ~29%. Correct with 1/cos(mid-latitude).
    mid_lat = 0.5 * (extent[2] + extent[3])
    ax.set_aspect(1.0 / np.cos(np.deg2rad(mid_lat)))
    ax.set_axis_off()

    ds.close()
    return fig, ax


if __name__ == "__main__":
    fig, ax = plot_hillshade(
        str(DATA_DIR / "cities_of_interest.shp"),
        str(DATA_DIR / "COtopography.nc"),
        downsample=1,
        color_map="Greys_r",
        topo_alpha=0.3,
        method="hillshade",
        zfactor=0.05,
        azimuth=320.0,
        altitude=25.0,
    )


