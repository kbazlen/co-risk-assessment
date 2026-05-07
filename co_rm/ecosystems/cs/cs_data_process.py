
from pathlib import Path
import glob
import json
import numpy as np
import rasterio
from rasterio.warp import reproject, calculate_default_transform
from rasterio.enums import Resampling
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

# ============================================================
# Grid / reprojection helpers
# ============================================================

def build_reference_grid(path, dst_crs="EPSG:3857", target_resolution=250):
    with rasterio.open(path) as ref:
        if target_resolution is None:
            transform, width, height = calculate_default_transform(
                ref.crs, dst_crs, ref.width, ref.height, *ref.bounds
            )
        else:
            transform, width, height = calculate_default_transform(
                ref.crs, dst_crs, ref.width, ref.height, *ref.bounds,
                resolution=target_resolution,
            )
    return transform, width, height


def reproject_to_grid(path, dst_transform, dst_width, dst_height,
                     dst_crs="EPSG:3857", resampling=Resampling.nearest):
    with rasterio.open(path) as src:
        src_arr = src.read(1).astype(np.float32)
        if src.nodata is not None:
            src_arr[src_arr == src.nodata] = np.nan
        dst_arr = np.full((dst_height, dst_width), np.nan, dtype=np.float32)
        reproject(
            source=src_arr, destination=dst_arr,
            src_transform=src.transform, src_crs=src.crs,
            dst_transform=dst_transform, dst_crs=dst_crs,
            src_nodata=np.nan, dst_nodata=np.nan,
            resampling=resampling,
        )
    return dst_arr


def grid_to_extent(transform, width, height):
    left   = transform.c
    top    = transform.f
    right  = left + transform.a * width
    bottom = top  + transform.e * height
    return (left, right, bottom, top)

# ============================================================
# Bivariate helpers
# ============================================================

def mask_valid_pixels(*arrays):
    if not arrays:
        raise ValueError("mask_valid_pixels requires at least one array")
    shape = arrays[0].shape
    mask_2d = np.ones(shape, dtype=bool)
    for a in arrays:
        if a.shape != shape:
            raise ValueError(f"shape mismatch: {a.shape} vs {shape}")
        mask_2d &= np.isfinite(a)
    return tuple(a[mask_2d] for a in arrays), mask_2d


def bivariate_classify(x_valid, y_valid, n_classes=3, method="quantile"):
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
    return x_breaks, y_breaks, y_class * n_classes + x_class

def unflatten_to_raster(values, mask_2d, fill=-1, dtype=int):
    out = np.full(mask_2d.shape, fill, dtype=dtype)
    out[mask_2d] = values
    return out
