"""
Multi-Day Antecedent Hydro-Geotechnical Pre-Conditioning & Debris-Flow Bulking Engine.

Grounded in physical hydrology (SCS-CN with Hawkins 2002 steep-mountain initial abstraction,
Kohler-Linsley multi-day API, root-zone soil moisture assimilation, non-urban SAR dielectric
saturation, and Iverson/Takahashi debris-flow sediment bulking mechanics).

Key Scientific Principle:
Because Tunari micro-watersheds have times of concentration Tc = 9 to 56 minutes while satellite
precipitation (GPM IMERG ~11 km, 4h latency) and SAR (6-12 day revisit) operate on multi-day
synoptic scales, this engine does NOT make false minute-by-minute radar rainfall predictions.
Instead, it computes from the PREVIOUS DAYS' physical state:
  1. Antecedent Catchment Saturation Index W_ant(t) in [0, 1]
  2. Dynamic Soil Storage Deficit S(t) [mm] and Effective Curve Number CN_eff(t)
  3. Debris-Flow (Mazamorra) Sediment Bulking Factor BF(t) = 1 / (1 - Cv(t))
  4. Critical Storm Trigger Threshold P_crit(t) [mm in 1h] required to exceed downstream
     urban channel capacity at each alluvial fan apex.
"""
import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from src.config import DATA_PROCESSED

# Map each of the 23 GAMC Cuencas de Influencia to its corresponding ~10 km mesoscale
# meteorological sector (Tunari West vs. Tunari East vs. Piedemonte) based on longitude/elevation
WEST_TUNARI_BASINS = {
    "C. Khora",
    "C. Chuta Khawa",
    "C. Pajcha Mayu",
    "C. Andrada",
    "C. Takho Pampa",
    "C. Pintu Mayu",
    "C. Taquiña",
}


def assign_meteo_sector(basin_name: str, z_mean_m: float) -> str:
    if "Intercuencas" in basin_name or z_mean_m < 2700.0:
        return "PIEDEMONTE_COTA2750"
    if any(w in basin_name for w in WEST_TUNARI_BASINS):
        return "TUNARI_WEST_HIGH"
    return "TUNARI_EAST_HIGH"


def compute_base_cn2(sar_row: Dict, geom_row: Dict) -> float:
    """
    Compute baseline AMC-II Curve Number (CN_II) from ESA WorldCover land-cover fractions,
    GAMC periurban encroachment, and bare-earth slope.
    """
    f_bare = sar_row.get("worldcover_bare_colluvium_frac", 0.1)
    f_grass = sar_row.get("worldcover_grass_shrub_frac", 0.7)
    f_wet = sar_row.get("worldcover_bofedal_wetland_frac", 0.02)
    f_peri = geom_row.get("periurban_encroachment_frac", 0.05)
    f_other = max(0.0, 1.0 - (f_bare + f_grass + f_wet + f_peri))

    # Standard USDA-NRCS Andean mountain hydrologic soil group B/C curve numbers
    cn2 = (
        85.0 * f_bare
        + 71.0 * f_grass
        + 91.0 * f_wet
        + 88.0 * f_peri
        + 76.0 * f_other
    )
    # Steep slope adjustment (Huang et al. 2006)
    slope_deg = geom_row.get("slope_mean_deg", 15.0)
    slope_adj = min(5.0, max(0.0, (slope_deg - 10.0) * 0.22))
    return float(np.clip(cn2 + slope_adj, 65.0, 92.0))


def cn_amc_bounds(cn2: float) -> tuple[float, float]:
    """Hawkins et al. (1985) AMC-I (dry) and AMC-III (saturated) Curve Number bounds."""
    cn1 = (4.2 * cn2) / (10.0 - 0.058 * cn2)
    cn3 = (23.0 * cn2) / (10.0 + 0.13 * cn2)
    return float(cn1), float(cn3)


