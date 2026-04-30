"""Unified non-interactive execution entrypoint for ecosystem workflows."""

from __future__ import annotations

import argparse
import glob
import os
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
from rasterio.enums import Resampling

from co_rm.plotting_base import CUSTOM_OFFSETS, DEFAULT_PATHS, extract_gwl, make_basemap
import numpy as np
import rasterio

from co_rm.ns_ecosystems.data_process import (
    bivariate_classify,
    build_reference_grid,
    mask_valid_pixels,
    reproject_to_grid,
    unflatten_to_raster,
)
from co_rm.ns_ecosystems.execution_comap import run_comap_single_levels
from co_rm.ns_ecosystems.plotting import (
    add_bivariate_legend,
    compute_extent,
    layers,
    plot_bivariate_map,
    plot_elevation_scatter,
    plot_veg_composition,
)
from functions.plot_hillshade import plot_hillshade

# Force headless rendering for script/CLI runs.
matplotlib.use("Agg")

BIVAR_COLORS = {
    0: "#e8e8e8",  # low cs, low temp
    1: "#ace4e4",  # mid cs, low temp
    2: "#5ac8c8",  # high cs, low temp
    3: "#dfb0d6",  # low cs, mid temp
    4: "#a5add3",  # mid cs, mid temp
    5: "#5698b9",  # high cs, mid temp
    6: "#be64ac",  # low cs, high temp
    7: "#8c62aa",  # mid cs, high temp
    8: "#3b4994",  # high cs, high temp
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _render_cs_bivariate_map(
    path_cs: str | Path,
    path_temp: str | Path,
    out_file: str | Path,
    hazard_label: str,
    map_title: str,
    hillshade_shp: str | Path | None = None,
    hillshade_nc: str | Path | None = None,
    path_cs_upsampled: str | Path | None = None,
) -> Path:
    """Render a non-interactive CS x hazard bivariate PNG map."""
    root = _repo_root()
    path_cs = Path(path_cs)
    path_temp = Path(path_temp)
    out_file = Path(out_file)

    if hillshade_shp is None:
        hillshade_shp = root / "functions/supporting_data_for_hillshade/cities_of_interest.shp"
    if hillshade_nc is None:
        hillshade_nc = root / "functions/supporting_data_for_hillshade/COtopography.nc"

    hillshade_shp = Path(hillshade_shp)
    hillshade_nc = Path(hillshade_nc)

    out_file.parent.mkdir(parents=True, exist_ok=True)

    dst_crs = "EPSG:4326"

    if path_cs_upsampled is not None:
        # Use the pre-upsampled CS raster (already at climate grid resolution).
        # Skip expensive reprojection of the fine-resolution CS raster.
        with rasterio.open(str(path_cs_upsampled)) as src:
            cs_aligned = src.read(1, masked=True).filled(np.nan).astype(np.float32)
            transform = src.transform
            width = src.width
            height = src.height
    else:
        transform, width, height = build_reference_grid(str(path_cs), dst_crs=dst_crs)
        cs_aligned = reproject_to_grid(
            str(path_cs),
            transform,
            width,
            height,
            dst_crs=dst_crs,
            resampling=Resampling.nearest,
        )

    temp_aligned = reproject_to_grid(
        str(path_temp),
        transform,
        width,
        height,
        dst_crs=dst_crs,
        resampling=Resampling.bilinear,
    )

    extent = compute_extent(transform, width, height)
    (cs_valid, temp_valid), mask = mask_valid_pixels(cs_aligned, temp_aligned)
    _, _, bivar_codes = bivariate_classify(cs_valid, temp_valid)
    bivar_map = unflatten_to_raster(bivar_codes, mask)

    fig, ax = plot_hillshade(
        shp_path=str(hillshade_shp),
        nc_path=str(hillshade_nc),
        method="hillshade",
        zfactor=10,
        azimuth=320.0,
        altitude=25.0,
        topo_alpha=1,
        city_size=10,
        city_color="black",
        label_fontsize=10,
    )
    plot_bivariate_map(bivar_map, extent, BIVAR_COLORS, ax)

    fig, ax = make_basemap(
        county_boundaries=DEFAULT_PATHS["county_boundaries"],
        custom_offsets=CUSTOM_OFFSETS,
        ax=ax,
    )

    # Keep basemap labels and lines above the raster overlay.
    for line in ax.lines:
        line.set_zorder(5)
    for text in ax.texts:
        text.set_zorder(6)
    for patch in ax.patches:
        patch.set_zorder(5)

    add_bivariate_legend(fig, BIVAR_COLORS, "Conservation ->", f"{hazard_label} ->")
    ax.set_title(map_title, fontsize=14, fontweight="bold")

    fig.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_file}")

    return out_file


