# Ecosystems Module

This folder contains ecosystem-specific plotting, processing, and batch execution logic.

## Files
- `plotting.py`: ecosystem plotting utilities and layer definitions.
- `data_process.py`: raster/grid processing helpers.
- `execution.py`: non-interactive batch runner for COMaP map generation.

## Batch COMaP Map Generation
Run the non-interactive execution module from the `co-risk-assessment` repo root:

`python -m co_rm.ns_ecosystems.execution`

### Optional Arguments
- `--out-dir`: output directory for PNG files.
- `--lpkx-path`: path to `COMaP_ConservationStatus_DraftV5.lpkx`.
- `--colorbar-json`: path to `co_clim_data_colorbars.json`.
- `--extract-dir`: temporary extraction directory for the `.lpkx` archive.

Example:

`python -m co_rm.ns_ecosystems.execution --out-dir /Users/kylabazlen/Documents/Climate_Roadmap/maps/ecosystems/COMap/comap_single_levels_2 --lpkx-path /Users/kylabazlen/Documents/Climate_Roadmap/Ecosystems/eco_data/COMaP_ConservationStatus_DraftV5.lpkx --colorbar-json /Users/kylabazlen/Documents/Climate_Roadmap/co-risk-assessment/co_rm/co_clim_data_colorbars.json --extract-dir /tmp/lpkx_extracted`

## Design Notes
- Execution is headless (`matplotlib` uses `Agg`), so no interactive windows are opened.
- Reusable API is exposed as `run_comap_single_levels(...)`.
- The runner logs each output file path and prints a final image count.