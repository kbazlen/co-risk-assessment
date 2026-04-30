# Ecosystems Module

This folder contains ecosystem-specific plotting, processing, and batch execution logic.

## Files
- `plotting.py`: ecosystem plotting utilities and layer definitions.
- `data_process.py`: raster/grid processing helpers.
- `execution.py`: unified non-interactive runner for COMaP and CS-bivariate workflows.
- `execution_comap.py`: COMaP implementation used by the unified runner.

## Batch COMaP Map Generation
Run the non-interactive execution module from the `co-risk-assessment` repo root:

`python -m co_rm.ns_ecosystems.execution --workflow comap`

Run the CS x hazard bivariate workflow (always iterates all configured layers):

`python -m co_rm.ns_ecosystems.execution --workflow cs-bivariate`

### Optional Arguments
- `--workflow`: `comap`, `cs-bivariate`, `cs-elevation`, or `cs-vegetation`.
- `--hillshade-shp`: path to hillshade city points shapefile.
- `--hillshade-nc`: path to hillshade topography netcdf.
- `--out-dir`: COMaP output directory for PNG files.
- `--lpkx-path`: path to `COMaP_ConservationStatus_DraftV5.lpkx`.
- `--colorbar-json`: path to `co_clim_data_colorbars.json`.
- `--extract-dir`: temporary extraction directory for the `.lpkx` archive.
- `--path-cs`: CS raster path for bivariate workflow.
- `--path-cs-upsampled`: path to pre-upsampled CS raster (at climate grid resolution). Skips expensive reprojection of the full-resolution CS raster.
- `--layer-key`: run only one specific layer key from `plotting.layers` (omit to run all layers).
- `--cs-out-dir`: output directory for cs-bivariate PNG files.
- `--elev-nc`: path to elevation netCDF (`COtopography.nc`) for cs-elevation workflow.
- `--elev-out-dir`: output directory for cs-elevation scatter PNGs.
- `--path-veg`: path to `Vegetation_COWRA22.tif` for cs-vegetation workflow.
- `--veg-out-dir`: output directory for cs-vegetation stacked bar PNGs.

Example:

`python -m co_rm.ns_ecosystems.execution --workflow comap --out-dir /Users/kylabazlen/Documents/Climate_Roadmap/maps/ecosystems/COMap/comap_single_levels_2 --lpkx-path /Users/kylabazlen/Documents/Climate_Roadmap/Ecosystems/eco_data/COMaP_ConservationStatus_DraftV5.lpkx --colorbar-json /Users/kylabazlen/Documents/Climate_Roadmap/co-risk-assessment/co_rm/co_clim_data_colorbars.json --extract-dir /tmp/lpkx_extracted`


`python -m co_rm.ns_ecosystems.execution --workflow cs-bivariate --path-cs /Users/kylabazlen/Documents/Climate_Roadmap/Ecosystems/eco_data/COStatewideConservationSummaryV8/TIF_File/ConservationSummaryV8_NoTribalLands.tif --cs-out-dir /Users/kylabazlen/Documents/Climate_Roadmap/maps/ecosystems/CS/bivariate_layers`

Using the pre-upsampled CS raster (faster, skips reprojection):

`python -m co_rm.ns_ecosystems.execution --workflow cs-bivariate --path-cs /Users/kylabazlen/Documents/Climate_Roadmap/Ecosystems/eco_data/COStatewideConservationSummaryV8/TIF_File/ConservationSummaryV8_NoTribalLands.tif --path-cs-upsampled /Users/kylabazlen/Documents/Climate_Roadmap/Ecosystems/eco_data/COStatewideConservationSummaryV8/TIF_File/ConservationSummaryV8_climate_grid.tif --cs-out-dir /Users/kylabazlen/Documents/Climate_Roadmap/maps/ecosystems/CS/bivariate_layers_coarse`

Run elevation scatter plots for all layers (separate output folder):

`python -m co_rm.ns_ecosystems.execution --workflow cs-elevation --path-cs /Users/kylabazlen/Documents/Climate_Roadmap/Ecosystems/eco_data/COStatewideConservationSummaryV8/TIF_File/ConservationSummaryV8_NoTribalLands.tif --path-cs-upsampled /Users/kylabazlen/Documents/Climate_Roadmap/Ecosystems/eco_data/COStatewideConservationSummaryV8/TIF_File/ConservationSummaryV8_climate_grid.tif --elev-out-dir /Users/kylabazlen/Documents/Climate_Roadmap/maps/ecosystems/CS/elevation_scatter`

Run vegetation composition stacked bars for all layers:

`python -m co_rm.ns_ecosystems.execution --workflow cs-vegetation --path-cs /Users/kylabazlen/Documents/Climate_Roadmap/Ecosystems/eco_data/COStatewideConservationSummaryV8/TIF_File/ConservationSummaryV8_NoTribalLands.tif --path-cs-upsampled /Users/kylabazlen/Documents/Climate_Roadmap/Ecosystems/eco_data/COStatewideConservationSummaryV8/TIF_File/ConservationSummaryV8_climate_grid.tif --veg-out-dir /Users/kylabazlen/Documents/Climate_Roadmap/maps/ecosystems/CS/vegetation_composition`

## Design Notes
- Execution is headless (`matplotlib` uses `Agg`), so no interactive windows are opened.
- Reusable API is exposed as `run_comap_single_levels(...)`.
- The runner logs each output file path and prints a final image count.
- CS-bivariate always iterates all layers configured in `plotting.layers`; use `--layer-key` to run just one.
- CS-bivariate legend y-label and map title are automatically derived from each layer's label.
- CS-bivariate output filenames use each source raster tif basename (COMaP-style naming).
- CS-elevation is a separate workflow (`--workflow cs-elevation`) that outputs to `--elev-out-dir`.
- CS-vegetation is a separate workflow (`--workflow cs-vegetation`) that produces stacked bar charts showing how each vegetation class (from Vegetation_COWRA22 VAT) distributes across the 9 nonants. Outputs to `--veg-out-dir`.