def _render_elevation_scatter(
    path_cs: str | Path,
    path_temp: str | Path,
    elev_nc: str | Path,
    out_file: str | Path,
    hazard_label: str,
    path_cs_upsampled: str | Path | None = None,
) -> Path:
    """Render a non-interactive elevation vs CS×hazard scatter PNG."""
    import xarray as xr
    from rasterio.transform import from_bounds
    from rasterio.warp import reproject as rio_reproject

    out_file = Path(out_file)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    dst_crs = "EPSG:4326"

    # Get CS aligned grid
    if path_cs_upsampled is not None:
        with rasterio.open(str(path_cs_upsampled)) as src:
            cs_aligned = src.read(1, masked=True).filled(np.nan).astype(np.float32)
            transform = src.transform
            width = src.width
            height = src.height
    else:
        transform, width, height = build_reference_grid(str(path_cs), dst_crs=dst_crs)
        cs_aligned = reproject_to_grid(
            str(path_cs), transform, width, height,
            dst_crs=dst_crs, resampling=Resampling.nearest,
        )

    # Align hazard
    temp_aligned = reproject_to_grid(
        str(path_temp), transform, width, height,
        dst_crs=dst_crs, resampling=Resampling.bilinear,
    )

    # Load and align elevation
    ds = xr.open_dataset(str(elev_nc))
    elev_da = ds["HGT"]
    elev_vals = elev_da.values.astype(np.float32)
    lats = elev_da["latitude"].values
    lons = elev_da["longitude"].values
    if lats[0] < lats[-1]:
        elev_vals = elev_vals[::-1, :]

    elev_aligned = np.full((height, width), np.nan, dtype=np.float32)
    rio_reproject(
        source=elev_vals,
        destination=elev_aligned,
        src_transform=from_bounds(
            lons.min(), lats.min(), lons.max(), lats.max(),
            elev_vals.shape[1], elev_vals.shape[0],
        ),
        src_crs="EPSG:4326",
        dst_transform=transform,
        dst_crs=dst_crs,
        resampling=Resampling.bilinear,
    )
    ds.close()

    # Plot
    fig, _ = plot_elevation_scatter(
        cs_aligned, temp_aligned, elev_aligned,
        BIVAR_COLORS, hazard_label=hazard_label,
    )
    fig.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_file}")

    return out_file