def evaluate_basin_state_for_day(
    geom_row: Dict,
    sar_row: Dict,
    api_k85_mm: float,
    api_k92_mm: float,
    root_sm_m3m3: float,
    sar_saturation_override: float = None,
) -> Dict:
    """
    Evaluate physical pre-conditioning state, dynamic storage deficit S(t), debris-flow
    bulking factor BF(t), and critical 1-hr storm threshold P_crit(t) for a single basin on day t.
    """
    cn2 = compute_base_cn2(sar_row, geom_row)
    cn1, cn3 = cn_amc_bounds(cn2)

    # 1. Normalize the three antecedent state indicators to [0, 1]
    s_api = float(np.clip((0.65 * api_k85_mm + 0.35 * api_k92_mm) / 62.0, 0.0, 1.0))
    # Root-zone volumetric soil moisture normalized between wilting point (0.12) and saturation (0.40)
    s_sm = float(np.clip((root_sm_m3m3 - 0.12) / (0.40 - 0.12), 0.0, 1.0))

    sar_valid_frac = sar_row.get("sar_valid_pixel_fraction", 0.5)
    s_sar = (
        float(sar_saturation_override)
        if sar_saturation_override is not None
        else float(sar_row.get("sar_dielectric_saturation_now_nov2026", 0.3))
    )

    # Weight SAR strictly by its valid non-urban, non-layover pixel fraction in the basin
    w_sar = 0.25 * sar_valid_frac
    w_api = 0.42 + 0.15 * (1.0 - sar_valid_frac)
    w_sm = 1.0 - (w_sar + w_api)

    w_ant = float(np.clip(w_api * s_api + w_sm * s_sm + w_sar * s_sar, 0.0, 1.0))

    # 2. Dynamic Curve Number & Soil Storage Capacity Deficit S(t) [mm]
    cn_eff = cn1 + w_ant * (cn3 - cn1)
    storage_s_mm = (25400.0 / cn_eff) - 254.0
    # Steep mountain initial abstraction ratio lambda = 0.10 (Hawkins et al. 2002)
    ia_mm = 0.10 * storage_s_mm

    # Compare against dry-season baseline storage (W_ant = 0.05)
    cn_dry = cn1 + 0.05 * (cn3 - cn1)
    storage_dry_mm = (25400.0 / cn_dry) - 254.0
    storage_loss_pct = 100.0 * (1.0 - storage_s_mm / max(storage_dry_mm, 1.0))

    # 3. Debris-Flow (Mazamorra) Sediment Bulking Factor BF(t) = 1 / (1 - Cv(t))
    rm = geom_row.get("melton_ruggedness_rm", 0.2)
    f_coll = geom_row.get("colluvial_source_frac", 0.05)
    # Maximum physical sediment volume concentration Cv_max (Iverson 1997: debris flows reach Cv ~ 0.45-0.55)
    cv_max = float(np.clip(0.32 * min(1.2, rm / 0.40) + 0.45 * min(1.0, f_coll / 0.30), 0.08, 0.54))
    # Sediment mobilization activates non-linearly once antecedent saturation wets colluvial hollows (W_ant > 0.28)
    moisture_activation = float(np.clip((w_ant - 0.25) / 0.75, 0.0, 1.0) ** 1.30)
    cv_t = cv_max * moisture_activation
    bulking_factor = float(1.0 / (1.0 - cv_t))

    # 4. Critical 1-Hour Convective Rainfall Trigger Depth P_crit(t) [mm]
    # Downstream urban channel safe capacity scales with A^0.62, penalized by DSM building constriction
    area_km2 = max(geom_row.get("area_km2", 5.0), 0.5)
    tc_hr = max(geom_row.get("tc_kirpich_min", 20.0) / 60.0, 0.15)
    tp_hr = 0.6 * tc_hr + 0.5 * 1.0  # For a 1-hour convective storm cell

    dz_obstr = geom_row.get("mean_dsm_obstruction_m", 1.5)
    constriction_penalty = float(np.clip(1.0 - 0.06 * max(0.0, dz_obstr - 1.0), 0.68, 1.0))
    # Empirical bankfull safe capacity at the Cochabamba urban fan apex (m³/s)
    q_cap_m3s = 5.2 * (area_km2 ** 0.65) * constriction_penalty

    # Required clear-water runoff depth Q_req (mm) before bulking exceeds q_cap_m3s:
    # Q_p_bulked = BF(t) * (0.208 * A * Q_req) / Tp  =>  Q_req = (q_cap * Tp) / (0.208 * A * BF)
    q_req_mm = (q_cap_m3s * tp_hr) / (0.208 * area_km2 * bulking_factor)

    # Invert SCS runoff equation Q = (P - Ia)^2 / (P - Ia + S) for X = P - Ia:
    # X^2 - Q*X - Q*S = 0  =>  X = 0.5 * (Q + sqrt(Q^2 + 4*Q*S))
    x_mm = 0.5 * (q_req_mm + np.sqrt(q_req_mm ** 2 + 4.0 * q_req_mm * storage_s_mm))
    p_crit_1hr_mm = float(ia_mm + x_mm)

    # Also compute simulated peak bulked discharge for a standard 25 mm / 1 hr wet-season storm
    p_ref = 25.0
    q_runoff_25 = ((p_ref - ia_mm) ** 2) / (p_ref - ia_mm + storage_s_mm) if p_ref > ia_mm else 0.0
    qp_bulked_25_m3s = float(bulking_factor * (0.208 * area_km2 * q_runoff_25) / tp_hr)
    capacity_exceedance_ratio_25mm = float(qp_bulked_25_m3s / max(q_cap_m3s, 0.1))

    # Classify Pre-Conditioned Warning Level based on P_crit and exceedance ratio
    if p_crit_1hr_mm <= 18.0 or (w_ant >= 0.72 and bulking_factor >= 1.45):
        alert_tier = "RED_CRITICAL_PRECONDITIONED"
        alert_label = "Crítico (Cuenca Saturada / Propensa a Mazamorra con Lluvia Moderada)"
    elif p_crit_1hr_mm <= 26.0 or w_ant >= 0.48:
        alert_tier = "ORANGE_HIGH_SUSCEPTIBILITY"
        alert_label = "Alerta Naranja (Capacidad de Infiltración Reducida / Bulking Activo)"
    elif p_crit_1hr_mm <= 35.0 or w_ant >= 0.28:
        alert_tier = "YELLOW_MODERATE_WATCH"
        alert_label = "Vigilancia Amarilla (Humedecimiento Antecedente en Transición)"
    else:
        alert_tier = "GREEN_HIGH_STORAGE_BUFFER"
        alert_label = "Verde (Suelo Seco / Alta Capacidad de Absorción Hidrológica)"

    return {
        "cn_ii_base": round(cn2, 1),
        "cn_eff_t": round(cn_eff, 1),
        "antecedent_wetness_index": round(w_ant, 3),
        "remaining_soil_storage_s_mm": round(storage_s_mm, 1),
        "initial_abstraction_ia_mm": round(ia_mm, 1),
        "storage_capacity_lost_pct": round(storage_loss_pct, 1),
        "sediment_volume_conc_cv": round(cv_t, 3),
        "debris_bulking_factor_bf": round(bulking_factor, 2),
        "apex_channel_capacity_m3s": round(q_cap_m3s, 1),
        "critical_1hr_rain_threshold_mm": round(p_crit_1hr_mm, 1),
        "simulated_qp_25mm_storm_m3s": round(qp_bulked_25_m3s, 1),
        "capacity_exceedance_ratio_25mm": round(capacity_exceedance_ratio_25mm, 2),
        "alert_tier": alert_tier,
        "alert_label": alert_label,
    }


