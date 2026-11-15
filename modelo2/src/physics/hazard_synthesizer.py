"""
Non-Tautological Hazard Synthesizer & Urban Exposure Engine.

Couples:
1. Upper-Basin Multi-Day Antecedent Pre-Conditioning (W_ant, S_rem, Debris Bulking BF, P_crit)
2. Bare-Earth FABDEM Alluvial Fan Avulsion Corridors (PALEO-*) & Hydraulic Choke Points (AVN-*)
3. Valley-Floor Endorheic Topographic Sinks & Backwater-Locked Depressions (SINK-*)
4. GAMC Municipal Exposure Layers:
   - 14,145 Manzanas (Población y Viviendas)
   - 264 Unidades Educativas (Schools)
   - 67 Centros de Salud (Hospitals & Clinics)
   - 15 Municipal Districts (Límite Distritos)
   - 97 GAMC Emergencias Reports

Anti-Tautology Enforcement:
Explicitly separates trivial channel-proximity zones (<= 120m from mapped rivers/torrenteras)
from novel, physically derived OFF-CHANNEL hazard zones (> 120m from mapped channels):
  - Class A: Off-Channel Alluvial Fan Avulsion & Paleochannel Breakout Zones
  - Class B: Off-Channel Endorheic Pluvial & Rocha-Backwater Depressions
  - Class C: Compound Avulsion-to-Sink Terminal Traps
"""
import json
from pathlib import Path
from typing import Dict, List

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.ops import unary_union

from src.config import CRS_UTM19S, CRS_WGS84, DATA_PROCESSED, EPISTEMOLOGICAL_RULES