def run_cs_bivariate_all_layers(
    path_cs: str | Path,
    cs_out_dir: str | Path,
    hillshade_shp: str | Path | None = None,
    hillshade_nc: str | Path | None = None,
    layer_key: str | None = None,
    path_cs_upsampled: str | Path | None = None,
) -> int:
    """Generate CS x hazard bivariate maps for all configured ecosystem layers."""
    cs_out_dir = Path(cs_out_dir)
    cs_out_dir.mkdir(parents=True, exist_ok=True)

    selected_layers = layers.items()
    if layer_key is not None:
        if layer_key not in layers:
            raise ValueError(f"Unknown layer key: {layer_key}")
        selected_layers = [(layer_key, layers[layer_key])]

    saved_count = 0

    for key, layer_info in selected_layers:
        path_pattern = layer_info["path"]
        if "*" in path_pattern:
            matching_files = sorted(glob.glob(path_pattern))
        else:
            matching_files = [path_pattern] if os.path.exists(path_pattern) else []

        if not matching_files:
            print(f"No files match {path_pattern}")
            continue

        layer_label = layer_info.get("label", key)

        for hazard_path in matching_files:
            stem = Path(hazard_path).stem
            gwl = extract_gwl(stem)
            if gwl:
                map_title = f"Bivariate: Conservation x {layer_label} at {gwl}"
            else:
                map_title = f"Bivariate: Conservation x {layer_label}"

            # Match COMaP naming style by keying output names off the source tif name.
            # If a duplicate stem appears, append layer key to keep filenames unique.
            out_file = cs_out_dir / f"{stem}.png"
            if out_file.exists():
                safe_key = key.replace(" ", "_")
                out_file = cs_out_dir / f"{stem}_{safe_key}.png"

            _render_cs_bivariate_map(
                path_cs=path_cs,
                path_temp=hazard_path,
                out_file=out_file,
                hazard_label=layer_label,
                map_title=map_title,
                hillshade_shp=hillshade_shp,
                hillshade_nc=hillshade_nc,
                path_cs_upsampled=path_cs_upsampled,
            )
            saved_count += 1

    return saved_count


def run_cs_elevation_all_layers(
    path_cs: str | Path,
    elev_out_dir: str | Path,
    elev_nc: str | Path,
    layer_key: str | None = None,
    path_cs_upsampled: str | Path | None = None,
) -> int:
    """Generate elevation scatter plots for all configured ecosystem layers."""
    elev_out_dir = Path(elev_out_dir)
    elev_out_dir.mkdir(parents=True, exist_ok=True)

    selected_layers = layers.items()
    if layer_key is not None:
        if layer_key not in layers:
            raise ValueError(f"Unknown layer key: {layer_key}")
        selected_layers = [(layer_key, layers[layer_key])]

    saved_count = 0

    for key, layer_info in selected_layers:
        path_pattern = layer_info["path"]
        if "*" in path_pattern:
            matching_files = sorted(glob.glob(path_pattern))
        else:
            matching_files = [path_pattern] if os.path.exists(path_pattern) else []

        if not matching_files:
            print(f"No files match {path_pattern}")
            continue

        layer_label = layer_info.get("label", key)

        for hazard_path in matching_files:
            stem = Path(hazard_path).stem
            out_file = elev_out_dir / f"{stem}_elevation.png"
            if out_file.exists():
                safe_key = key.replace(" ", "_")
                out_file = elev_out_dir / f"{stem}_{safe_key}_elevation.png"

            _render_elevation_scatter(
                path_cs=path_cs,
                path_temp=hazard_path,
                elev_nc=elev_nc,
                out_file=out_file,
                hazard_label=layer_label,
                path_cs_upsampled=path_cs_upsampled,
            )
            saved_count += 1

    return saved_count


# Default vegetation raster path
_DEFAULT_VEG_PATH = (
    "/Users/kylabazlen/Documents/Climate_Roadmap/Forest/Data/"
    "Vegetation_COWRA22/Vegetation_COWRA22.tif"
)