def run_antecedent_hydro_pipeline() -> Dict:
    terrain_dir = DATA_PROCESSED / "terrain_physics"
    sar_dir = DATA_PROCESSED / "sar_analysis"
    out_dir = DATA_PROCESSED / "antecedent_forecast"
    out_dir.mkdir(parents=True, exist_ok=True)

    terrain_summary = json.loads((terrain_dir / "terrain_physics_summary.json").read_text(encoding="utf-8"))
    sar_summary = json.loads((sar_dir / "sar_dielectric_summary.json").read_text(encoding="utf-8"))
    meteo_data = json.loads((out_dir / "meteo_antecedent_forcing.json").read_text(encoding="utf-8"))

    geom_by_id = {b["basin_id"]: b for b in terrain_summary["basin_metrics"]}
    sar_by_id = {b["basin_id"]: b for b in sar_summary["basin_sar_metrics"]}

    # 1. Evaluate all 23 Basins across 4 Canonical Scenarios:
    #    (a) Current Operational State (Today: 2026-11-15, based on previous 14 days Nov 1-14, 2026)
    #    (b) 7-Day Forecast Peak State (2026-11-21, incorporating next week's predicted wetting)
    #    (c) Historical Disaster Benchmark 1: Eve of 6 Feb 2018 Taquiña Mazamorra (2018-02-06)
    #    (d) Historical Disaster Benchmark 2: Eve of 21 Feb 2020 Taquiña Mazamorra (2020-02-21)
    #    (e) Peak Wet Season SAR Benchmark (2026-02-21)
    #    (f) Bone-Dry Winter Baseline (2026-08-03)

    def get_sector_day(sector_series: List[Dict], target_date: str) -> Dict:
        for r in sector_series:
            if r["date"] == target_date:
                return r
        return sector_series[-1]

    scenarios_output = {
        "current_2026_11_15": [],
        "forecast_2026_11_21": [],
        "historical_2018_02_06_taquina": [],
        "historical_2020_02_21_taquina": [],
        "benchmark_wet_2026_02_21": [],
        "benchmark_dry_2026_08_03": [],
    }

    for b_id, geom_row in geom_by_id.items():
        sar_row = sar_by_id[b_id]
        sector_id = assign_meteo_sector(geom_row["basin_name"], geom_row["z_mean_m"])

        # (a) Current 2026-11-15
        op_series = meteo_data["operational_2026_11"][sector_id]["daily_series"]
        d_now = get_sector_day(op_series, "2026-11-15")
        st_now = evaluate_basin_state_for_day(
            geom_row,
            sar_row,
            d_now["api_k85_mm"],
            d_now["api_k92_mm"],
            d_now["root_zone_sm_m3m3"] or 0.24,
            sar_saturation_override=sar_row["sar_dielectric_saturation_now_nov2026"],
        )
        scenarios_output["current_2026_11_15"].append({**geom_row, "sector_id": sector_id, "forcing_date": "2026-11-15", **st_now})

        # (b) Forecast 2026-11-21
        d_fc = op_series[-1]
        st_fc = evaluate_basin_state_for_day(
            geom_row,
            sar_row,
            d_fc["api_k85_mm"],
            d_fc["api_k92_mm"],
            d_fc["root_zone_sm_m3m3"] or 0.26,
            sar_saturation_override=min(1.0, sar_row["sar_dielectric_saturation_now_nov2026"] + 0.08),
        )
        scenarios_output["forecast_2026_11_21"].append({**geom_row, "sector_id": sector_id, "forcing_date": d_fc["date"], **st_fc})

        # (c) Historical 2018-02-06 Taquiña Disaster
        s_2018 = meteo_data["historical_benchmarks"]["2018_taquina_disaster"]["sectors"][sector_id]
        d_2018 = get_sector_day(s_2018, "2018-02-06")
        st_2018 = evaluate_basin_state_for_day(
            geom_row,
            sar_row,
            d_2018["api_k85_mm"],
            d_2018["api_k92_mm"],
            d_2018["root_zone_sm_m3m3"],
            sar_saturation_override=min(0.96, sar_row["sar_dielectric_saturation_wet_feb2026"] * 1.15),
        )
        scenarios_output["historical_2018_02_06_taquina"].append({**geom_row, "sector_id": sector_id, "forcing_date": "2018-02-06", "prev_14d_rain_mm": d_2018["precip_prev_14d_mm"], **st_2018})

        # (d) Historical 2020-02-21 Taquiña Disaster
        s_2020 = meteo_data["historical_benchmarks"]["2020_taquina_disaster"]["sectors"][sector_id]
        d_2020 = get_sector_day(s_2020, "2020-02-21")
        st_2020 = evaluate_basin_state_for_day(
            geom_row,
            sar_row,
            d_2020["api_k85_mm"],
            d_2020["api_k92_mm"],
            d_2020["root_zone_sm_m3m3"],
            sar_saturation_override=min(0.95, sar_row["sar_dielectric_saturation_wet_feb2026"] * 1.12),
        )
        scenarios_output["historical_2020_02_21_taquina"].append({**geom_row, "sector_id": sector_id, "forcing_date": "2020-02-21", "prev_14d_rain_mm": d_2020["precip_prev_14d_mm"], **st_2020})

        # (e) Peak Wet Season SAR 2026-02-21
        s_wet26 = meteo_data["historical_benchmarks"]["2026_wet_season_sar"]["sectors"][sector_id]
        d_wet26 = get_sector_day(s_wet26, "2026-02-21")
        st_wet26 = evaluate_basin_state_for_day(
            geom_row,
            sar_row,
            d_wet26["api_k85_mm"],
            d_wet26["api_k92_mm"],
            d_wet26["root_zone_sm_m3m3"],
            sar_saturation_override=sar_row["sar_dielectric_saturation_wet_feb2026"],
        )
        scenarios_output["benchmark_wet_2026_02_21"].append({**geom_row, "sector_id": sector_id, "forcing_date": "2026-02-21", "prev_14d_rain_mm": d_wet26["precip_prev_14d_mm"], **st_wet26})

        # (f) Bone-Dry Baseline 2026-08-03
        s_dry26 = meteo_data["historical_benchmarks"]["2026_dry_season_sar"]["sectors"][sector_id]
        d_dry26 = get_sector_day(s_dry26, "2026-08-03")
        st_dry26 = evaluate_basin_state_for_day(
            geom_row,
            sar_row,
            d_dry26["api_k85_mm"],
            d_dry26["api_k92_mm"],
            d_dry26["root_zone_sm_m3m3"],
            sar_saturation_override=sar_row["sar_dielectric_saturation_dry_aug2026"],
        )
        scenarios_output["benchmark_dry_2026_08_03"].append({**geom_row, "sector_id": sector_id, "forcing_date": "2026-08-03", "prev_14d_rain_mm": d_dry26["precip_prev_14d_mm"], **st_dry26})

    # 2. Generate Full Daily Time-Series Trajectory for Key Reference Catchments (Taquiña, K'hora, Pintumayu, Pajcha Mayu, Chaquimayu)
    tracked_names = {"C. Taquiña", "C. Khora", "C. Pintu Mayu", "C. Pajcha Mayu", "C. Chaquimayu", "C. Chuta Khawa"}
    taquina_row = next(b for b in terrain_summary["basin_metrics"] if b["basin_name"] == "C. Taquiña")
    taquina_sar = sar_by_id[taquina_row["basin_id"]]

    daily_trajectories = {}
    for ep_key in ["2018_taquina_disaster", "2020_taquina_disaster", "2026_wet_season_sar", "2026_dry_season_sar"]:
        sec_series = meteo_data["historical_benchmarks"][ep_key]["sectors"]["TUNARI_WEST_HIGH"]
        traj = []
        for d in sec_series:
            sar_est = np.clip((d["root_zone_sm_m3m3"] - 0.12) / 0.28, 0.05, 0.95)
            st = evaluate_basin_state_for_day(
                taquina_row, taquina_sar, d["api_k85_mm"], d["api_k92_mm"], d["root_zone_sm_m3m3"], sar_saturation_override=sar_est
            )
            traj.append(
                {
                    "date": d["date"],
                    "precip_mm": d["precip_mm"],
                    "precip_prev_7d_mm": d["precip_prev_7d_mm"],
                    "precip_prev_14d_mm": d["precip_prev_14d_mm"],
                    "api_k85_mm": d["api_k85_mm"],
                    "root_zone_sm_m3m3": d["root_zone_sm_m3m3"],
                    "antecedent_wetness_index": st["antecedent_wetness_index"],
                    "remaining_soil_storage_s_mm": st["remaining_soil_storage_s_mm"],
                    "debris_bulking_factor_bf": st["debris_bulking_factor_bf"],
                    "critical_1hr_rain_threshold_mm": st["critical_1hr_rain_threshold_mm"],
                    "alert_tier": st["alert_tier"],
                }
            )
        daily_trajectories[ep_key] = traj

    # Also operational Nov 2026 trajectory for Taquiña
    op_traj = []
    for d in meteo_data["operational_2026_11"]["TUNARI_WEST_HIGH"]["daily_series"]:
        sm_val = d["root_zone_sm_m3m3"] or 0.24
        st = evaluate_basin_state_for_day(
            taquina_row, taquina_sar, d["api_k85_mm"], d["api_k92_mm"], sm_val, sar_saturation_override=taquina_sar["sar_dielectric_saturation_now_nov2026"]
        )
        op_traj.append(
            {
                "date": d["date"],
                "precip_mm": d["precip_mm"],
                "precip_prev_7d_mm": d["precip_prev_7d_mm"],
                "precip_prev_14d_mm": d["precip_prev_14d_mm"],
                "api_k85_mm": d["api_k85_mm"],
                "root_zone_sm_m3m3": sm_val,
                "antecedent_wetness_index": st["antecedent_wetness_index"],
                "remaining_soil_storage_s_mm": st["remaining_soil_storage_s_mm"],
                "debris_bulking_factor_bf": st["debris_bulking_factor_bf"],
                "critical_1hr_rain_threshold_mm": st["critical_1hr_rain_threshold_mm"],
                "alert_tier": st["alert_tier"],
            }
        )
    daily_trajectories["operational_2026_11"] = op_traj

    out_payload = {
        "scenarios": scenarios_output,
        "taquina_daily_trajectories": daily_trajectories,
    }
    out_path = out_dir / "basin_antecedent_forecasts.json"
    out_path.write_text(json.dumps(out_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[Antecedent Hydro] Complete! Saved {out_path}", flush=True)
    return out_payload


if __name__ == "__main__":
    run_antecedent_hydro_pipeline()
