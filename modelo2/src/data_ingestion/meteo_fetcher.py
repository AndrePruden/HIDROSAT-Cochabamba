"""
Mesoscale Hydro-Meteorological, Soil-Moisture, and River Discharge Ingestion Module.

Epistemological Consistency Note:
Satellite and reanalysis precipitation products (GPM IMERG at 0.1° ~11 km, ERA5-Land at 0.1° ~9 km)
cannot resolve individual 2–15 km² Tunari micro-watersheds independently. Therefore, this module
queries forcing at 6 physically distinct mesoscale grid sectors (~10 km spacing) representing
the true resolvable synoptic/orographic zones of the Cochabamba-Tunari system, plus GloFAS
macro-basin river discharge for the Río Rocha (10,386 km² UH7 basin).
"""
import json
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import requests

from src.config import DATA_PROCESSED, DATA_RAW

MESOSCALE_SECTORS = [
    {
        "sector_id": "TUNARI_WEST_HIGH",
        "name": "Cordillera del Tunari Occidental (Cabeceras K'hora, Taquiña, Pintumayu)",
        "lat": -17.27,
        "lon": -66.22,
        "elev_m": 4120,
        "domain": "upper_watershed_west",
        "effective_resolution_km": 10.0,
    },
    {
        "sector_id": "TUNARI_EAST_HIGH",
        "name": "Cordillera del Tunari Central-Oriental (Cabeceras Tirani, Chungara, Wara Wara, Chaquimayu)",
        "lat": -17.28,
        "lon": -66.12,
        "elev_m": 3960,
        "domain": "upper_watershed_east",
        "effective_resolution_km": 10.0,
    },
    {
        "sector_id": "PIEDEMONTE_COTA2750",
        "name": "Piedemonte y Ápices Aluviales (Transición Cota 2750)",
        "lat": -17.34,
        "lon": -66.16,
        "elev_m": 2810,
        "domain": "alluvial_fan_apex",
        "effective_resolution_km": 10.0,
    },
    {
        "sector_id": "VALLEY_ROCHA_CENTRAL",
        "name": "Valle Central Cercado y Corredor Medio Río Rocha",
        "lat": -17.39,
        "lon": -66.16,
        "elev_m": 2565,
        "domain": "urban_valley_floor",
        "effective_resolution_km": 10.0,
    },
    {
        "sector_id": "VALLEY_SOUTH_TAMBORADA",
        "name": "Planicie Sur (Tamborada, Alalay, La Maica, Albarrancho)",
        "lat": -17.44,
        "lon": -66.20,
        "elev_m": 2535,
        "domain": "southern_depression_outlet",
        "effective_resolution_km": 10.0,
    },
    {
        "sector_id": "UPPER_ROCHA_SACABA",
        "name": "Subcuenca Alta Río Rocha / Maylanco (Aporte Este UH8)",
        "lat": -17.40,
        "lon": -65.98,
        "elev_m": 2720,
        "domain": "eastern_macro_tributary",
        "effective_resolution_km": 10.0,
    },
]

HISTORICAL_EPOCHS = {
    "2018_taquina_disaster": {
        "title": "Aluvión / Mazamorra de Tiquipaya - Río Taquiña (6 Feb 2018)",
        "start_date": "2018-01-15",
        "end_date": "2018-02-15",
        "critical_event_date": "2018-02-06",
    },
    "2020_taquina_disaster": {
        "title": "Segundo Aluvión / Mazamorra de Tiquipaya - Río Taquiña (21 Feb 2020)",
        "start_date": "2020-01-25",
        "end_date": "2020-02-26",
        "critical_event_date": "2020-02-21",
    },
    "2026_wet_season_sar": {
        "title": "Época Húmeda 2026 (Coincidente con adquisición Sentinel-1 RTC 21-22 Feb 2026)",
        "start_date": "2026-01-25",
        "end_date": "2026-02-25",
        "critical_event_date": "2026-02-21",
    },
    "2026_dry_season_sar": {
        "title": "Estiaje Invernal 2026 (Coincidente con adquisición Sentinel-1 RTC 3-4 Ago 2026)",
        "start_date": "2026-07-10",
        "end_date": "2026-08-10",
        "critical_event_date": "2026-08-03",
    },
}


