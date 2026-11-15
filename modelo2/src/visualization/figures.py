"""
Publication-Grade Scientific Figures Generator
==============================================
Generates 5 high-resolution diagnostic figures in docs/figures/ demonstrating:
1. fig1_dsm_vs_fabdem_proof.png — Bare-Earth FABDEM V1-2 vs. Copernicus GLO-30 DSM proof
2. fig2_sar_epistemological_domains.png — Urban Double-Bounce Clutter vs. Cota-2750 Dielectric Wetting & Dual-Orbit Fusion
3. fig3_taquina_backtest_2018_2020_2026.png — Historical 2018 & 2020 Taquiña Mazamorra Multi-Day Pre-Conditioning Backtests
4. fig4_non_tautological_hazard_map.png — Non-Tautological Off-Channel Hazard Mechanisms (>120 m from rivers)
5. fig5_district_exposure_and_critical_thresholds.png — District Exposure by Mechanism & Basin Critical Trigger Thresholds P_crit
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import Resampling, reproject

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROC = PROJECT_ROOT / "data" / "processed"
FIG_DIR = PROJECT_ROOT / "docs" / "figures"

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
        "axes.edgecolor": "#334155",
        "axes.linewidth": 0.8,
        "grid.color": "#cbd5e1",
        "grid.linestyle": "--",
        "grid.alpha": 0.5,
    }
)


def generate_fig1_dsm_vs_fabdem() -> Path:
    """Figure 1: Copernicus GLO-30 DSM vs. Bare-Earth FABDEM V1-2 Proof."""
    print("[Figures] Generating Figure 1: DSM vs FABDEM bare-earth proof...")
    terrain_sum = json.loads(
        (DATA_PROC / "terrain_physics" / "terrain_physics_summary.json").read_text(encoding="utf-8")
    )
    proof = terrain_sum["dsm_vs_fabdem_proof"]

    # Load FABDEM & Copernicus DSM over central Cochabamba alluvial fan & city
    bbox = (-66.24, -17.46, -66.11, -17.32)
    fab_path = DATA_RAW / "fabdem" / "S18W067_FABDEM_V1-2.tif"
    dsm_path = DATA_RAW / "fabdem" / "Copernicus_DSM_COG_10_S18_00_W067_00_DEM.tif"

    with rasterio.open(fab_path) as src_fab:
        win = rasterio.windows.from_bounds(*bbox, transform=src_fab.transform)
        win = win.round_offsets().round_lengths()
        z_fab = src_fab.read(1, window=win).astype(np.float32)
        win_transform = src_fab.window_transform(win)

    with rasterio.open(dsm_path) as src_dsm:
        z_dsm = np.empty_like(z_fab, dtype=np.float32)
        reproject(
            source=rasterio.band(src_dsm, 1),
            destination=z_dsm,
            src_transform=src_dsm.transform,
            src_crs=src_dsm.crs,
            dst_transform=win_transform,
            dst_crs="EPSG:4326",
            resampling=Resampling.bilinear,
        )

    dz = np.clip(z_dsm - z_fab, -2.0, 18.0)
    drenaje = gpd.read_file(DATA_PROC / "gamc" / "drenaje_influencia.geojson")
    cota2750 = gpd.read_file(DATA_PROC / "gamc" / "cota_2750.geojson")

    fig = plt.figure(figsize=(16, 5.8), dpi=220, facecolor="#f8fafc")
    gs = fig.add_gridspec(1, 3, width_ratios=[1.35, 1.0, 0.95], wspace=0.26)

    # Panel A: Spatial Map of Delta Z = DSM - FABDEM
    ax0 = fig.add_subplot(gs[0])
    extent = [bbox[0], bbox[2], bbox[1], bbox[3]]
    im = ax0.imshow(
        dz,
        extent=extent,
        origin="upper",
        cmap="inferno",
        vmin=0.0,
        vmax=12.0,
        aspect="auto",
    )
    drenaje.plot(ax=ax0, color="#38bdf8", linewidth=1.1, alpha=0.85)
    cota2750[cota2750.geometry.type.isin(["LineString", "MultiLineString", "Polygon", "MultiPolygon"])].boundary.plot(
        ax=ax0, color="#22c55e", linewidth=1.3, linestyle="--"
    )
    ax0.set_xlim(bbox[0], bbox[2])
    ax0.set_ylim(bbox[1], bbox[3])
    ax0.set_title(
        "A. Elevation Bias ΔZ = DSM (GLO-30) − Bare-Earth (FABDEM V1-2)\nBuilding & Riparian Canopy Artifacts Blocking Flow Routing",
        fontsize=10.5,
        fontweight="bold",
        color="#0f172a",
    )
    ax0.set_xlabel("Longitude (°W)", fontsize=9)
    ax0.set_ylabel("Latitude (°S)", fontsize=9)
    cb = fig.colorbar(im, ax=ax0, fraction=0.042, pad=0.03)
    cb.set_label("ΔZ = Z_DSM − Z_FABDEM (m)", fontsize=8.5)
    ax0.legend(
        handles=[
            plt.Line2D([0], [0], color="#38bdf8", lw=1.4, label="Torrenteras / Río Rocha"),
            plt.Line2D([0], [0], color="#22c55e", lw=1.4, ls="--", label="Cota 2750 m Boundary"),
        ],
        loc="upper right",
        fontsize=8,
        framealpha=0.92,
    )

    # Panel B: Bias Distribution Comparison
    ax1 = fig.add_subplot(gs[1])
    categories = [
        "Urban Matrix\n(Mean ΔZ)",
        "Riparian ≤90m\n(Mean ΔZ)",
        "Urban Matrix\n(90th Pct ΔZ)",
        "Riparian ≤90m\n(90th Pct ΔZ)",
    ]
    vals = [
        proof["urban_mean_delta_z_m"],
        proof["channel_corridor_mean_delta_z_m"],
        proof["urban_p90_delta_z_m"],
        proof["channel_corridor_p90_delta_z_m"],
    ]
    colors = ["#64748b", "#f97316", "#475569", "#dc2626"]
    bars = ax1.bar(categories, vals, color=colors, width=0.58, edgecolor="#1e293b", linewidth=0.8)
    ax1.axhline(3.0, color="#dc2626", linestyle="--", linewidth=1.1, label="False-Dam Threshold (+3.0 m)")
    for b, v in zip(bars, vals):
        ax1.text(
            b.get_x() + b.get_width() / 2,
            v + 0.22,
            f"+{v:.2f} m",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
            color="#0f172a",
        )
    ax1.set_ylim(0, 10.0)
    ax1.grid(axis="y")
    ax1.set_ylabel("Positive Elevation Bias vs. Bare Earth (m)", fontsize=9)
    ax1.set_title(
        f"B. Riparian Corridor Constriction Bias\n({proof['false_dsm_dams_along_channels_count']:,} False Dam Pixels >3m on Channels)",
        fontsize=10.5,
        fontweight="bold",
        color="#0f172a",
    )
    ax1.tick_params(axis="x", labelsize=8.5)
    ax1.legend(loc="upper left", fontsize=8)

    # Panel C: False Sinks vs True Bare-Earth Depressions
    ax2 = fig.add_subplot(gs[2])
    sink_labels = [
        "Artificial DSM Sinks\n(Street-Wall Artifacts\nRemoved by FABDEM)",
        "True Bare-Earth Sinks\n(Geomorphic Endorheic &\nBackwater Depressions)",
    ]
    sink_vals = [proof["false_dsm_sink_area_ha"], proof["true_bare_earth_sink_area_ha"]]
    s_bars = ax2.bar(
        sink_labels,
        sink_vals,
        color=["#94a3b8", "#0284c7"],
        width=0.52,
        edgecolor="#1e293b",
        linewidth=0.8,
    )
    for b, v in zip(s_bars, sink_vals):
        ax2.text(
            b.get_x() + b.get_width() / 2,
            v + 15,
            f"{v:.1f} ha",
            ha="center",
            va="bottom",
            fontsize=9.5,
            fontweight="bold",
            color="#0f172a",
        )
    ax2.set_ylim(0, 760)
    ax2.grid(axis="y")
    ax2.set_ylabel("Total Depression Area in Valley (ha)", fontsize=9)
    ax2.set_title(
        "C. Topographic Sink Fidelity\nWhy Standard DSMs Corrupt Pluvial Pooling",
        fontsize=10.5,
        fontweight="bold",
        color="#0f172a",
    )
    ax2.tick_params(axis="x", labelsize=8.5)

    fig.suptitle(
        "Epistemological Proof 1: Why Bare-Earth FABDEM V1-2 Is Mandatory Over Standard DSMs in Cochabamba",
        fontsize=13,
        fontweight="bold",
        color="#0f172a",
        y=0.99,
    )
    out_path = FIG_DIR / "fig1_dsm_vs_fabdem_proof.png"
    fig.savefig(out_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path


def generate_fig2_sar_domains() -> Path:
    """Figure 2: SAR Urban Double-Bounce Clutter vs. Cota-2750 Dielectric Wetting & Dual-Orbit Fusion."""
    print("[Figures] Generating Figure 2: SAR epistemological domains & dual-orbit layover recovery...")
    sar_sum = json.loads(
        (DATA_PROC / "sar_analysis" / "sar_dielectric_summary.json").read_text(encoding="utf-8")
    )
    urb = sar_sum["urban_vs_natural_proof"]["urban_builtup_domain"]
    tun = sar_sum["urban_vs_natural_proof"]["upper_tunari_watersheds_above_cota2750"]
    basins = sar_sum["basin_sar_metrics"]

    fig = plt.figure(figsize=(16, 5.6), dpi=220, facecolor="#f8fafc")
    gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 1.25, 0.95], wspace=0.27)

    # Panel A: Urban Clutter vs Upper Tunari Backscatter (Dry vs Wet vs P90 Hollows)
    ax0 = fig.add_subplot(gs[0])
    x = np.arange(2)
    width = 0.26
    dry_vals = [urb["cband_vv_dry_mean_db"], tun["cband_vv_dry_mean_db"]]
    wet_vals = [urb["cband_vv_wet_mean_db"], tun["cband_vv_wet_mean_db"]]
    lband_vals = [urb["lband_hh_mean_db"], tun["lband_hh_mean_db"]]

    b1 = ax0.bar(x - width, dry_vals, width, label="S1 C-Band VV Dry (Aug 2026)", color="#f59e0b", edgecolor="#1e293b")
    b2 = ax0.bar(x, wet_vals, width, label="S1 C-Band VV Wet (Feb 2026)", color="#0284c7", edgecolor="#1e293b")
    b3 = ax0.bar(x + width, lband_vals, width, label="ALOS-2/NISAR L-Band HH", color="#10b981", edgecolor="#1e293b")

    ax0.axhline(-3.5, color="#dc2626", linestyle="--", linewidth=1.1, label="Corner-Reflector Threshold (-3.5 dB)")
    ax0.set_xticks(x)
    ax0.set_xticklabels(
        [
            f"Urban Built-Up\n(52.1% Corner Clutter)\nΔγ° = {urb['cband_seasonal_dynamic_range_db']:+.2f} dB (Noise)",
            f"Upper Tunari (>2750m)\n(Natural Pajonal/Colluvium)\nΔγ° = +{tun['cband_seasonal_dynamic_range_db']:.2f} dB (+{tun['cband_p90_dynamic_range_db']:.1f} dB P90)",
        ],
        fontsize=8.5,
        fontweight="bold",
    )
    ax0.set_ylim(-15.5, 0.0)
    ax0.set_ylabel("Radiometric Terrain-Corrected Backscatter γ° (dB)", fontsize=9)
    ax0.set_title(
        "A. Urban Double-Bounce Clutter vs. Mountain Soil Signal\nWhy SAR Must Be Masked Inside Limite Urbano",
        fontsize=10.5,
        fontweight="bold",
    )
    ax0.grid(axis="y")
    ax0.legend(loc="lower left", fontsize=7.8, framealpha=0.92)

    # Panel B: Basin-by-Basin Seasonal Dielectric Wetting vs Valid Non-Urban Pixel Fraction
    ax1 = fig.add_subplot(gs[1])
    valid_fracs = [b["sar_valid_pixel_fraction"] * 100.0 for b in basins]
    wet_deltas = [b["s1_seasonal_delta_vv_db"] for b in basins]
    sat_wet = [b["sar_dielectric_saturation_wet_feb2026"] for b in basins]
    names = [b["basin_name"] for b in basins]

    sc = ax1.scatter(
        valid_fracs,
        wet_deltas,
        c=sat_wet,
        cmap="YlGnBu",
        s=75,
        edgecolors="#0f172a",
        linewidth=0.8,
        vmin=0.1,
        vmax=0.85,
        zorder=4,
    )
    ax1.axhline(0.0, color="#64748b", linestyle=":", linewidth=1.0)
    ax1.axvline(50.0, color="#dc2626", linestyle="--", linewidth=1.0, label="Min Valid Non-Urban Area (50%)")

    highlight_basins = {"C. Taquiña", "C. Wara Wara", "C. Pintu Mayu", "C. Khora", "C. Pajcha Mayu", "Intercuencas y areas de aporte"}
    for vf, wd, nm in zip(valid_fracs, wet_deltas, names):
        if nm in highlight_basins:
            short_nm = "Intercuencas (Urban)" if "Intercuencas" in nm else nm
            is_right = vf > 75.0
            ax1.annotate(
                short_nm,
                (vf, wd),
                xytext=(-7 if is_right else 6, 3),
                textcoords="offset points",
                ha="right" if is_right else "left",
                fontsize=7.8,
                fontweight="bold",
                color="#0f172a",
            )

    ax1.set_xlim(-5, 108)
    ax1.set_ylim(-1.1, 2.3)

    cb1 = fig.colorbar(sc, ax=ax1, fraction=0.042, pad=0.03)
    cb1.set_label("Wet-Season SAR Dielectric Saturation Index", fontsize=8.5)
    ax1.set_xlabel("Valid Non-Urban / Non-Layover Basin Pixel Fraction (%)", fontsize=9)
    ax1.set_ylabel("Seasonal C-Band Wetting Δγ°_VV (Wet − Dry, dB)", fontsize=9)
    ax1.set_title(
        "B. Dielectric Soil Wetting Across 23 Tunari Catchments\nStrong Signal in High-Altitude Catchments (>85% Valid)",
        fontsize=10.5,
        fontweight="bold",
    )
    ax1.grid(True)
    ax1.legend(loc="upper left", fontsize=8)

    # Panel C: Steep-Cordillera Layover Loss Recovery via Dual-Orbit Fusion
    ax2 = fig.add_subplot(gs[2])
    orbit_labels = [
        "Descending Only\n(Orbit 156)",
        "Ascending Only\n(Orbit 003)",
        "Dual-Orbit Fused\n(Asc 003 + Desc 156)",
    ]
    layover_pct = [
        tun["single_orbit_layover_fraction_desc"] * 100.0,
        tun["single_orbit_layover_fraction_asc"] * 100.0,
        tun["unrecoverable_cliff_fraction_after_dual_orbit"] * 100.0,
    ]
    obars = ax2.bar(
        orbit_labels,
        layover_pct,
        color=["#ef4444", "#f97316", "#16a34a"],
        width=0.54,
        edgecolor="#1e293b",
    )
    for b, v in zip(obars, layover_pct):
        ax2.text(
            b.get_x() + b.get_width() / 2,
            v + 0.35,
            f"{v:.1f}% Lost\n({100.0 - v:.1f}% Valid)",
            ha="center",
            va="bottom",
            fontsize=8.5,
            fontweight="bold",
        )
    ax2.set_ylim(0, 14.5)
    ax2.grid(axis="y")
    ax2.set_ylabel("Topographic Layover / Shadow Loss (%)", fontsize=9)
    ax2.set_title(
        "C. Cordillera Tunari Layover Mitigation\nAspect-Weighted Dual-Orbit RTC Fusion",
        fontsize=10.5,
        fontweight="bold",
    )
    ax2.tick_params(axis="x", labelsize=8.5)

    fig.suptitle(
        "Epistemological Proof 2: SAR Operational Validity Domain (Cota 2750 Masking & Dual-Orbit Fusion)",
        fontsize=13,
        fontweight="bold",
        color="#0f172a",
        y=0.99,
    )
    out_path = FIG_DIR / "fig2_sar_epistemological_domains.png"
    fig.savefig(out_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path


def generate_fig3_taquina_backtest() -> Path:
    """Figure 3: Multi-Day Antecedent Pre-Conditioning Backtest on 2018 & 2020 Taquiña Disasters."""
    print("[Figures] Generating Figure 3: 2018 & 2020 Taquiña Mazamorra historical backtest...")
    hydro = json.loads(
        (DATA_PROC / "antecedent_forecast" / "basin_antecedent_forecasts.json").read_text(encoding="utf-8")
    )
    trajs = hydro["taquina_daily_trajectories"]

    t18 = [d for d in trajs["2018_taquina_disaster"] if d["date"] <= "2018-02-06"]
    t20 = [d for d in trajs["2020_taquina_disaster"] if d["date"] <= "2020-02-21"]
    t26 = trajs["operational_2026_11"]

    # Align trajectories by "Days Relative to Event / Target Date" (-21 to 0)
    def to_rel_df(traj: list[dict], ref_idx: int = -1) -> pd.DataFrame:
        df = pd.DataFrame(traj)
        n = len(df) if ref_idx == -1 else ref_idx + 1
        df["rel_day"] = np.arange(len(df)) - (n - 1)
        return df[df["rel_day"] >= -21].copy()

    df18 = to_rel_df(t18)
    df20 = to_rel_df(t20)
    # For operational Nov 2026, day 0 = 2026-11-15 (today), +1..+6 = 7-day forecast
    idx_now = next(i for i, d in enumerate(t26) if d["date"] == "2026-11-15")
    df26 = to_rel_df(t26, ref_idx=idx_now)

    fig, axes = plt.subplots(2, 2, figsize=(15.5, 9.2), dpi=220, facecolor="#f8fafc")
    axA, axB, axC, axD = axes.flatten()

    # Panel A: 14-Day Antecedent Precipitation Index (API_k85)
    axA.plot(df18["rel_day"], df18["api_k85_mm"], "-o", color="#dc2626", linewidth=2.2, markersize=4, label="2018-02-06 Taquiña Disaster (Peak API = 86.9 mm)")
    axA.plot(df20["rel_day"], df20["api_k85_mm"], "-s", color="#ea580c", linewidth=2.0, markersize=4, label="2020-02-21 Taquiña Disaster (Peak API = 63.2 mm)")
    axA.plot(df26["rel_day"], df26["api_k85_mm"], "--^", color="#0284c7", linewidth=2.0, markersize=4, label="Nov 2026 Operational + Forecast (Pre-Wet Transition)")
    axA.axvline(0, color="#0f172a", linestyle="--", linewidth=1.2, label="Day 0 (Catastrophe / Operational Today)")
    axA.set_title("A. Multi-Day Antecedent Precipitation Index (API, k=0.85)", fontsize=10.5, fontweight="bold")
    axA.set_xlabel("Days Relative to Disaster / Evaluation Date", fontsize=9)
    axA.set_ylabel("API_k85 (mm)", fontsize=9)
    axA.grid(True)
    axA.legend(loc="upper left", fontsize=8)

    # Panel B: Composite Antecedent Wetness Index W_ant(t) & Alert Tier Zones
    axB.axhspan(0.72, 1.05, color="#fecaca", alpha=0.45, label="RED: Critical Pre-Conditioned (W_ant ≥ 0.72)")
    axB.axhspan(0.48, 0.72, color="#fed7aa", alpha=0.45, label="ORANGE: High Susceptibility (0.48–0.72)")
    axB.axhspan(0.28, 0.48, color="#fef08a", alpha=0.40, label="YELLOW: Moderate Watch (0.28–0.48)")
    axB.plot(df18["rel_day"], df18["antecedent_wetness_index"], "-o", color="#dc2626", linewidth=2.2, markersize=4, label="2018 Taquiña (Crosses RED at Day -9)")
    axB.plot(df20["rel_day"], df20["antecedent_wetness_index"], "-s", color="#ea580c", linewidth=2.0, markersize=4, label="2020 Taquiña (Crosses RED at Day -17)")
    axB.plot(df26["rel_day"], df26["antecedent_wetness_index"], "--^", color="#0284c7", linewidth=2.0, markersize=4, label="Nov 2026 Operational + 7d Forecast")
    axB.axvline(0, color="#0f172a", linestyle="--", linewidth=1.2)
    axB.set_ylim(0.15, 1.03)
    axB.set_title("B. Basin Antecedent Wetness State W_ant(t) & Warning Lead Time", fontsize=10.5, fontweight="bold")
    axB.set_xlabel("Days Relative to Disaster / Evaluation Date", fontsize=9)
    axB.set_ylabel("Composite Antecedent Wetness W_ant [0–1]", fontsize=9)
    axB.grid(True)
    axB.legend(loc="lower left", fontsize=7.6, ncol=2)

    # Panel C: Dynamic Soil Storage Capacity S(t) Collapse & Bulking Factor BF(t)
    axC.axhline(157.1, color="#64748b", linestyle=":", linewidth=1.2, label="Dry Winter Baseline Storage S_dry = 157.1 mm")
    axC.plot(df18["rel_day"], df18["remaining_soil_storage_s_mm"], "-o", color="#dc2626", linewidth=2.2, markersize=4, label="2018 Remaining Soil Storage S(t) (-75% on Day -1)")
    axC.plot(df20["rel_day"], df20["remaining_soil_storage_s_mm"], "-s", color="#ea580c", linewidth=2.0, markersize=4, label="2020 Remaining Soil Storage S(t) (-66% on Day -1)")
    axC.plot(df26["rel_day"], df26["remaining_soil_storage_s_mm"], "--^", color="#0284c7", linewidth=2.0, markersize=4, label="Nov 2026 Remaining Soil Storage S(t)")
    axC.axvline(0, color="#0f172a", linestyle="--", linewidth=1.2)
    axC.set_title("C. Collapse of Catchment Infiltration Storage Capacity S(t)", fontsize=10.5, fontweight="bold")
    axC.set_xlabel("Days Relative to Disaster / Evaluation Date", fontsize=9)
    axC.set_ylabel("Remaining SCS-CN Soil Storage Deficit S(t) [mm]", fontsize=9)
    axC.set_ylim(25, 170)
    axC.grid(True)
    axC.legend(loc="upper right", fontsize=7.8)

    # Panel D: Critical 1-Hour Convective Rainfall Trigger Threshold P_crit(t)
    axD.axhspan(10, 18.0, color="#fecaca", alpha=0.45, label="RED Trigger Zone: Moderate Storm (≤18 mm/hr) Causes Overflow")
    axD.axhspan(18.0, 26.0, color="#fed7aa", alpha=0.45, label="ORANGE Trigger Zone (18–26 mm/hr)")
    axD.axhline(48.7, color="#64748b", linestyle=":", linewidth=1.2, label="Dry Baseline Trigger Threshold = 48.7 mm/hr")
    axD.plot(df18["rel_day"], df18["critical_1hr_rain_threshold_mm"], "-o", color="#dc2626", linewidth=2.2, markersize=4, label="2018 Taquiña P_crit (Drops to 15.6 mm/hr on Day -1)")
    axD.plot(df20["rel_day"], df20["critical_1hr_rain_threshold_mm"], "-s", color="#ea580c", linewidth=2.0, markersize=4, label="2020 Taquiña P_crit (Drops to 20.4 mm/hr on Day -1)")
    axD.plot(df26["rel_day"], df26["critical_1hr_rain_threshold_mm"], "--^", color="#0284c7", linewidth=2.0, markersize=4, label="Nov 2026 Operational P_crit (~29.6 mm/hr)")
    axD.axvline(0, color="#0f172a", linestyle="--", linewidth=1.2)
    axD.set_ylim(12, 53)
    axD.set_title("D. Critical 1-Hour Rainfall Trigger Threshold P_crit(t) for Debris Flow", fontsize=10.5, fontweight="bold")
    axD.set_xlabel("Days Relative to Disaster / Evaluation Date", fontsize=9)
    axD.set_ylabel("Critical 1-Hr Trigger Rainfall P_crit [mm/hr]", fontsize=9)
    axD.grid(True)
    axD.legend(loc="upper right", fontsize=7.6)

    fig.suptitle(
        "Historical Validation Backtest: Multi-Day Antecedent Pre-Conditioning Prior to the 2018 & 2020 Taquiña Mazamorras",
        fontsize=13,
        fontweight="bold",
        color="#0f172a",
        y=0.995,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    out_path = FIG_DIR / "fig3_taquina_backtest_2018_2020_2026.png"
    fig.savefig(out_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path


def generate_fig4_non_tautological_map() -> Path:
    """Figure 4: Spatial Map of Non-Tautological Off-Channel Hazard Mechanisms (>120 m from rivers)."""
    print("[Figures] Generating Figure 4: Non-tautological off-channel hazard discovery map...")
    basins = gpd.read_file(DATA_PROC / "hazard_zones" / "tunari_basins_preconditioned_warning.geojson")
    drenaje = gpd.read_file(DATA_PROC / "gamc" / "drenaje_influencia.geojson")
    distritos = gpd.read_file(DATA_PROC / "gamc" / "limite_distritos.geojson")
    cota2750 = gpd.read_file(DATA_PROC / "gamc" / "cota_2750.geojson")
    chokepoints = gpd.read_file(DATA_PROC / "terrain_physics" / "fan_avulsion_chokepoints.geojson")
    paleo = gpd.read_file(DATA_PROC / "terrain_physics" / "off_channel_paleochannel_corridors.geojson")
    sinks = gpd.read_file(DATA_PROC / "terrain_physics" / "off_channel_pluvial_sinks.geojson")
    manzanas = gpd.read_file(DATA_PROC / "hazard_zones" / "non_obvious_high_risk_manzanas.geojson")
    schools = gpd.read_file(DATA_PROC / "hazard_zones" / "schools_hazard_assessment.geojson")
    health = gpd.read_file(DATA_PROC / "hazard_zones" / "health_centers_hazard_assessment.geojson")

    sch_exposed = schools[schools["hazard_mechanism"].isin(["OFF_CHANNEL_PALEOCHANNEL_BREAKOUT", "OFF_CHANNEL_PLUVIAL_DEPRESSION", "COMPOUND_PALEO_SINK_TRAP"])]
    hlth_exposed = health[health["hazard_mechanism"].isin(["OFF_CHANNEL_PALEOCHANNEL_BREAKOUT", "OFF_CHANNEL_PLUVIAL_DEPRESSION", "COMPOUND_PALEO_SINK_TRAP"])]

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(16.5, 7.8), dpi=220, facecolor="#f8fafc")

    # Left Panel: Cordillera-to-Valley System Overview
    distritos.plot(ax=axL, facecolor="#f1f5f9", edgecolor="#94a3b8", linewidth=0.6)
    basins.plot(
        ax=axL,
        column="geomorphic_susceptibility",
        cmap="YlOrRd",
        alpha=0.55,
        edgecolor="#7c2d12",
        linewidth=0.8,
        legend=True,
        legend_kwds={"label": "Intrinsic Geomorphic Debris-Flow Susceptibility", "shrink": 0.65},
    )
    cota2750.boundary.plot(ax=axL, color="#15803d", linestyle="--", linewidth=1.3)
    drenaje.plot(ax=axL, color="#94a3b8", linewidth=1.0, alpha=0.7)
    paleo.plot(ax=axL, facecolor="#f97316", edgecolor="#c2410c", alpha=0.75, linewidth=0.6)
    sinks.plot(ax=axL, facecolor="#0284c7", edgecolor="#0369a1", alpha=0.75, linewidth=0.6)
    chokepoints.plot(ax=axL, color="#dc2626", markersize=28, marker="^", edgecolor="white", linewidth=0.5, zorder=5)

    axL.set_xlim(-66.29, -66.06)
    axL.set_ylim(-17.49, -17.24)
    axL.set_title(
        "A. Cordillera Tunari Source Catchments & Valley Hazard System\nCoupling Mountain Pre-Conditioning (>2750m) to Alluvial Fan Breakouts",
        fontsize=10.5,
        fontweight="bold",
    )
    axL.set_xlabel("Longitude (°W)", fontsize=9)
    axL.set_ylabel("Latitude (°S)", fontsize=9)
    axL.grid(True)

    # Right Panel: Zoomed Urban Alluvial Fan & Southern Pluvial Bowl (Non-Tautological Zones >120m from rivers)
    distritos.plot(ax=axR, facecolor="#f8fafc", edgecolor="#cbd5e1", linewidth=0.7)
    drenaje.plot(ax=axR, color="#94a3b8", linewidth=1.2, linestyle=":", alpha=0.75)
    paleo.plot(ax=axR, facecolor="#fb923c", edgecolor="#ea580c", alpha=0.65, linewidth=0.7)
    sinks.plot(ax=axR, facecolor="#38bdf8", edgecolor="#0284c7", alpha=0.65, linewidth=0.7)
    manzanas.plot(ax=axR, facecolor="#dc2626", edgecolor="#7f1d1d", alpha=0.85, linewidth=0.3, zorder=4)
    chokepoints.plot(ax=axR, color="#b91c1c", markersize=36, marker="^", edgecolor="white", linewidth=0.6, zorder=6)
    sch_exposed.plot(ax=axR, color="#eab308", markersize=32, marker="s", edgecolor="#0f172a", linewidth=0.6, zorder=7)
    hlth_exposed.plot(ax=axR, color="#ec4899", markersize=42, marker="P", edgecolor="#0f172a", linewidth=0.6, zorder=8)

    axR.set_xlim(-66.23, -66.11)
    axR.set_ylim(-17.46, -17.33)
    axR.set_title(
        "B. Non-Tautological Off-Channel Hazard Zones (>120 m from Mapped Rivers)\n693 High-Risk Manzanas (61,833 People), 32 Schools & 12 Health Centers",
        fontsize=10.5,
        fontweight="bold",
    )
    axR.set_xlabel("Longitude (°W)", fontsize=9)
    axR.set_ylabel("Latitude (°S)", fontsize=9)
    axR.grid(True)

    legend_handles = [
        mpatches.Patch(facecolor="#fb923c", edgecolor="#ea580c", label="Off-Channel Paleochannel Avulsion Corridors (PALEO-*, >120m)"),
        mpatches.Patch(facecolor="#38bdf8", edgecolor="#0284c7", label="Off-Channel Endorheic & Backwater Sinks (SINK-*, >120m)"),
        mpatches.Patch(facecolor="#dc2626", edgecolor="#7f1d1d", label="Top Exposed Off-Channel Urban Blocks (Manzanas)"),
        plt.Line2D([0], [0], marker="^", color="w", markerfacecolor="#b91c1c", markersize=8, label="Alluvial Fan Apex Hydraulic Choke Points (AVN-01..28)"),
        plt.Line2D([0], [0], marker="s", color="w", markerfacecolor="#eab308", markeredgecolor="#0f172a", markersize=7, label="Exposed Off-Channel Schools (32 Unidades Educativas)"),
        plt.Line2D([0], [0], marker="P", color="w", markerfacecolor="#ec4899", markeredgecolor="#0f172a", markersize=8, label="Exposed Off-Channel Health Centers (12 Centros de Salud)"),
        plt.Line2D([0], [0], color="#94a3b8", linestyle=":", linewidth=1.5, label="Mapped Torrenteras (120m Buffer Excluded as Tautological)"),
    ]
    axR.legend(handles=legend_handles, loc="lower right", fontsize=7.6, framealpha=0.94)

    fig.suptitle(
        "Anti-Tautology Discovery: Bare-Earth Paleochannel Breakouts & Endorheic Sinks Outside Known River Buffers",
        fontsize=13,
        fontweight="bold",
        color="#0f172a",
        y=0.99,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out_path = FIG_DIR / "fig4_non_tautological_hazard_map.png"
    fig.savefig(out_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path


def generate_fig5_district_and_thresholds() -> Path:
    """Figure 5: District-Level Non-Obvious Exposure & Basin Critical Trigger Thresholds P_crit."""
    print("[Figures] Generating Figure 5: District off-channel exposure & basin critical rainfall thresholds...")
    haz_sum = json.loads(
        (DATA_PROC / "hazard_zones" / "hazard_synthesis_summary.json").read_text(encoding="utf-8")
    )
    hydro = json.loads(
        (DATA_PROC / "antecedent_forecast" / "basin_antecedent_forecasts.json").read_text(encoding="utf-8")
    )

    districts = [d for d in haz_sum["district_ranking"] if d["novel_off_channel_exposed_population"] > 0]
    d_names = [d["distrito"] for d in districts]
    pop_paleo = np.array([d["avulsion_paleochannel_population"] for d in districts])
    pop_sink = np.array([d["endorheic_sink_population"] for d in districts])
    pop_comp = np.array([d["compound_trap_population"] for d in districts])

    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(16, 6.2), dpi=220, facecolor="#f8fafc")

    # Panel A: Stacked Bar of Non-Tautological Exposed Population by District & Mechanism
    y = np.arange(len(d_names))
    ax0.barh(y, pop_paleo, color="#f97316", edgecolor="#1e293b", height=0.65, label="Off-Channel Paleochannel Avulsion (38,118 people)")
    ax0.barh(y, pop_sink, left=pop_paleo, color="#0284c7", edgecolor="#1e293b", height=0.65, label="Off-Channel Endorheic/Backwater Sink (22,063 people)")
    ax0.barh(
        y,
        pop_comp,
        left=pop_paleo + pop_sink,
        color="#7c3aed",
        edgecolor="#1e293b",
        height=0.65,
        label="Compound Avulsion-to-Sink Trap (1,652 people)",
    )
    for idx_d, d in enumerate(districts):
        tot = d["novel_off_channel_exposed_population"]
        ax0.text(
            tot + 250,
            idx_d,
            f"{tot:,} ({d['novel_off_channel_exposed_manzanas']} manzanas)",
            va="center",
            fontsize=8.2,
            fontweight="bold",
            color="#0f172a",
        )
    ax0.set_yticks(y)
    ax0.set_yticklabels(d_names, fontsize=9, fontweight="bold")
    ax0.invert_yaxis()
    ax0.set_xlim(0, 21500)
    ax0.set_xlabel("Exposed Population Strictly >120 m from Mapped Channels (Inhabitants)", fontsize=9)
    ax0.set_title(
        "A. Non-Obvious Off-Channel Population Exposure by GAMC District\nTotal: 61,833 Inhabitants (693 Manzanas) Missed by River-Buffer Maps",
        fontsize=10.5,
        fontweight="bold",
    )
    ax0.grid(axis="x")
    ax0.legend(loc="lower right", fontsize=8.2)

    # Panel B: Critical 1-Hour Convective Rainfall Trigger Threshold P_crit across Top 12 Steep Tunari Catchments
    cur_list = hydro["scenarios"]["current_2026_11_15"]
    dry_map = {b["basin_id"]: b for b in hydro["scenarios"]["benchmark_dry_2026_08_03"]}
    h18_map = {b["basin_id"]: b for b in hydro["scenarios"]["historical_2018_02_06_taquina"]}

    # Sort by 2018 pre-conditioned P_crit (most sensitive catchments first)
    steep_basins = [b for b in cur_list if "Intercuencas" not in b["basin_name"]]
    steep_basins = sorted(steep_basins, key=lambda b: h18_map[b["basin_id"]]["critical_1hr_rain_threshold_mm"])[:12]

    b_labels = [b["basin_name"] for b in steep_basins]
    yb = np.arange(len(b_labels))
    h = 0.26

    p_dry = [dry_map[b["basin_id"]]["critical_1hr_rain_threshold_mm"] for b in steep_basins]
    p_now = [b["critical_1hr_rain_threshold_mm"] for b in steep_basins]
    p_18 = [h18_map[b["basin_id"]]["critical_1hr_rain_threshold_mm"] for b in steep_basins]

    ax1.barh(yb - h, p_dry, height=h, color="#94a3b8", edgecolor="#1e293b", label="Dry Winter Baseline (Aug 2026)")
    ax1.barh(yb, p_now, height=h, color="#eab308", edgecolor="#1e293b", label="Current Pre-Wet Transition (Nov 15, 2026)")
    ax1.barh(yb + h, p_18, height=h, color="#dc2626", edgecolor="#1e293b", label="Pre-Conditioned Disaster Eve (Feb 2018)")

    ax1.axvline(20.0, color="#dc2626", linestyle="--", linewidth=1.1, label="Moderate 1-Hr Convective Storm (20 mm/hr)")
    ax1.set_yticks(yb)
    ax1.set_yticklabels(b_labels, fontsize=8.8, fontweight="bold")
    ax1.invert_yaxis()
    ax1.set_xlabel("Critical 1-Hr Rainfall Trigger Intensity P_crit [mm/hr]", fontsize=9)
    ax1.set_title(
        "B. Dynamic Shift in Critical Trigger Threshold P_crit(t)\nHow Antecedent Wetting Turns Moderate Storms into Catastrophes",
        fontsize=10.5,
        fontweight="bold",
    )
    ax1.grid(axis="x")
    ax1.legend(loc="lower right", fontsize=8)

    fig.suptitle(
        "Operational Decision Support: Off-Channel Population Exposure & Dynamic Catchment Trigger Thresholds",
        fontsize=13,
        fontweight="bold",
        color="#0f172a",
        y=0.99,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out_path = FIG_DIR / "fig5_district_exposure_and_critical_thresholds.png"
    fig.savefig(out_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    f1 = generate_fig1_dsm_vs_fabdem()
    f2 = generate_fig2_sar_domains()
    f3 = generate_fig3_taquina_backtest()
    f4 = generate_fig4_non_tautological_map()
    f5 = generate_fig5_district_and_thresholds()
    print("[Figures] All 5 publication-grade figures generated:")
    for p in (f1, f2, f3, f4, f5):
        print(f"  -> {p} ({p.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