def _render_veg_composition(
    path_cs: str | Path,
    path_temp: str | Path,
    path_veg: str | Path,
    out_file: str | Path,
    hazard_label: str,
    path_cs_upsampled: str | Path | None = None,
) -> Path:
    """Render a non-interactive vegetation composition stacked-bar PNG."""
    from rasterio.warp import reproject as rio_reproject

    out_file = Path(out_file)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    dst_crs = "EPSG:4326"

    # Get CS aligned grid
    if path_cs_upsampled is not None:
        with rasterio.open(str(path_cs_upsampled)) as src:
            cs_aligned = src.read(1, masked=True).filled(np.nan).astype(np.float32)
            transform = src.transform
            width = src.width
            height = src.height
    else:
        transform, width, height = build_reference_grid(str(path_cs), dst_crs=dst_crs)
        cs_aligned = reproject_to_grid(
            str(path_cs), transform, width, height,
            dst_crs=dst_crs, resampling=Resampling.nearest,
        )

    # Align hazard
    temp_aligned = reproject_to_grid(
        str(path_temp), transform, width, height,
        dst_crs=dst_crs, resampling=Resampling.bilinear,
    )

    # Compute bivariate classification
    (cs_valid, temp_valid), mask = mask_valid_pixels(cs_aligned, temp_aligned)
    _, _, bivar_codes = bivariate_classify(cs_valid, temp_valid)
    bivar_map = unflatten_to_raster(bivar_codes, mask)

    # Load and reproject vegetation
    with rasterio.open(str(path_veg)) as src:
        veg_filled = src.read(1, masked=True).astype(np.float32).filled(np.nan)
        veg_src_transform = src.transform
        veg_src_crs = src.crs

    veg_aligned = np.full((height, width), np.nan, dtype=np.float32)
    rio_reproject(
        source=veg_filled,
        destination=veg_aligned,
        src_transform=veg_src_transform,
        src_crs=veg_src_crs,
        dst_transform=transform,
        dst_crs=dst_crs,
        src_nodata=np.nan,
        dst_nodata=np.nan,
        resampling=Resampling.nearest,
    )

    # Plot
    fig, _ = plot_veg_composition(
        bivar_map, veg_aligned, BIVAR_COLORS, hazard_label=hazard_label,
    )
    fig.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_file}")

    return out_file


def run_cs_vegetation_all_layers(
    path_cs: str | Path,
    veg_out_dir: str | Path,
    path_veg: str | Path | None = None,
    layer_key: str | None = None,
    path_cs_upsampled: str | Path | None = None,
) -> int:
    """Generate vegetation composition stacked bars for all configured layers."""
    veg_out_dir = Path(veg_out_dir)
    veg_out_dir.mkdir(parents=True, exist_ok=True)

    if path_veg is None:
        path_veg = _DEFAULT_VEG_PATH

    selected_layers = layers.items()
    if layer_key is not None:
        if layer_key not in layers:
            raise ValueError(f"Unknown layer key: {layer_key}")
        selected_layers = [(layer_key, layers[layer_key])]

    saved_count = 0

    for key, layer_info in selected_layers:
        path_pattern = layer_info["path"]
        if "*" in path_pattern:
            matching_files = sorted(glob.glob(path_pattern))
        else:
            matching_files = [path_pattern] if os.path.exists(path_pattern) else []

        if not matching_files:
            print(f"No files match {path_pattern}")
            continue

        layer_label = layer_info.get("label", key)

        for hazard_path in matching_files:
            stem = Path(hazard_path).stem
            out_file = veg_out_dir / f"{stem}_vegetation.png"
            if out_file.exists():
                safe_key = key.replace(" ", "_")
                out_file = veg_out_dir / f"{stem}_{safe_key}_vegetation.png"

            _render_veg_composition(
                path_cs=path_cs,
                path_temp=hazard_path,
                path_veg=path_veg,
                out_file=out_file,
                hazard_label=layer_label,
                path_cs_upsampled=path_cs_upsampled,
            )
            saved_count += 1

    return saved_count