def run_hazard_synthesis_pipeline() -> Dict:
    gamc_dir = DATA_PROCESSED / "gamc"
    terrain_dir = DATA_PROCESSED / "terrain_physics"
    ant_dir = DATA_PROCESSED / "antecedent_forecast"
    out_dir = DATA_PROCESSED / "hazard_zones"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[Hazard Synthesizer] Loading GAMC exposure layers and physical hazard geometries...", flush=True)
    manzanas = gpd.read_file(gamc_dir / "poblacion_manzanas.geojson")
    schools = gpd.read_file(gamc_dir / "unidades_educativas.geojson")
    health = gpd.read_file(gamc_dir / "centros_salud.geojson")
    distritos = gpd.read_file(gamc_dir / "limite_distritos.geojson")
    drenaje = gpd.read_file(gamc_dir / "drenaje_influencia.geojson")
    emergencias = gpd.read_file(gamc_dir / "emergencias.geojson")
    cuencas = gpd.read_file(terrain_dir / "tunari_basins_geomorphometry.geojson")

    paleo = gpd.read_file(terrain_dir / "off_channel_paleochannel_corridors.geojson")
    sinks = gpd.read_file(terrain_dir / "off_channel_pluvial_sinks.geojson")
    avulsion_pts = gpd.read_file(terrain_dir / "fan_avulsion_chokepoints.geojson")

    ant_data = json.loads((ant_dir / "basin_antecedent_forecasts.json").read_text(encoding="utf-8"))
    meteo_data = json.loads((ant_dir / "meteo_antecedent_forcing.json").read_text(encoding="utf-8"))

    # Project all geometries to metric UTM 19S (EPSG:32719)
    manz_utm = manzanas.to_crs(CRS_UTM19S)
    sch_utm = schools.to_crs(CRS_UTM19S)
    hlth_utm = health.to_crs(CRS_UTM19S)
    dren_utm = drenaje.to_crs(CRS_UTM19S)
    paleo_utm = paleo.to_crs(CRS_UTM19S)
    sinks_utm = sinks.to_crs(CRS_UTM19S)
    av_utm = avulsion_pts.to_crs(CRS_UTM19S)
    emerg_utm = emergencias.to_crs(CRS_UTM19S)

    dren_union = unary_union(dren_utm.geometry)
    paleo_union = unary_union(paleo_utm.geometry.buffer(25.0)) if len(paleo_utm) else None
    sinks_union = unary_union(sinks_utm.geometry.buffer(25.0)) if len(sinks_utm) else None

    # Compute distance of every Manzana centroid to nearest mapped river/torrentera
    print("[Hazard Synthesizer] Evaluating 14,145 urban blocks (Manzanas) against off-channel hazard mechanisms...", flush=True)
    manz_centroids = manz_utm.geometry.centroid
    dist_channel = manz_centroids.distance(dren_union)
    manzanas["dist_to_mapped_channel_m"] = dist_channel.round(1)

    in_paleo = manz_utm.geometry.intersects(paleo_union) if paleo_union is not None else pd.Series(False, index=manzanas.index)
    in_sink = manz_utm.geometry.intersects(sinks_union) if sinks_union is not None else pd.Series(False, index=manzanas.index)

    min_buf = EPISTEMOLOGICAL_RULES["non_tautological_buffer_m"]
    is_off_channel = dist_channel > min_buf

    hazard_mechanism = np.full(len(manzanas), "LOW_BACKGROUND_RISK", dtype=object)
    # Tautological channel proximity (<= 120m) is explicitly separated from novel off-channel mechanisms
    hazard_mechanism[~is_off_channel] = "TAUTOLOGICAL_CHANNEL_BUFFER_EXCLUDED"
    hazard_mechanism[is_off_channel & in_paleo & (~in_sink)] = "NON_OBVIOUS_AVULSION_PALEOCHANNEL"
    hazard_mechanism[is_off_channel & (~in_paleo) & in_sink] = "NON_OBVIOUS_ENDORHEIC_PLUVIAL_SINK"
    hazard_mechanism[is_off_channel & in_paleo & in_sink] = "COMPOUND_AVULSION_TO_SINK_TRAP"

    manzanas["hazard_mechanism"] = hazard_mechanism
    manzanas["personas_num"] = pd.to_numeric(manzanas.get("personas", 0), errors="coerce").fillna(0).astype(int)
    manzanas["viviendas_num"] = pd.to_numeric(manzanas.get("viviendas", 0), errors="coerce").fillna(0).astype(int)

    # Save the subset of non-tautological high-risk Manzanas (>120m from channel, in Paleo or Sink)
    novel_manzanas = manzanas[
        manzanas["hazard_mechanism"].isin(
            [
                "NON_OBVIOUS_AVULSION_PALEOCHANNEL",
                "NON_OBVIOUS_ENDORHEIC_PLUVIAL_SINK",
                "COMPOUND_AVULSION_TO_SINK_TRAP",
            ]
        )
    ].copy()

    # Compute priority risk score for each novel exposed manzana
    dist_avulsion = manz_utm.loc[novel_manzanas.index].geometry.centroid.apply(
        lambda pt: float(av_utm.geometry.distance(pt).min()) if len(av_utm) else 1000.0
    )
    novel_manzanas["dist_to_avulsion_node_m"] = dist_avulsion.round(1)
    base_mech_weight = novel_manzanas["hazard_mechanism"].map(
        {
            "COMPOUND_AVULSION_TO_SINK_TRAP": 0.95,
            "NON_OBVIOUS_AVULSION_PALEOCHANNEL": 0.80,
            "NON_OBVIOUS_ENDORHEIC_PLUVIAL_SINK": 0.75,
        }
    )
    pop_factor = np.clip(novel_manzanas["personas_num"] / 250.0, 0.05, 1.0)
    novel_manzanas["composite_risk_score"] = (0.70 * base_mech_weight + 0.30 * pop_factor).round(3)

    # Save top 350 highest-exposure non-tautological Manzanas for interactive WebGIS rendering
    top_novel_manzanas = novel_manzanas.sort_values(
        ["composite_risk_score", "personas_num"], ascending=[False, False]
    ).head(350)
    top_novel_manzanas.to_file(out_dir / "non_obvious_high_risk_manzanas.geojson", driver="GeoJSON")

    # Evaluate Critical Infrastructure: Schools (264) & Health Centers (67)
    sch_dist_ch = sch_utm.geometry.distance(dren_union)
    sch_in_paleo = sch_utm.geometry.buffer(45.0).intersects(paleo_union) if paleo_union else pd.Series(False, index=schools.index)
    sch_in_sink = sch_utm.geometry.buffer(45.0).intersects(sinks_union) if sinks_union else pd.Series(False, index=schools.index)

    schools["dist_to_mapped_channel_m"] = sch_dist_ch.round(1)
    sch_mech = np.full(len(schools), "SAFE_BACKGROUND", dtype=object)
    sch_mech[sch_dist_ch <= min_buf] = "NEAR_MAPPED_CHANNEL_KNOWN"
    sch_mech[(sch_dist_ch > min_buf) & sch_in_paleo] = "OFF_CHANNEL_PALEOCHANNEL_BREAKOUT"
    sch_mech[(sch_dist_ch > min_buf) & sch_in_sink] = "OFF_CHANNEL_PLUVIAL_DEPRESSION"
    sch_mech[(sch_dist_ch > min_buf) & sch_in_paleo & sch_in_sink] = "COMPOUND_PALEO_SINK_TRAP"
    schools["hazard_mechanism"] = sch_mech
    schools.to_file(out_dir / "schools_hazard_assessment.geojson", driver="GeoJSON")

    hlth_dist_ch = hlth_utm.geometry.distance(dren_union)
    hlth_in_paleo = hlth_utm.geometry.buffer(60.0).intersects(paleo_union) if paleo_union else pd.Series(False, index=health.index)
    hlth_in_sink = hlth_utm.geometry.buffer(60.0).intersects(sinks_union) if sinks_union else pd.Series(False, index=health.index)

    health["dist_to_mapped_channel_m"] = hlth_dist_ch.round(1)
    hlth_mech = np.full(len(health), "SAFE_BACKGROUND", dtype=object)
    hlth_mech[hlth_dist_ch <= min_buf] = "NEAR_MAPPED_CHANNEL_KNOWN"
    hlth_mech[(hlth_dist_ch > min_buf) & hlth_in_paleo] = "OFF_CHANNEL_PALEOCHANNEL_BREAKOUT"
    hlth_mech[(hlth_dist_ch > min_buf) & hlth_in_sink] = "OFF_CHANNEL_PLUVIAL_DEPRESSION"
    hlth_mech[(hlth_dist_ch > min_buf) & hlth_in_paleo & hlth_in_sink] = "COMPOUND_PALEO_SINK_TRAP"
    health["hazard_mechanism"] = hlth_mech
    health.to_file(out_dir / "health_centers_hazard_assessment.geojson", driver="GeoJSON")

    # Cross-validate GAMC Emergencias against our physical hazard zones
    emerg_dist_ch = emerg_utm.geometry.distance(dren_union)
    emerg_dist_paleo = emerg_utm.geometry.distance(paleo_union) if paleo_union else pd.Series(999.0, index=emergencias.index)
    emerg_dist_sink = emerg_utm.geometry.distance(sinks_union) if sinks_union else pd.Series(999.0, index=emergencias.index)
    emergencias["dist_to_channel_m"] = emerg_dist_ch.round(1)
    emergencias["dist_to_paleo_corridor_m"] = emerg_dist_paleo.round(1)
    emergencias["dist_to_pluvial_sink_m"] = emerg_dist_sink.round(1)
    emergencias.to_file(out_dir / "emergencias_physical_context.geojson", driver="GeoJSON")

    # Aggregate District-Level Exposure Summary
    district_summary = []
    for d_name, grp in manzanas.groupby("distritos"):
        novel_grp = grp[
            grp["hazard_mechanism"].isin(
                [
                    "NON_OBVIOUS_AVULSION_PALEOCHANNEL",
                    "NON_OBVIOUS_ENDORHEIC_PLUVIAL_SINK",
                    "COMPOUND_AVULSION_TO_SINK_TRAP",
                ]
            )
        ]
        paleo_grp = grp[grp["hazard_mechanism"] == "NON_OBVIOUS_AVULSION_PALEOCHANNEL"]
        sink_grp = grp[grp["hazard_mechanism"] == "NON_OBVIOUS_ENDORHEIC_PLUVIAL_SINK"]
        comp_grp = grp[grp["hazard_mechanism"] == "COMPOUND_AVULSION_TO_SINK_TRAP"]
        taut_grp = grp[grp["hazard_mechanism"] == "TAUTOLOGICAL_CHANNEL_BUFFER_EXCLUDED"]

        district_summary.append(
            {
                "distrito": str(d_name),
                "total_manzanas": int(len(grp)),
                "total_population": int(grp["personas_num"].sum()),
                "novel_off_channel_exposed_manzanas": int(len(novel_grp)),
                "novel_off_channel_exposed_population": int(novel_grp["personas_num"].sum()),
                "novel_off_channel_exposed_dwellings": int(novel_grp["viviendas_num"].sum()),
                "avulsion_paleochannel_population": int(paleo_grp["personas_num"].sum()),
                "endorheic_sink_population": int(sink_grp["personas_num"].sum()),
                "compound_trap_population": int(comp_grp["personas_num"].sum()),
                "tautological_channel_buffer_population_excluded": int(taut_grp["personas_num"].sum()),
            }
        )
    district_summary = sorted(district_summary, key=lambda x: x["novel_off_channel_exposed_population"], reverse=True)

    # Save enriched Tunari Basins GeoJSON with Current + Historical Antecedent Attributes
    cur_map = {b["basin_id"]: b for b in ant_data["scenarios"]["current_2026_11_15"]}
    dry_map = {b["basin_id"]: b for b in ant_data["scenarios"]["benchmark_dry_2026_08_03"]}
    wet_map = {b["basin_id"]: b for b in ant_data["scenarios"]["benchmark_wet_2026_02_21"]}
    hist18_map = {b["basin_id"]: b for b in ant_data["scenarios"]["historical_2018_02_06_taquina"]}

    for col in [
        "antecedent_wetness_index",
        "remaining_soil_storage_s_mm",
        "storage_capacity_lost_pct",
        "debris_bulking_factor_bf",
        "critical_1hr_rain_threshold_mm",
        "simulated_qp_25mm_storm_m3s",
        "apex_channel_capacity_m3s",
        "alert_tier",
        "alert_label",
    ]:
        cuencas[f"now_{col}"] = [cur_map.get(int(fid), {}).get(col) for fid in cuencas["ogc_fid"]]
        cuencas[f"dry_{col}"] = [dry_map.get(int(fid), {}).get(col) for fid in cuencas["ogc_fid"]]
        cuencas[f"wet_{col}"] = [wet_map.get(int(fid), {}).get(col) for fid in cuencas["ogc_fid"]]
        cuencas[f"hist2018_{col}"] = [hist18_map.get(int(fid), {}).get(col) for fid in cuencas["ogc_fid"]]

    cuencas.to_file(out_dir / "tunari_basins_preconditioned_warning.geojson", driver="GeoJSON")

    synthesis_summary = {
        "total_manzanas_evaluated": int(len(manzanas)),
        "total_population_evaluated": int(manzanas["personas_num"].sum()),
        "non_obvious_off_channel_discoveries": {
            "total_off_channel_exposed_manzanas": int(len(novel_manzanas)),
            "total_off_channel_exposed_population": int(novel_manzanas["personas_num"].sum()),
            "total_off_channel_exposed_dwellings": int(novel_manzanas["viviendas_num"].sum()),
            "by_mechanism": {
                "NON_OBVIOUS_AVULSION_PALEOCHANNEL": {
                    "manzanas": int((manzanas["hazard_mechanism"] == "NON_OBVIOUS_AVULSION_PALEOCHANNEL").sum()),
                    "population": int(manzanas.loc[manzanas["hazard_mechanism"] == "NON_OBVIOUS_AVULSION_PALEOCHANNEL", "personas_num"].sum()),
                    "mean_dist_from_mapped_river_m": round(float(manzanas.loc[manzanas["hazard_mechanism"] == "NON_OBVIOUS_AVULSION_PALEOCHANNEL", "dist_to_mapped_channel_m"].mean()), 1),
                },
                "NON_OBVIOUS_ENDORHEIC_PLUVIAL_SINK": {
                    "manzanas": int((manzanas["hazard_mechanism"] == "NON_OBVIOUS_ENDORHEIC_PLUVIAL_SINK").sum()),
                    "population": int(manzanas.loc[manzanas["hazard_mechanism"] == "NON_OBVIOUS_ENDORHEIC_PLUVIAL_SINK", "personas_num"].sum()),
                    "mean_dist_from_mapped_river_m": round(float(manzanas.loc[manzanas["hazard_mechanism"] == "NON_OBVIOUS_ENDORHEIC_PLUVIAL_SINK", "dist_to_mapped_channel_m"].mean()), 1),
                },
                "COMPOUND_AVULSION_TO_SINK_TRAP": {
                    "manzanas": int((manzanas["hazard_mechanism"] == "COMPOUND_AVULSION_TO_SINK_TRAP").sum()),
                    "population": int(manzanas.loc[manzanas["hazard_mechanism"] == "COMPOUND_AVULSION_TO_SINK_TRAP", "personas_num"].sum()),
                    "mean_dist_from_mapped_river_m": round(float(manzanas.loc[manzanas["hazard_mechanism"] == "COMPOUND_AVULSION_TO_SINK_TRAP", "dist_to_mapped_channel_m"].mean()), 1),
                },
            },
            "schools_in_off_channel_hazard_zones": int(schools["hazard_mechanism"].isin(["OFF_CHANNEL_PALEOCHANNEL_BREAKOUT", "OFF_CHANNEL_PLUVIAL_DEPRESSION", "COMPOUND_PALEO_SINK_TRAP"]).sum()),
            "health_centers_in_off_channel_hazard_zones": int(health["hazard_mechanism"].isin(["OFF_CHANNEL_PALEOCHANNEL_BREAKOUT", "OFF_CHANNEL_PLUVIAL_DEPRESSION", "COMPOUND_PALEO_SINK_TRAP"]).sum()),
        },
        "excluded_tautological_channel_buffer": {
            "buffer_distance_m": min_buf,
            "manzanas_near_channel_excluded": int((manzanas["hazard_mechanism"] == "TAUTOLOGICAL_CHANNEL_BUFFER_EXCLUDED").sum()),
            "population_near_channel_excluded": int(manzanas.loc[manzanas["hazard_mechanism"] == "TAUTOLOGICAL_CHANNEL_BUFFER_EXCLUDED", "personas_num"].sum()),
        },
        "district_ranking": district_summary,
    }

    out_json = out_dir / "hazard_synthesis_summary.json"
    out_json.write_text(json.dumps(synthesis_summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[Hazard Synthesizer] Complete! Saved {out_json}", flush=True)
    return synthesis_summary


if __name__ == "__main__":
    run_hazard_synthesis_pipeline()
