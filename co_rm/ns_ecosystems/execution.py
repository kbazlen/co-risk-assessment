"""Batch execution helpers for ecosystem map generation."""

from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path

import geopandas as gpd
import matplotlib
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import py7zr

from co_rm.plotting_base import CUSTOM_OFFSETS, DEFAULT_PATHS, extract_gwl, make_basemap, plot_raster
from co_rm.ns_ecosystems.plotting import layers
from functions.plot_hillshade import plot_hillshade

# Force headless rendering for script/CLI runs.
matplotlib.use("Agg")

ORDER = ["V", "G", "F", "P", "U"]
LABELS = {
    "V": "Very Good",
    "G": "Good",
    "F": "Fair",
    "P": "Poor",
    "U": "Unknown",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_colorbar_metadata(colorbar_json: Path) -> dict:
    with colorbar_json.open("r", encoding="utf-8") as f:
        return json.load(f)


def _apply_layer_styling(cvariables: dict) -> None:
    for key, layer_info in layers.items():
        layer_info["vmin"] = None
        layer_info["vmax"] = None

        try:
            json_key = key.split("__")[0]
            subtype = layer_info.get("subtype", "standard")
            var_data = cvariables["variables"][json_key]["subtypes"][subtype]

            numeric_values = []
            for value in var_data["values"]:
                try:
                    numeric_values.append(float(value))
                except (TypeError, ValueError):
                    continue

            if numeric_values:
                layer_info["vmin"] = min(numeric_values)
                layer_info["vmax"] = max(numeric_values)

            if "cmap" not in layer_info:
                layer_info["cmap"] = mcolors.ListedColormap(var_data["colors"])
        except KeyError:
            if "cmap" not in layer_info:
                layer_info["cmap"] = "viridis"

    for layer_info in layers.values():
        if isinstance(layer_info.get("cmap"), list):
            layer_info["cmap"] = mcolors.ListedColormap(layer_info["cmap"])
        if isinstance(layer_info.get("vmin"), str):
            layer_info["vmin"] = None
        if isinstance(layer_info.get("vmax"), str):
            layer_info["vmax"] = None


def _extract_comap_shapefile(lpkx_path: Path, extract_dir: Path) -> Path:
    extract_dir.mkdir(parents=True, exist_ok=True)
    with py7zr.SevenZipFile(str(lpkx_path), mode="r") as archive:
        archive.extractall(path=str(extract_dir))

    shp_path = extract_dir / "commondata/comap_conservation_status_draftv5/COMaP_Conservation_Status_DraftV5.shp"
    if not shp_path.exists():
        raise FileNotFoundError(f"Could not find extracted shapefile at {shp_path}")
    return shp_path


def run_comap_single_levels(
    out_dir: str | Path,
    lpkx_path: str | Path,
    colorbar_json: str | Path,
    extract_dir: str | Path = "/tmp/lpkx_extracted",
    hillshade_shp: str | Path | None = None,
    hillshade_nc: str | Path | None = None,
) -> int:
    """Generate non-interactive map PNGs for each layer and COMaP status.

    Returns
    -------
    int
        Count of output images written.
    """
    out_dir = Path(out_dir)
    lpkx_path = Path(lpkx_path)
    colorbar_json = Path(colorbar_json)
    extract_dir = Path(extract_dir)

    if hillshade_shp is None:
        hillshade_shp = _repo_root() / "functions/supporting_data_for_hillshade/cities_of_interest.shp"
    if hillshade_nc is None:
        hillshade_nc = _repo_root() / "functions/supporting_data_for_hillshade/COtopography.nc"

    hillshade_shp = Path(hillshade_shp)
    hillshade_nc = Path(hillshade_nc)

    out_dir.mkdir(parents=True, exist_ok=True)

    cvariables = _load_colorbar_metadata(colorbar_json)
    _apply_layer_styling(cvariables)

    comap_shp = _extract_comap_shapefile(lpkx_path, extract_dir)
    gdf = gpd.read_file(str(comap_shp)).to_crs(epsg=4326)
    gdf["geometry"] = gdf.simplify(0.001)

    saved_count = 0

    for key, layer_info in layers.items():
        path_pattern = layer_info["path"]

        if "*" in path_pattern:
            matching_files = sorted(glob.glob(path_pattern))
            if not matching_files:
                print(f"No files match {path_pattern}")
                continue
        else:
            if not os.path.exists(path_pattern):
                print(f"File not found: {path_pattern}")
                continue
            matching_files = [path_pattern]

        for path in matching_files:
            tif_name = Path(path).stem
            gwl = extract_gwl(tif_name)

            for status in ORDER:
                try:
                    fig, ax = plot_hillshade(
                        shp_path=str(hillshade_shp),
                        nc_path=str(hillshade_nc),
                        method="hillshade",
                        zfactor=10,
                        azimuth=320.0,
                        altitude=25.0,
                        topo_alpha=1,
                    )

                    fig, ax, _ = plot_raster(
                        path=path,
                        alpha=0.8,
                        cmap=layer_info["cmap"],
                        vmin=layer_info["vmin"],
                        vmax=layer_info["vmax"],
                        cbar_label=layer_info.get("cbar_label", ""),
                        ax=ax,
                    )

                    fig, ax = make_basemap(
                        county_boundaries=DEFAULT_PATHS["county_boundaries"],
                        custom_offsets=CUSTOM_OFFSETS,
                        ax=ax,
                    )

                    gdf_status = gdf[gdf["Overall"] == status]
                    gdf_status.plot(
                        ax=ax,
                        facecolor="none",
                        edgecolor="red",
                        linewidth=0.65,
                        zorder=5,
                    )

                    base_label = layer_info.get("label", key)
                    if gwl:
                        title = f"{base_label} at {gwl} - {LABELS[status]}"
                    else:
                        title = f"{base_label} - {LABELS[status]}"
                    ax.set_title(title, fontsize=14, fontweight="bold")

                    plt.tight_layout()

                    level_str = LABELS[status].replace(" ", "_")
                    out_path = out_dir / f"{tif_name}_{level_str}.png"
                    fig.savefig(out_path, dpi=300, bbox_inches="tight")
                    plt.close(fig)
                    saved_count += 1
                    print(f"Saved: {out_path}")
                except Exception as exc:
                    print(f"ERROR on {key} - {tif_name} - {status}: {exc}")
                    plt.close("all")

    return saved_count


def parse_args() -> argparse.Namespace:
    root = _repo_root()
    parser = argparse.ArgumentParser(description="Generate non-interactive COMaP ecosystem map images.")
    parser.add_argument(
        "--out-dir",
        default=str(root / "../maps/ecosystems/COMap/comap_single_levels_1"),
        help="Output directory for PNG files.",
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    saved = run_comap_single_levels(
        out_dir=args.out_dir,
        lpkx_path=args.lpkx_path,
        colorbar_json=args.colorbar_json,
        extract_dir=args.extract_dir,
    )
    print(f"Finished. Wrote {saved} image(s).")


if __name__ == "__main__":
    main()