def compute_api_series(precip_daily: List[float], k_decay: float = 0.85) -> List[float]:
    """
    Compute Kohler & Linsley (1951) Antecedent Precipitation Index (API):
        API_t = k * API_{t-1} + P_{t-1}
    Note: Strictly uses PRIOR days' precipitation (up to t-1) to represent
    antecedent basin pre-conditioning before day t's storm.
    """
    api = []
    curr = 0.0
    for p in precip_daily:
        api.append(round(curr, 3))
        p_val = float(p) if p is not None and not np.isnan(p) else 0.0
        curr = k_decay * curr + p_val
    return api


def fetch_all_meteo_and_glofas() -> Dict:
    raw_dir = DATA_RAW / "meteo"
    proc_dir = DATA_PROCESSED / "antecedent_forecast"
    raw_dir.mkdir(parents=True, exist_ok=True)
    proc_dir.mkdir(parents=True, exist_ok=True)

    lats = ",".join(str(s["lat"]) for s in MESOSCALE_SECTORS)
    lons = ",".join(str(s["lon"]) for s in MESOSCALE_SECTORS)

    # 1. Operational Window: Past 21 days + 7 days forecast around Nov 15, 2026
    r_op = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lats,
            "longitude": lons,
            "daily": "precipitation_sum,rain_sum,precipitation_hours,et0_fao_evapotranspiration",
            "hourly": "precipitation,soil_moisture_0_to_1cm,soil_moisture_1_to_3cm,soil_moisture_3_to_9cm,soil_moisture_9_to_27cm",
            "past_days": 21,
            "forecast_days": 7,
            "timezone": "America/La_Paz",
        },
        timeout=30,
    )
    r_op.raise_for_status()
    op_data = r_op.json()

    operational_sectors = {}
    for s_meta, s_resp in zip(MESOSCALE_SECTORS, op_data):
        sid = s_meta["sector_id"]
        daily = s_resp["daily"]
        hourly = s_resp["hourly"]

        # Aggregate hourly soil moisture to daily mean
        hr_df = pd.DataFrame(hourly)
        hr_df["date"] = hr_df["time"].str.slice(0, 10)
        sm_daily = (
            hr_df.groupby("date")[
                [
                    "soil_moisture_0_to_1cm",
                    "soil_moisture_1_to_3cm",
                    "soil_moisture_3_to_9cm",
                    "soil_moisture_9_to_27cm",
                ]
            ]
            .mean()
            .reset_index()
        )
        sm_daily["root_zone_sm_m3m3"] = (
            0.15 * sm_daily["soil_moisture_0_to_1cm"]
            + 0.25 * sm_daily["soil_moisture_1_to_3cm"]
            + 0.30 * sm_daily["soil_moisture_3_to_9cm"]
            + 0.30 * sm_daily["soil_moisture_9_to_27cm"]
        ).round(4)

        p_list = [float(x or 0.0) for x in daily["precipitation_sum"]]
        api_85 = compute_api_series(p_list, k_decay=0.85)  # Shallow colluvial memory (~6d half-life)
        api_92 = compute_api_series(p_list, k_decay=0.92)  # Deep root-zone memory (~12d half-life)

        records = []
        for idx, dt in enumerate(daily["time"]):
            sm_row = sm_daily[sm_daily["date"] == dt]
            sm_root = float(sm_row["root_zone_sm_m3m3"].iloc[0]) if len(sm_row) else None
            sm_surf = float(sm_row["soil_moisture_0_to_1cm"].iloc[0]) if len(sm_row) else None
            records.append(
                {
                    "date": dt,
                    "precip_mm": round(p_list[idx], 2),
                    "precip_hours": float(daily["precipitation_hours"][idx] or 0.0),
                    "et0_mm": round(float(daily["et0_fao_evapotranspiration"][idx] or 0.0), 2),
                    "api_k85_mm": round(api_85[idx], 2),
                    "api_k92_mm": round(api_92[idx], 2),
                    "precip_prev_3d_mm": round(sum(p_list[max(0, idx - 3) : idx]), 2),
                    "precip_prev_7d_mm": round(sum(p_list[max(0, idx - 7) : idx]), 2),
                    "precip_prev_14d_mm": round(sum(p_list[max(0, idx - 14) : idx]), 2),
                    "surface_sm_m3m3": round(sm_surf, 4) if sm_surf is not None else None,
                    "root_zone_sm_m3m3": round(sm_root, 4) if sm_root is not None else None,
                }
            )
        operational_sectors[sid] = {
            "metadata": s_meta,
            "daily_series": records,
        }

    # 2. Historical Benchmark Epochs (2018, 2020, Feb 2026, Aug 2026)
    historical_results = {}
    for epoch_key, epoch_cfg in HISTORICAL_EPOCHS.items():
        r_hist = requests.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params={
                "latitude": lats,
                "longitude": lons,
                "start_date": epoch_cfg["start_date"],
                "end_date": epoch_cfg["end_date"],
                "daily": "precipitation_sum,et0_fao_evapotranspiration",
                "hourly": "precipitation,soil_moisture_0_to_7cm,soil_moisture_7_to_28cm",
                "timezone": "America/La_Paz",
            },
            timeout=30,
        )
        r_hist.raise_for_status()
        hist_json = r_hist.json()
        epoch_sectors = {}
        for s_meta, s_resp in zip(MESOSCALE_SECTORS, hist_json):
            sid = s_meta["sector_id"]
            daily = s_resp["daily"]
            hr_df = pd.DataFrame(s_resp["hourly"])
            hr_df["date"] = hr_df["time"].str.slice(0, 10)
            sm_daily = (
                hr_df.groupby("date")
                .agg(
                    sm_0_7=("soil_moisture_0_to_7cm", "mean"),
                    sm_7_28=("soil_moisture_7_to_28cm", "mean"),
                    max_hourly_precip_mm=("precipitation", "max"),
                )
                .reset_index()
            )
            p_list = [float(x or 0.0) for x in daily["precipitation_sum"]]
            api_85 = compute_api_series(p_list, k_decay=0.85)
            api_92 = compute_api_series(p_list, k_decay=0.92)
            recs = []
            for idx, dt in enumerate(daily["time"]):
                sm_row = sm_daily[sm_daily["date"] == dt]
                sm07 = float(sm_row["sm_0_7"].iloc[0]) if len(sm_row) else 0.0
                sm728 = float(sm_row["sm_7_28"].iloc[0]) if len(sm_row) else 0.0
                max_hr = float(sm_row["max_hourly_precip_mm"].iloc[0]) if len(sm_row) else 0.0
                recs.append(
                    {
                        "date": dt,
                        "precip_mm": round(p_list[idx], 2),
                        "max_hourly_mm": round(max_hr, 2),
                        "et0_mm": round(float(daily["et0_fao_evapotranspiration"][idx] or 0.0), 2),
                        "api_k85_mm": round(api_85[idx], 2),
                        "api_k92_mm": round(api_92[idx], 2),
                        "precip_prev_3d_mm": round(sum(p_list[max(0, idx - 3) : idx]), 2),
                        "precip_prev_7d_mm": round(sum(p_list[max(0, idx - 7) : idx]), 2),
                        "precip_prev_14d_mm": round(sum(p_list[max(0, idx - 14) : idx]), 2),
                        "sm_0_to_7cm_m3m3": round(sm07, 4),
                        "sm_7_to_28cm_m3m3": round(sm728, 4),
                        "root_zone_sm_m3m3": round(0.45 * sm07 + 0.55 * sm728, 4),
                    }
                )
            epoch_sectors[sid] = recs
        historical_results[epoch_key] = {
            "config": epoch_cfg,
            "sectors": epoch_sectors,
        }
        time.sleep(0.3)

    # 3. GloFAS River Discharge at Río Rocha Outlet (-17.41, -66.22)
    r_flood = requests.get(
        "https://flood-api.open-meteo.com/v1/flood",
        params={
            "latitude": -17.41,
            "longitude": -66.22,
            "daily": "river_discharge,river_discharge_mean,river_discharge_max,river_discharge_p75",
            "past_days": 30,
            "forecast_days": 14,
        },
        timeout=20,
    )
    r_flood.raise_for_status()
    glofas_op = r_flood.json()["daily"]

    out_payload = {
        "epistemological_metadata": {
            "spatial_resolution_note": (
                "Mesoscale precipitation and land-surface assimilation (ERA5-Land / GPM IMERG ~9-11 km) "
                "cannot resolve individual 2-15 km2 Tunari torrenteras. Therefore, precipitation is used "
                "strictly at its valid mesoscale sector scale to compute Multi-Day Antecedent Precipitation "
                "Index (API) and root-zone soil moisture pre-conditioning."
            ),
            "sectors": MESOSCALE_SECTORS,
        },
        "operational_2026_11": operational_sectors,
        "historical_benchmarks": historical_results,
        "glofas_rocha_discharge": glofas_op,
    }

    out_file = proc_dir / "meteo_antecedent_forcing.json"
    out_file.write_text(json.dumps(out_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[Meteo Fetcher] Saved {out_file} ({out_file.stat().st_size / 1024:.1f} KB)", flush=True)
    return out_payload


if __name__ == "__main__":
    fetch_all_meteo_and_glofas()
