from pathlib import Path

FINALMODST_COLORS = {
    "V":   "#5c8944",
    "G":   "#98bd00",
    "F":   "#b2b2b2",
    "P":   "#d7d79e",
    "U":   "#d7c29e",
    "NKP": "#f0f0f0",
}

FINALMODST_LABELS = {
    "V":   "Very Good",
    "G":   "Good",
    "F":   "Fair",
    "P":   "Poor",
    "U":   "Unknown",
    "NKP": "Private & Unmapped Lands",
}

FINALMODST_ORDER        = ["V", "G", "F", "P", "U", "NKP"]
FINALMODST_LEGEND_TITLE = "Conservation Protection Status"

BASE_DIR = Path("/Users/kylabazlen/Documents/Climate_Roadmap/clim_data")
COMPAP_PATH = Path("/Users/kylabazlen/Documents/Climate_Roadmap/Ecosystems/eco_data/COMaP_ConservationStatus_DraftV5.lpkx")

from pathlib import Path

layers = {
    "drought__D1": {
        "path": str(BASE_DIR / "pct_change_Aridity/pct_change_Aridity_*_D1_timescale_12months.tif"),
        "subtype": "rel-change",
        "vmin": None,
        "vmax": None,
        "variable": "drought",
        "center": 0,
        "label": "Change in D1 Drought Exposure",
        "cbar_label": "Drought Exposure",
    },
    "drought__D2": {
        "path": str(BASE_DIR / "pct_change_Aridity/pct_change_Aridity_*_D2_timescale_12months.tif"),
        "subtype": "rel-change",
        "vmin": None,
        "vmax": None,
        "variable": "drought",
        "center": 0,
        "label": "Change in D2 Drought Exposure",
        "cbar_label": "Drought Exposure",
    },
    "drought__D3": {
        "path": str(BASE_DIR / "pct_change_Aridity/pct_change_Aridity_*_D3_timescale_12months.tif"),
        "subtype": "rel-change",
        "vmin": None,
        "vmax": None,
         "variable": "drought",
        "center": 0,
        "label": "Change in D3 Drought Exposure",
        "cbar_label": "Drought Exposure",
    },
    "drought__D4": {
        "path": str(BASE_DIR / "pct_change_Aridity/pct_change_Aridity_*_D4_timescale_12months.tif"),
        "subtype": "rel-change",
        "vmin": None,
        "vmax": None,
        "variable": "drought",
        "center": 0,
        "label": "Change in D4 Drought Exposure",
        "cbar_label": "Drought Exposure",
    },
    "snowfall": {
        "path": str(BASE_DIR / "snow_fraction/snow_fraction_relative_apr.tif"),
        "subtype": "rel-change",
        "vmin": None,
        "vmax": None,
        "center": 0,
        "variable": "snowfall",
        "label": "Difference in Percent of Precipitation Received as Snow (April)",
        "cbar_label": "Snowfall",
    },
    "Days Exceeding 95th Percentile Maximum Temperature": {
        "path": str(BASE_DIR / "severe_heat/TX95p_GWL*C_minus_REF_absoule_change_v2.tif"),
        "subtype": "standard",
        "cmap": "Reds",
        "vmin": None,
        "vmax": None,
        "variable": "heat-stress",
        "center": 0,
        "label": "Days Exceeding 95th Percentile Maximum Temperature",
        "cbar_label": "Days",
    },
    "Change in Number of Frost Days": {
        "path": str(BASE_DIR / "FD/FD_GWL*C_minus_REF_absoule_change_v2.tif"),
        "subtype": "abs-change",
        "cmap": "PuBu_r",
        "vmin": None,
        "vmax": None,
        "variable": "snowfall",
        "center": 0,
        "label": "Change in Number of Frost Days",
        "cbar_label": "Days",
    },
    "Rx1day": {
        "path": str(BASE_DIR / "Rx1day/Rx1day_GWL*C_minus_REF_absoule_change_v2.tif"),
        "subtype": "abs-change",
        "vmin": None,
        "vmax": None,
        "center": 0,
        "label": "Change in Maximum 1-Day Precipitation",
        "cbar_label": "mm",
        "variable": "Rx1day",
    },
    "5 day max precip": {
        "path": str(BASE_DIR / "Rx5day/Rx5day_GWL*C_minus_REF_relative_change_v2.tif"),
        "subtype": "rel-change",
        "variable": "Rx5day",
        "vmin": None,
        "vmax": None,
        "center": 0,
        "label": "Change in Maximum 5-Day Precipitation",
        "cbar_label": "mm",
    },
}