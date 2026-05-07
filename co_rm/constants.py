from pathlib import Path

BASE_DIR = Path("/Users/kylabazlen/Documents/Climate_Roadmap/clim_data")


STEVENS_BLUERED = { #95th temp
    0: "#e8e8e8", 1: "#b0d5df", 2: "#64acbe",
    3: "#e4acac", 4: "#ad9ea5", 5: "#627f8c",
    6: "#c85a5a", 7: "#985356", 8: "#574249",
}

STEVENS_PINKBLUE = { #5day precip
    0: "#e8e8e8", 1: "#ace4e4", 2: "#5ac8c8",
    3: "#dfb0d6", 4: "#a5add3", 5: "#5698b9",
    6: "#be64ac", 7: "#8c62aa", 8: "#3b4994",
}

STEVENS_GREENBLUE = { 
    0: "#e8e8e8", 1: "#b5c0da", 2: "#6c83b5",
    3: "#b8d6be", 4: "#90b2b3", 5: "#567994",
    6: "#73ae80", 7: "#5a9178", 8: "#2a5a5b",
}

STEVENS_PINKGREEN = {
    0: "#f3f3f3", 1: "#c2f1ce", 2: "#8be2af",
    3: "#eac5dd", 4: "#9ec6d3", 5: "#7fc6b1",
    6: "#e6a3d0", 7: "#bc9fce", 8: "#7b8eaf",
}

STEVENS_PURPLEGOLD = { #d3
    0: "#e8e8e8", 1: "#e4d9ac", 2: "#c8b35a",
    3: "#cbb8d7", 4: "#c8ada0", 5: "#af8e53",
    6: "#9972af", 7: "#976b82", 8: "#804d36",
}


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
        "bivar": None,
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
        "bivar": None,
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
        "bivar": STEVENS_PURPLEGOLD,
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
        "bivar": None,
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
        "bivar": None,
    },
    "Days Exceeding 95th Percentile Maximum Temperature": {
        "path": str(BASE_DIR / "Tx95/TX95p_GWL*C_minus_REF_absoule_change_v2.tif"),
        "subtype": "standard",
        "cmap": "Reds",
        "vmin": None,
        "vmax": None,
        "variable": "heat-stress",
        "center": 0,
        "label": "Days Exceeding 95th Percentile Maximum Temperature",
        "cbar_label": "Days",
        "bivar": STEVENS_BLUERED,
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
        "bivar": None,
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
        "bivar": None,
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
        "bivar": STEVENS_PINKBLUE,
    },
}