def parse_args() -> argparse.Namespace:
    root = _repo_root()

    parser = argparse.ArgumentParser(description="Run non-interactive ecosystem workflows.")
    parser.add_argument(
        "--workflow",
        choices=["comap", "cs-bivariate", "cs-elevation", "cs-vegetation"],
        required=True,
        help="Which workflow to run.",
    )

    parser.add_argument(
        "--hillshade-shp",
        default=str(root / "functions/supporting_data_for_hillshade/cities_of_interest.shp"),
        help="Path to hillshade cities shapefile.",
    )
    parser.add_argument(
        "--hillshade-nc",
        default=str(root / "functions/supporting_data_for_hillshade/COtopography.nc"),
        help="Path to hillshade topography netcdf.",
    )

    parser.add_argument(
        "--out-dir",
        default=str(root / "../maps/ecosystems/COMap/comap_single_levels_1"),
        help="Output directory for COMaP PNG files.",
    )
    parser.add_argument(
        "--lpkx-path",
        default=str(root / "../Ecosystems/eco_data/COMaP_ConservationStatus_DraftV5.lpkx"),
        help="Path to COMaP .lpkx archive.",
    )
    parser.add_argument(
        "--colorbar-json",
        default=str(root / "co_rm/co_clim_data_colorbars.json"),
        help="Path to colorbar JSON metadata file.",
    )
    parser.add_argument(
        "--extract-dir",
        default="/tmp/lpkx_extracted",
        help="Directory for temporary lpkx extraction.",
    )

    parser.add_argument(
        "--path-cs",
        default=str(
            root
            / "../Ecosystems/eco_data/COStatewideConservationSummaryV8/TIF_File/ConservationSummaryV8_NoTribalLands.tif"
        ),
        help="Path to conservation status raster for CS bivariate workflow.",
    )
    parser.add_argument(
        "--layer-key",
        default=None,
        help="For cs-bivariate workflow, run only one specific layer key from plotting.layers.",
    )
    parser.add_argument(
        "--cs-out-dir",
        default=str(root / "../maps/ecosystems/CS/bivariate_layers"),
        help="Output directory for cs-bivariate all-layers mode.",
    )
    parser.add_argument(
        "--path-cs-upsampled",
        default=None,
        help="Path to pre-upsampled CS raster (at climate grid resolution). "
        "Skips expensive reprojection of the full-resolution CS raster.",
    )
    parser.add_argument(
        "--elev-nc",
        default=str(root / "functions/supporting_data_for_hillshade/COtopography.nc"),
        help="Path to elevation netCDF (COtopography.nc) for cs-elevation workflow.",
    )
    parser.add_argument(
        "--elev-out-dir",
        default=str(root / "../maps/ecosystems/CS/elevation_scatter"),
        help="Output directory for cs-elevation scatter PNGs.",
    )
    parser.add_argument(
        "--path-veg",
        default=_DEFAULT_VEG_PATH,
        help="Path to Vegetation_COWRA22.tif raster for cs-vegetation workflow.",
    )
    parser.add_argument(
        "--veg-out-dir",
        default=str(root / "../maps/ecosystems/CS/vegetation_composition"),
        help="Output directory for cs-vegetation stacked bar PNGs.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.workflow == "comap":
        saved = run_comap_single_levels(
            out_dir=args.out_dir,
            lpkx_path=args.lpkx_path,
            colorbar_json=args.colorbar_json,
            extract_dir=args.extract_dir,
            hillshade_shp=args.hillshade_shp,
            hillshade_nc=args.hillshade_nc,
        )
        print(f"Finished COMaP workflow. Wrote {saved} image(s).")
        return

    if args.workflow == "cs-bivariate":
        saved = run_cs_bivariate_all_layers(
            path_cs=args.path_cs,
            cs_out_dir=args.cs_out_dir,
            hillshade_shp=args.hillshade_shp,
            hillshade_nc=args.hillshade_nc,
            layer_key=args.layer_key,
            path_cs_upsampled=args.path_cs_upsampled,
        )
        print(f"Finished CS bivariate workflow. Wrote {saved} image(s).")
        return

    if args.workflow == "cs-elevation":
        saved = run_cs_elevation_all_layers(
            path_cs=args.path_cs,
            elev_out_dir=args.elev_out_dir,
            elev_nc=args.elev_nc,
            layer_key=args.layer_key,
            path_cs_upsampled=args.path_cs_upsampled,
        )
        print(f"Finished CS elevation workflow. Wrote {saved} image(s).")
        return

    if args.workflow == "cs-vegetation":
        saved = run_cs_vegetation_all_layers(
            path_cs=args.path_cs,
            veg_out_dir=args.veg_out_dir,
            path_veg=args.path_veg,
            layer_key=args.layer_key,
            path_cs_upsampled=args.path_cs_upsampled,
        )
        print(f"Finished CS vegetation workflow. Wrote {saved} image(s).")
        return

    raise ValueError(f"Unsupported workflow: {args.workflow}")


if __name__ == "__main__":
    main()
