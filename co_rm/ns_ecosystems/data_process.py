from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.warp import reproject, calculate_default_transform
from rasterio.enums import Resampling



def build_reference_grid(path, dst_crs="EPSG:4326"):
    """
    Build a destination grid (transform, width, height) in `dst_crs` that
    matches the resolution of the raster at `path`.

    Returns
    -------
    transform : affine.Affine
    width     : int
    height    : int
    """
    with rasterio.open(path) as ref:
        transform, width, height = calculate_default_transform(
            ref.crs, dst_crs, ref.width, ref.height, *ref.bounds
        )
    return transform, width, height


def reproject_to_grid(
    path,
    dst_transform,
    dst_width,
    dst_height,
    dst_crs="EPSG:4326",
    resampling=Resampling.nearest,
):
    """
    Reproject a single-band raster at `path` onto the target grid.

    Parameters
    ----------
    path : str
        Path to source raster.
    dst_transform, dst_width, dst_height : affine.Affine, int, int
        Target grid (e.g. from `build_reference_grid`).
    dst_crs : str
    resampling : rasterio.enums.Resampling

    Returns
    -------
    np.ndarray (float32) with NaN for nodata, shape (dst_height, dst_width).
    """
    with rasterio.open(path) as src:
        src_arr = src.read(1, masked=True).filled(np.nan).astype(np.float32)

        dst_arr = np.full((dst_height, dst_width), np.nan, dtype=np.float32)
        reproject(
            source=src_arr,
            destination=dst_arr,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            src_nodata=np.nan,
            dst_nodata=np.nan,
            resampling=resampling,
        )
    return dst_arr


def mask_valid_pixels(*arrays):
    """
    Given N 2D arrays of the same shape, return the flat valid values for
    each along with the 2D boolean mask of valid pixels.

    Valid = finite (non-NaN, non-inf) across ALL input arrays.

    Returns
    -------
    valid_values : tuple of np.ndarray
        One 1D array per input, containing only the valid pixels.
    mask_2d : np.ndarray (bool)
        Boolean mask with the same shape as the inputs; True where all
        inputs are finite.
    """
    if len(arrays) == 0:
        raise ValueError("mask_valid_pixels requires at least one array")

    shape = arrays[0].shape
    mask_2d = np.ones(shape, dtype=bool)
    for a in arrays:
        if a.shape != shape:
            raise ValueError(f"shape mismatch: {a.shape} vs {shape}")
        mask_2d &= np.isfinite(a)

    valid_values = tuple(a[mask_2d] for a in arrays)
    return valid_values, mask_2d


def bivariate_classify(x_valid, y_valid, n_classes=3, method="quantile"):
    """
    Classify two 1D arrays into an n x n grid of bivariate classes.

    Class code = y_class * n_classes + x_class, so codes run 0..n_classes**2 - 1.
    For n_classes=3, this produces 9 codes with x (cs) on columns and
    y (temp) on rows.

    Parameters
    ----------
    x_valid, y_valid : 1D np.ndarray
        Flat arrays of valid pixel values (same length).
    n_classes : int
        Number of bins per axis (3 -> terciles, 4 -> quartiles, etc.).
    method : {"quantile", "equal_interval"}
        How to pick breaks.

    Returns
    -------
    x_breaks : np.ndarray, length n_classes - 1
    y_breaks : np.ndarray, length n_classes - 1
    class_codes : 1D np.ndarray of ints
    """
    if method == "quantile":
        qs = np.linspace(0, 1, n_classes + 1)[1:-1]
        x_breaks = np.quantile(x_valid, qs)
        y_breaks = np.quantile(y_valid, qs)
    elif method == "equal_interval":
        x_breaks = np.linspace(x_valid.min(), x_valid.max(), n_classes + 1)[1:-1]
        y_breaks = np.linspace(y_valid.min(), y_valid.max(), n_classes + 1)[1:-1]
    else:
        raise ValueError(f"unknown method: {method}")

    x_class = np.digitize(x_valid, x_breaks)
    y_class = np.digitize(y_valid, y_breaks)
    class_codes = y_class * n_classes + x_class
    return x_breaks, y_breaks, class_codes


def unflatten_to_raster(values, mask_2d, fill=-1, dtype=int):
    """
    Inverse of mask_valid_pixels for a single variable: place `values` back
    into a 2D raster at the True positions of `mask_2d`, filling the rest
    with `fill`.

    Parameters
    ----------
    values : 1D np.ndarray
        Values for each True pixel in mask_2d (same length as mask_2d.sum()).
    mask_2d : 2D np.ndarray (bool)
        Boolean mask from `mask_valid_pixels`.
    fill : scalar
        Value for invalid/masked pixels.
    dtype : numpy dtype

    Returns
    -------
    np.ndarray with shape == mask_2d.shape
    """
    out = np.full(mask_2d.shape, fill, dtype=dtype)
    out[mask_2d] = values
    return out


def upsample_raster_to_climate_grid(
    path_raster: str | Path,
    path_climate_ref: str | Path,
    out_path: str | Path,
    dst_crs: str = "EPSG:4326",
) -> Path:
    """
    Reproject the fine-resolution conservation raster onto the coarser
    climate grid and save as a GeoTIFF.  Run once; all subsequent analyses
    can read the saved file instead of reprojecting every time.

    Parameters
    ----------
    path_raster : path to the high-resolution raster to be upsampled.
    path_climate_ref : path to any climate raster whose resolution defines
        the target grid.
    out_path : where to write the upsampled raster GeoTIFF.
    dst_crs : CRS for the output grid.

    Returns
    -------
    Path to the saved raster.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Build the target grid from the *climate* raster (coarser)
    transform, width, height = build_reference_grid(str(path_climate_ref), dst_crs=dst_crs)

    # Reproject raster onto that grid (nearest preserves categorical scores)
    cs_aligned = reproject_to_grid(
        str(path_raster), transform, width, height,
        dst_crs=dst_crs, resampling=Resampling.nearest,
    )

    # Write out
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": width,
        "height": height,
        "count": 1,
        "crs": dst_crs,
        "transform": transform,
        "nodata": np.nan,
        "compress": "deflate",
    }
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(cs_aligned, 1)

    print(f"Saved upsampled raster ({height}x{width}) → {out_path}")
    return out_path


if __name__ == "__main__":
    path_cs = Path(
        "/Users/kylabazlen/Documents/Climate_Roadmap/Ecosystems/eco_data/"
        "COStatewideConservationSummaryV8/TIF_File/ConservationSummaryV8_NoTribalLands.tif"
    )
    path_climate_ref = Path(
        "/Users/kylabazlen/Documents/Climate_Roadmap/clim_data/Tx95/"
        "TX95p_GWL20C_minus_REF_absoule_change_v2.tif"
    )
    # Save in the same directory as the CS raster
    out_path = path_cs.parent / "ConservationSummaryV8_climate_grid.tif"

    upsample_raster_to_climate_grid(path_cs, path_climate_ref, out_path)

