"""
Interactive Scientific WebGIS & Pre-Conditioning Early Warning Dashboard Builder
================================================================================
Generates the self-contained interactive WebGIS application at `docs/index.html`
embedding real processed GeoJSON layers, multi-scenario antecedent hydrological
states, historical 2018/2020 Taquiña backtest trajectories, live GAMC WMS tile
layers, and an interactive SCS-CN + Debris-Bulking storm trigger simulator.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import geopandas as gpd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PROC = PROJECT_ROOT / "data" / "processed"
DOCS_DIR = PROJECT_ROOT / "docs"


def gdf_to_clean_geojson_dict(gdf: gpd.GeoDataFrame) -> dict[str, Any]:
    """Convert GeoDataFrame to JSON-serializable GeoJSON dict, converting any Timestamps to strings."""
    gdf_clean = gdf.copy()
    for col in gdf_clean.columns:
        if col == "geometry":
            continue
        if str(gdf_clean[col].dtype).startswith("datetime") or str(gdf_clean[col].dtype) == "object":
            gdf_clean[col] = gdf_clean[col].apply(
                lambda v: v.isoformat() if hasattr(v, "isoformat") else v
            )
    return json.loads(gdf_clean.to_json())


def simplify_geojson_for_web(path: Path, tol: float = 0.00012) -> dict[str, Any]:
    """Load a GeoJSON, optionally simplify geometries for fast browser rendering, and return dict."""
    gdf = gpd.read_file(path)
    if tol > 0 and len(gdf) > 0:
        geom_type = gdf.geometry.iloc[0].geom_type
        if "Polygon" in geom_type or "LineString" in geom_type:
            gdf = gdf.copy()
            gdf["geometry"] = gdf.geometry.simplify(tol, preserve_topology=True)
    return gdf_to_clean_geojson_dict(gdf)


def build_webgis_dashboard() -> Path:
    print("[Dashboard Builder] Loading geospatial layers and physical model outputs...")
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    # Load JSON summaries
    terrain_sum = json.loads(
        (DATA_PROC / "terrain_physics" / "terrain_physics_summary.json").read_text(encoding="utf-8")
    )
    sar_sum = json.loads(
        (DATA_PROC / "sar_analysis" / "sar_dielectric_summary.json").read_text(encoding="utf-8")
    )
    hydro_data = json.loads(
        (DATA_PROC / "antecedent_forecast" / "basin_antecedent_forecasts.json").read_text(encoding="utf-8")
    )
    hazard_sum = json.loads(
        (DATA_PROC / "hazard_zones" / "hazard_synthesis_summary.json").read_text(encoding="utf-8")
    )
    val_report = json.loads(
        (DATA_PROC / "validation_audit_report.json").read_text(encoding="utf-8")
    )

    # Load GeoJSON layers
    basins_geojson = simplify_geojson_for_web(
        DATA_PROC / "hazard_zones" / "tunari_basins_preconditioned_warning.geojson", tol=0.00018
    )
    chokepoints_geojson = simplify_geojson_for_web(
        DATA_PROC / "terrain_physics" / "fan_avulsion_chokepoints.geojson", tol=0.0
    )
    paleo_geojson = simplify_geojson_for_web(
        DATA_PROC / "terrain_physics" / "off_channel_paleochannel_corridors.geojson", tol=0.00012
    )
    sinks_geojson = simplify_geojson_for_web(
        DATA_PROC / "terrain_physics" / "off_channel_pluvial_sinks.geojson", tol=0.00012
    )
    manzanas_geojson = simplify_geojson_for_web(
        DATA_PROC / "hazard_zones" / "non_obvious_high_risk_manzanas.geojson", tol=0.00006
    )
    drenaje_geojson = simplify_geojson_for_web(
        DATA_PROC / "gamc" / "drenaje_influencia.geojson", tol=0.00012
    )
    cota2750_geojson = simplify_geojson_for_web(
        DATA_PROC / "gamc" / "cota_2750.geojson", tol=0.00015
    )
    distritos_geojson = simplify_geojson_for_web(
        DATA_PROC / "gamc" / "limite_distritos.geojson", tol=0.00020
    )

    # Filter schools & health centers to off-channel exposed ones (plus keep counts)
    schools_gdf = gpd.read_file(DATA_PROC / "hazard_zones" / "schools_hazard_assessment.geojson")
    schools_exposed = schools_gdf[
        schools_gdf["hazard_mechanism"].isin(
            [
                "OFF_CHANNEL_PALEOCHANNEL_BREAKOUT",
                "OFF_CHANNEL_PLUVIAL_DEPRESSION",
                "COMPOUND_PALEO_SINK_TRAP",
            ]
        )
    ]
    schools_geojson = gdf_to_clean_geojson_dict(schools_exposed)

    health_gdf = gpd.read_file(DATA_PROC / "hazard_zones" / "health_centers_hazard_assessment.geojson")
    health_exposed = health_gdf[
        health_gdf["hazard_mechanism"].isin(
            [
                "OFF_CHANNEL_PALEOCHANNEL_BREAKOUT",
                "OFF_CHANNEL_PLUVIAL_DEPRESSION",
                "COMPOUND_PALEO_SINK_TRAP",
            ]
        )
    ]
    health_geojson = gdf_to_clean_geojson_dict(health_exposed)

    emerg_geojson = simplify_geojson_for_web(
        DATA_PROC / "hazard_zones" / "emergencias_physical_context.geojson", tol=0.0
    )

    # Bundle compact payload for client-side interactive physics & rendering
    app_bundle = {
        "terrain_summary": terrain_sum,
        "sar_summary": sar_sum,
        "hydro_scenarios": hydro_data["scenarios"],
        "taquina_trajectories": hydro_data["taquina_daily_trajectories"],
        "hazard_summary": hazard_sum,
        "validation_report": val_report,
        "layers": {
            "basins": basins_geojson,
            "chokepoints": chokepoints_geojson,
            "paleochannels": paleo_geojson,
            "sinks": sinks_geojson,
            "manzanas": manzanas_geojson,
            "drenaje": drenaje_geojson,
            "cota2750": cota2750_geojson,
            "distritos": distritos_geojson,
            "schools_exposed": schools_geojson,
            "health_exposed": health_geojson,
            "emergencias": emerg_geojson,
        },
    }

    bundle_json_str = json.dumps(app_bundle, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Cochabamba Flood & Mazamorra Pre-Conditioning Early Warning System</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <style>
    :root {{
      --bg-dark: #0b1120;
      --bg-panel: #111827;
      --bg-card: #1e293b;
      --bg-card-hover: #26354d;
      --border: #334155;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --accent-blue: #38bdf8;
      --accent-orange: #fb923c;
      --accent-red: #f87171;
      --accent-green: #4ade80;
      --accent-yellow: #facc15;
      --accent-purple: #c084fc;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg-dark);
      color: var(--text-main);
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}
    /* Top Header */
    header {{
      background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%);
      border-bottom: 1px solid var(--border);
      padding: 10px 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      z-index: 1000;
    }}
    .brand-title {{
      display: flex;
      flex-direction: column;
    }}
    .brand-title h1 {{
      font-size: 1.08rem;
      font-weight: 700;
      letter-spacing: 0.2px;
      color: #f8fafc;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .badge-rigor {{
      background: rgba(56, 189, 248, 0.15);
      border: 1px solid var(--accent-blue);
      color: var(--accent-blue);
      font-size: 0.7rem;
      padding: 2px 8px;
      border-radius: 999px;
      font-weight: 600;
      text-transform: uppercase;
    }}
    .brand-subtitle {{
      font-size: 0.76rem;
      color: var(--text-muted);
      margin-top: 2px;
    }}
    .nav-tabs {{
      display: flex;
      gap: 6px;
    }}
    .nav-btn {{
      background: var(--bg-card);
      color: var(--text-muted);
      border: 1px solid var(--border);
      padding: 7px 13px;
      border-radius: 6px;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
    }}
    .nav-btn:hover {{
      color: var(--text-main);
      background: var(--bg-card-hover);
    }}
    .nav-btn.active {{
      background: #0284c7;
      color: #ffffff;
      border-color: #38bdf8;
    }}

    /* Main Workspace Layout */
    .workspace {{
      flex: 1;
      display: flex;
      overflow: hidden;
      position: relative;
    }}
    .tab-pane {{
      display: none;
      width: 100%;
      height: 100%;
      overflow-y: auto;
    }}
    .tab-pane.active {{
      display: flex;
    }}

    /* Tab 1: Split Sidebar + Map + Inspector */
    .sidebar-left {{
      width: 370px;
      background: var(--bg-panel);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      overflow-y: auto;
      padding: 14px;
      gap: 14px;
    }}
    .map-container {{
      flex: 1;
      position: relative;
      display: flex;
      flex-direction: column;
    }}
    #map {{
      flex: 1;
      width: 100%;
      background: #0f172a;
    }}
    .sidebar-right {{
      width: 390px;
      background: var(--bg-panel);
      border-left: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      overflow-y: auto;
      padding: 14px;
      gap: 14px;
    }}

    /* Cards & Controls */
    .card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
    }}
    .card-title {{
      font-size: 0.82rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.4px;
      color: var(--accent-blue);
      margin-bottom: 8px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .control-label {{
      font-size: 0.78rem;
      color: var(--text-muted);
      margin-bottom: 5px;
      display: block;
    }}
    select.scenario-select {{
      width: 100%;
      background: #0f172a;
      color: var(--text-main);
      border: 1px solid var(--border);
      padding: 8px 10px;
      border-radius: 6px;
      font-size: 0.82rem;
      font-weight: 600;
      margin-bottom: 10px;
    }}
    .slider-row {{
      display: flex;
      flex-direction: column;
      gap: 5px;
      margin-top: 6px;
    }}
    .slider-header {{
      display: flex;
      justify-content: space-between;
      font-size: 0.8rem;
    }}
    .slider-val {{
      font-weight: 700;
      color: var(--accent-yellow);
    }}
    input[type="range"] {{
      width: 100%;
      accent-color: #38bdf8;
      cursor: pointer;
    }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }}
    .kpi-box {{
      background: #0f172a;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 8px 10px;
    }}
    .kpi-num {{
      font-size: 1.15rem;
      font-weight: 800;
      color: var(--text-main);
    }}
    .kpi-label {{
      font-size: 0.7rem;
      color: var(--text-muted);
      margin-top: 2px;
    }}

    /* Layer Toggles */
    .layer-item {{
      display: flex;
      align-items: flex-start;
      gap: 8px;
      padding: 5px 0;
      border-bottom: 1px solid rgba(51, 65, 85, 0.45);
      font-size: 0.79rem;
    }}
    .layer-item:last-child {{ border-bottom: none; }}
    .layer-item input {{ margin-top: 3px; cursor: pointer; }}
    .layer-swatch {{
      width: 12px;
      height: 12px;
      border-radius: 3px;
      margin-top: 3px;
      flex-shrink: 0;
    }}
    .layer-desc {{
      font-size: 0.7rem;
      color: var(--text-muted);
      display: block;
    }}

    /* Inspector Dossier */
    .dossier-header {{
      font-size: 0.95rem;
      font-weight: 700;
      color: #ffffff;
      margin-bottom: 4px;
    }}
    .tier-pill {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 0.72rem;
      font-weight: 700;
      margin-bottom: 8px;
    }}
    .tier-RED_CRITICAL_PRECONDITIONED {{ background: rgba(239, 68, 68, 0.22); color: #fca5a5; border: 1px solid #ef4444; }}
    .tier-ORANGE_HIGH_SUSCEPTIBILITY {{ background: rgba(249, 115, 22, 0.22); color: #fdba74; border: 1px solid #f97316; }}
    .tier-YELLOW_MODERATE_WATCH {{ background: rgba(234, 179, 8, 0.22); color: #fde047; border: 1px solid #eab308; }}
    .tier-GREEN_HIGH_STORAGE_BUFFER {{ background: rgba(34, 197, 94, 0.22); color: #86efac; border: 1px solid #22c55e; }}

    .metric-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.78rem;
      margin-top: 6px;
    }}
    .metric-table td {{
      padding: 5px 4px;
      border-bottom: 1px solid rgba(51, 65, 85, 0.5);
    }}
    .metric-table td:last-child {{
      text-align: right;
      font-weight: 600;
      color: #e2e8f0;
    }}

    /* Full-page Content Tabs */
    .content-page {{
      padding: 20px 28px;
      max-width: 1480px;
      margin: 0 auto;
      width: 100%;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }}
    .grid-2col {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
    }}
    .data-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.8rem;
    }}
    .data-table th, .data-table td {{
      padding: 8px 10px;
      border-bottom: 1px solid var(--border);
      text-align: left;
    }}
    .data-table th {{
      background: #0f172a;
      color: var(--accent-blue);
      font-weight: 700;
      position: sticky;
      top: 0;
    }}
    .fig-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 14px;
    }}
    .fig-card img {{
      width: 100%;
      border-radius: 6px;
      border: 1px solid var(--border);
      margin-top: 8px;
    }}
    .epist-callout {{
      background: rgba(56, 189, 248, 0.08);
      border-left: 4px solid var(--accent-blue);
      padding: 10px 12px;
      font-size: 0.79rem;
      line-height: 1.45;
      color: #e2e8f0;
      border-radius: 0 6px 6px 0;
    }}
  </style>
</head>
<body>

<header>
  <div class="brand-title">
    <h1>
      <span>COCHABAMBA HYDRO-GEOMORPHIC PRE-CONDITIONING & AVULSION EARLY WARNING SYSTEM</span>
      <span class="badge-rigor">FABDEM V1-2 + Dual-Orbit SAR + GAMC</span>
    </h1>
    <div class="brand-subtitle">
      Physically Grounded Multi-Day Antecedent Susceptibility & Non-Tautological Off-Channel Hazard Discovery (&gt;120 m from Mapped Rivers)
    </div>
  </div>
  <div class="nav-tabs">
    <button class="nav-btn active" onclick="switchTab('tab-map', this)">1. Interactive WebGIS & Simulator</button>
    <button class="nav-btn" onclick="switchTab('tab-backtest', this)">2. 2018 & 2020 Taquiña Backtest</button>
    <button class="nav-btn" onclick="switchTab('tab-epistemology', this)">3. Epistemological & SAR/DEM Proofs</button>
    <button class="nav-btn" onclick="switchTab('tab-exposure', this)">4. District & Infrastructure Priority</button>
  </div>
</header>

<div class="workspace">
  <!-- TAB 1: INTERACTIVE WEBGIS & SIMULATOR -->
  <div id="tab-map" class="tab-pane active">
    <aside class="sidebar-left">
      <div class="card">
        <div class="card-title">
          <span>Antecedent State & Storm Simulator</span>
        </div>
        <label class="control-label" for="scenarioSelect">1. Select Multi-Day Antecedent State (Previous 14 Days):</label>
        <select id="scenarioSelect" class="scenario-select" onchange="onScenarioChange()">
          <option value="current_2026_11_15">Operational Today: 15 Nov 2026 (Pre-Wet Transition)</option>
          <option value="forecast_2026_11_21">7-Day Forecast Peak: 21 Nov 2026 (Wetting Progression)</option>
          <option value="historical_2018_02_06_taquina">Historical Backtest: 6 Feb 2018 Taquiña Mazamorra</option>
          <option value="historical_2020_02_21_taquina">Historical Backtest: 21 Feb 2020 Taquiña Mazamorra</option>
          <option value="benchmark_wet_2026_02_21">Peak Wet Season SAR Benchmark: 21 Feb 2026</option>
          <option value="benchmark_dry_2026_08_03">Bone-Dry Winter Baseline: 3 Aug 2026</option>
        </select>

        <div class="slider-row">
          <div class="slider-header">
            <span class="control-label">2. Hypothetical 1-Hr Convective Storm Trigger:</span>
            <span id="stormValLabel" class="slider-val">22 mm/hr</span>
          </div>
          <input type="range" id="stormSlider" min="0" max="55" step="1" value="22" oninput="onStormSliderChange()" />
          <div style="display:flex; justify-content:space-between; font-size:0.68rem; color:var(--text-muted);">
            <span>0 mm/hr (No Rain)</span>
            <span>20 mm/hr (Moderate)</span>
            <span>40+ mm/hr (Extreme)</span>
          </div>
        </div>

        <div class="kpi-grid" style="margin-top:12px;">
          <div class="kpi-box">
            <div id="kpiPrecondBasins" class="kpi-num" style="color:var(--accent-orange);">0 / 23</div>
            <div class="kpi-label">Basins in Orange/Red Antecedent State</div>
          </div>
          <div class="kpi-box">
            <div id="kpiTriggeredBasins" class="kpi-num" style="color:var(--accent-red);">0 / 23</div>
            <div class="kpi-label">Basins Exceeding P_crit at Selected Storm</div>
          </div>
          <div class="kpi-box">
            <div class="kpi-num" style="color:var(--accent-blue);">61,833</div>
            <div class="kpi-label">Off-Channel Residents (&gt;120m from Rivers)</div>
          </div>
          <div class="kpi-box">
            <div class="kpi-num" style="color:var(--accent-purple);">693</div>
            <div class="kpi-label">Non-Obvious High-Risk Manzanas</div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-title"><span>Physical & Non-Tautological Layers</span></div>
        <div class="layer-item">
          <input type="checkbox" id="chkPaleo" checked onchange="toggleMapLayer('paleochannels', this.checked)" />
          <span class="layer-swatch" style="background:#f97316; border:1px solid #fff;"></span>
          <div>
            <strong>Off-Channel Paleochannel Corridors (PALEO-*)</strong>
            <span class="layer-desc">45 bare-earth FABDEM breakout paths strictly &gt;120m from rivers (38,118 people exposed)</span>
          </div>
        </div>
        <div class="layer-item">
          <input type="checkbox" id="chkChoke" checked onchange="toggleMapLayer('chokepoints', this.checked)" />
          <span class="layer-swatch" style="background:#dc2626; border-radius:50%;"></span>
          <div>
            <strong>Alluvial Fan Apex Choke Points (AVN-01..28)</strong>
            <span class="layer-desc">28 sharp channel bends + slope drops + DSM building constriction (&gt;3m)</span>
          </div>
        </div>
        <div class="layer-item">
          <input type="checkbox" id="chkSinks" checked onchange="toggleMapLayer('sinks', this.checked)" />
          <span class="layer-swatch" style="background:#0284c7; border:1px solid #38bdf8;"></span>
          <div>
            <strong>Off-Channel Endorheic & Backwater Sinks (SINK-*)</strong>
            <span class="layer-desc">45 topographic &amp; Rocha-backwater depressions &gt;120m from rivers (22,063 people)</span>
          </div>
        </div>
        <div class="layer-item">
          <input type="checkbox" id="chkManzanas" checked onchange="toggleMapLayer('manzanas', this.checked)" />
          <span class="layer-swatch" style="background:#ef4444;"></span>
          <div>
            <strong>Top Non-Obvious High-Risk Manzanas</strong>
            <span class="layer-desc">Urban blocks outside the 120m river buffer intersecting PALEO-* or SINK-*</span>
          </div>
        </div>
        <div class="layer-item">
          <input type="checkbox" id="chkInfra" checked onchange="toggleMapLayer('infra', this.checked)" />
          <span class="layer-swatch" style="background:#facc15;"></span>
          <div>
            <strong>Exposed Off-Channel Schools (32) &amp; Health Centers (12)</strong>
            <span class="layer-desc">Critical GAMC facilities in off-channel breakout or sink zones</span>
          </div>
        </div>
        <div class="layer-item">
          <input type="checkbox" id="chkBasins" checked onchange="toggleMapLayer('basins', this.checked)" />
          <span class="layer-swatch" style="background:#eab308; opacity:0.65;"></span>
          <div>
            <strong>23 Tunari Source Catchments (Cuencas de Influencia)</strong>
            <span class="layer-desc">Colored by antecedent pre-conditioning alert tier (click basin to inspect)</span>
          </div>
        </div>
        <div class="layer-item">
          <input type="checkbox" id="chkCota" checked onchange="toggleMapLayer('cota2750', this.checked)" />
          <span class="layer-swatch" style="background:#22c55e;"></span>
          <div>
            <strong>Cota 2750 m (SAR Dielectric Validity Boundary)</strong>
            <span class="layer-desc">Above 2750m: Valid C/L-band soil moisture; Below: Urban corner clutter masked</span>
          </div>
        </div>
        <div class="layer-item">
          <input type="checkbox" id="chkDrenaje" checked onchange="toggleMapLayer('drenaje', this.checked)" />
          <span class="layer-swatch" style="background:#64748b;"></span>
          <div>
            <strong>Mapped Torrenteras &amp; Río Rocha (120m Buffer Excluded)</strong>
            <span class="layer-desc">47 GAMC channels (trivial proximity excluded to prevent tautology)</span>
          </div>
        </div>
        <div class="layer-item">
          <input type="checkbox" id="chkEmerg" onchange="toggleMapLayer('emergencias', this.checked)" />
          <span class="layer-swatch" style="background:#c084fc; border-radius:50%;"></span>
          <div>
            <strong>GAMC Emergencias Ground-Truth (97 Reports)</strong>
            <span class="layer-desc">Classified into channel filling/obstruction, drainage overflow &amp; treefalls</span>
          </div>
        </div>
        <div class="layer-item">
          <input type="checkbox" id="chkGamcWms" onchange="toggleGamcLiveWms(this.checked)" />
          <span class="layer-swatch" style="background:#14b8a6;"></span>
          <div>
            <strong>Live GAMC GeoServer WMS Overlay (serviciosgamc)</strong>
            <span class="layer-desc">Streams live municipal WMS tiles directly from GAMC API</span>
          </div>
        </div>
      </div>

      <div class="epist-callout">
        <strong>Why Tautological River Buffers Are Excluded:</strong><br/>
        Flagging areas within 120 m of mapped torrenteras (5,155 blocks / 191,307 people) states the obvious. This system strictly excludes the ≤120 m corridor and reveals <strong>693 off-channel urban blocks (61,833 people)</strong> threatened by bare-earth paleochannel avulsions and backwater-locked topographic bowls up to 1.4 km away from mapped rivers.
      </div>
    </aside>

    <main class="map-container">
      <div id="map"></div>
    </main>

    <aside class="sidebar-right">
      <div class="card" id="inspectorCard">
        <div class="card-title">
          <span>Physical Mechanism & Basin Dossier</span>
          <span style="font-size:0.68rem; color:var(--text-muted);">Click any feature</span>
        </div>
        <div id="inspectorContent">
          <!-- Populated dynamically on load with C. Taquiña -->
        </div>
      </div>

      <div class="card">
        <div class="card-title"><span>23 Tunari Catchments — Dynamic P_crit Ranking</span></div>
        <div style="max-height: 360px; overflow-y: auto;">
          <table class="metric-table" id="basinRankingTable">
            <thead>
              <tr style="color:var(--text-muted); font-size:0.72rem; border-bottom:1px solid var(--border);">
                <th style="text-align:left; padding:4px;">Catchment</th>
                <th style="text-align:right; padding:4px;">W_ant</th>
                <th style="text-align:right; padding:4px;">BF(t)</th>
                <th style="text-align:right; padding:4px;">P_crit</th>
                <th style="text-align:right; padding:4px;">Q_p/Q_cap</th>
              </tr>
            </thead>
            <tbody id="basinRankingBody"></tbody>
          </table>
        </div>
      </div>
    </aside>
  </div>

  <!-- TAB 2: HISTORICAL BACKTEST (2018 & 2020 TAQUIÑA MAZAMORRAS) -->
  <div id="tab-backtest" class="tab-pane">
    <div class="content-page">
      <div class="card">
        <div class="card-title">
          <span>Historical Validation Backtest: Feb 6, 2018 &amp; Feb 21, 2020 Taquiña Mazamorra Catastrophes</span>
        </div>
        <p style="font-size:0.86rem; color:#cbd5e1; line-height:1.5;">
          Because satellite precipitation (GPM IMERG ~10 km, ERA5-Land ~9 km) cannot resolve micro-watershed convective cells (median Tunari basin area = <strong>10.5 km²</strong>, median Kirpich time of concentration <strong>T_c = 36.1 min</strong>), our system uses previous days' cumulative wetting, root-zone soil moisture, and Cota-2750 SAR dielectric saturation to track <strong>multi-day catchment pre-conditioning</strong>. Both historical Taquiña disasters were preceded by <strong>9 to 17 days of continuous RED_CRITICAL_PRECONDITIONED warnings</strong>, where remaining soil storage collapsed by <strong>64%–75%</strong> and the 1-hour rainfall required to trigger a bulked debris flow dropped from <strong>48.7 mm/hr (dry baseline) down to 15.6–20.4 mm/hr</strong>.
        </p>
      </div>

      <div class="grid-2col">
        <div class="card">
          <div class="card-title"><span>Interactive Trajectory: Antecedent Wetness W_ant(t) &amp; Storage S(t)</span></div>
          <canvas id="chartBacktestWetness" height="210"></canvas>
        </div>
        <div class="card">
          <div class="card-title"><span>Interactive Trajectory: Critical 1-Hr Trigger Threshold P_crit(t) [mm/hr]</span></div>
          <canvas id="chartBacktestPcrit" height="210"></canvas>
        </div>
      </div>

      <div class="fig-card">
        <div class="card-title"><span>Publication Diagnostic Figure 3: 2018 &amp; 2020 Taquiña Pre-Conditioning Backtest</span></div>
        <img src="figures/fig3_taquina_backtest_2018_2020_2026.png" alt="Taquiña Historical Backtest" />
      </div>
    </div>
  </div>

  <!-- TAB 3: EPISTEMOLOGICAL & PHYSICAL RIGOR PROOFS -->
  <div id="tab-epistemology" class="tab-pane">
    <div class="content-page">
      <div class="card">
        <div class="card-title"><span>Epistemological &amp; Sensor-Physics Audit: Matching Every Dataset to Its True Physical Scale</span></div>
        <table class="data-table">
          <thead>
            <tr>
              <th>Physical Domain / Sensor</th>
              <th>Naive Misuse (Rejected)</th>
              <th>Scientifically Rigorous Formulation (Implemented)</th>
              <th>Quantitative Empirical Proof in Cochabamba</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>1. Bare-Earth Topography</strong><br/>FABDEM V1-2 (30m DTM) vs. Copernicus GLO-30 DSM</td>
              <td>Running surface flow routing on standard DSMs (SRTM / Copernicus GLO-30) or claiming sub-meter street-curb hydraulics from 30m grids.</td>
              <td>Use <strong>FABDEM V1-2 bare-earth DTM</strong> for paleochannel MFD routing &amp; endorheic sink extraction; use <code>ΔZ = DSM − FABDEM</code> strictly to quantify building/tree constriction at channel bends.</td>
              <td>Copernicus DSM has a <strong>+2.45 m mean (+8.24 m P90)</strong> positive bias along Cochabamba's 90m channel corridors, creating <strong>9,328 false dam pixels</strong> and <strong>476.8 ha of artificial street-wall sinks</strong> vs. <strong>632.2 ha of true bare-earth depressions</strong>.</td>
            </tr>
            <tr>
              <td><strong>2. Synthetic Aperture Radar</strong><br/>Sentinel-1 C-Band (5.6cm) + ALOS-2/NISAR L-Band (23.6cm)</td>
              <td>Using C-band or L-band SAR inside urban Cochabamba to detect street flooding or urban soil moisture, or using a single orbit on steep slopes.</td>
              <td>Strictly mask out <code>Limite Urbano</code> &amp; corner reflectors (<code>γ° &gt; -3.5 dB</code>). Restrict SAR dielectric retrieval to non-urban Upper Tunari catchments (<strong>above Cota 2750 m</strong>) using <strong>Dual-Orbit (Asc 003 + Desc 156)</strong> aspect-weighted fusion.</td>
              <td>Urban C-band VV is pinned at <strong>-4.73 dB (dry) vs -4.91 dB (wet)</strong> (<strong>-0.19 dB clutter noise</strong>, 52.1% double-bounce contaminated). Above Cota 2750m, C-band VV rises by <strong>+1.06 to +1.94 dB mean (+6.57 dB P90 in colluvial hollows)</strong>, and dual-orbit fusion cuts layover loss from <strong>11.0% to 1.5%</strong>.</td>
            </tr>
            <tr>
              <td><strong>3. Mesoscale Precipitation</strong><br/>GPM IMERG / ERA5-Land (~9–11 km) &amp; GloFAS</td>
              <td>Claiming immediate street-level flash-flood nowcasting from 10 km satellite rainfall pixels with multi-hour latency.</td>
              <td>Drive a <strong>multi-day Antecedent Pre-Conditioning Model</strong> (14-day API, root-zone soil moisture, dynamic SCS-CN storage deficit <code>S(t)</code>, sediment bulking <code>BF(t)</code>, and critical 1-hr trigger rainfall <code>P_crit(t)</code>).</td>
              <td><strong>22 of 23 Tunari watersheds</strong> (median <strong>10.5 km²</strong>) are smaller than a single ~100 km² satellite pixel, and <strong>16 of 23</strong> have Kirpich concentration times <strong>T_c &lt; 60 min</strong> (median 36.1 min). Pre-conditioning flagged both 2018 &amp; 2020 disasters <strong>9–17 days in advance</strong>.</td>
            </tr>
            <tr>
              <td><strong>4. Anti-Tautology Hazard Discovery</strong><br/>Off-Channel Avulsions &amp; Sinks</td>
              <td>Drawing a buffer around mapped rivers and declaring "there is flood risk near torrenteras."</td>
              <td>Explicitly exclude the trivial <strong>≤120 m channel buffer</strong> (5,155 blocks) and model off-channel <strong>alluvial fan apex choke points (AVN-*)</strong>, <strong>paleochannel breakout swales (PALEO-*)</strong>, and <strong>endorheic/backwater bowls (SINK-*)</strong>.</td>
              <td>Identifies <strong>693 non-obvious off-channel Manzanas (61,833 inhabitants, 24,008 dwellings)</strong>, <strong>32 schools</strong>, and <strong>12 health centers</strong> at mean distances of <strong>398 m to 1,412 m</strong> away from the nearest mapped river.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="grid-2col">
        <div class="fig-card">
          <div class="card-title"><span>Figure 1: Bare-Earth FABDEM V1-2 vs. Copernicus GLO-30 DSM Proof</span></div>
          <img src="figures/fig1_dsm_vs_fabdem_proof.png" alt="DSM vs FABDEM Proof" />
        </div>
        <div class="fig-card">
          <div class="card-title"><span>Figure 2: SAR Urban Clutter Masking &amp; Cota-2750 Dual-Orbit Wetting</span></div>
          <img src="figures/fig2_sar_epistemological_domains.png" alt="SAR Epistemological Domains" />
        </div>
      </div>

      <div class="fig-card">
        <div class="card-title"><span>Figure 4: Spatial Discovery of Non-Tautological Off-Channel Hazard Zones (&gt;120 m from Rivers)</span></div>
        <img src="figures/fig4_non_tautological_hazard_map.png" alt="Non-Tautological Hazard Map" />
      </div>
    </div>
  </div>

  <!-- TAB 4: DISTRICT & CRITICAL INFRASTRUCTURE EXPOSURE -->
  <div id="tab-exposure" class="tab-pane">
    <div class="content-page">
      <div class="fig-card">
        <div class="card-title"><span>Figure 5: District-Level Off-Channel Exposure &amp; Dynamic Catchment Trigger Thresholds</span></div>
        <img src="figures/fig5_district_exposure_and_critical_thresholds.png" alt="District Exposure and Thresholds" />
      </div>

      <div class="grid-2col">
        <div class="card">
          <div class="card-title"><span>GAMC District Ranking — Non-Obvious Off-Channel Exposure (&gt;120 m from Rivers)</span></div>
          <table class="data-table" id="districtTable">
            <thead>
              <tr>
                <th>District</th>
                <th>Off-Channel Manzanas</th>
                <th>Off-Channel Pop.</th>
                <th>Paleochannel Avulsion Pop.</th>
                <th>Endorheic Sink Pop.</th>
                <th>Compound Trap Pop.</th>
                <th>Excluded ≤120m River Pop.</th>
              </tr>
            </thead>
            <tbody id="districtTableBody"></tbody>
          </table>
        </div>

        <div class="card">
          <div class="card-title"><span>GAMC Ground-Truth Audit: Emergencias Obstruction Incidents &amp; Red Mónica</span></div>
          <div class="epist-callout" style="margin-bottom:12px;">
            <strong>GAMC Data Audit Discovery:</strong><br/>
            1. <code>red_monica.zip</code> was audited and verified to contain atmospheric <strong>PM10 air quality</strong> records (<code>estacion, pm10, fecha_medicion</code>), <em>not</em> meteorological rain gauges; it is therefore excluded from hydrological forcing.<br/>
            2. <code>emergencias.kml</code> (97 UGR records) is dominated by wet-season treefalls (87), but contains critical ground-truth reports of <strong>anthropogenic filling of drainage canals with dirt/debris, clogged gutters, and avenue flooding</strong> that directly corroborate our hydraulic choke and paleochannel breakout mechanisms.
          </div>
          <div style="max-height:360px; overflow-y:auto;">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Emergency Type</th>
                  <th>Field Report Description</th>
                  <th>Dist. to Channel</th>
                  <th>Dist. to PALEO / SINK</th>
                </tr>
              </thead>
              <tbody id="emergTableBody"></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
  const APP_DATA = {bundle_json_str};

  let map;
  let layerGroups = {{}};
  let gamcWmsLayer = null;
  let activeScenarioKey = "current_2026_11_15";
  let selectedBasinId = 14; // Default to C. Taquiña (basin_id = 14)

  function switchTab(tabId, btnEl) {{
    document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
    btnEl.classList.add('active');
    if (tabId === 'tab-map' && map) {{
      setTimeout(() => map.invalidateSize(), 100);
    }}
  }}

  function getTierColor(tier) {{
    switch (tier) {{
      case "RED_CRITICAL_PRECONDITIONED": return "#ef4444";
      case "ORANGE_HIGH_SUSCEPTIBILITY": return "#f97316";
      case "YELLOW_MODERATE_WATCH": return "#eab308";
      default: return "#22c55e";
    }}
  }}

  function simulateStormForBasin(b, stormMmHr) {{
    const ia = b.initial_abstraction_ia_mm;
    const s = b.remaining_soil_storage_s_mm;
    const bf = b.debris_bulking_factor_bf;
    const area = Math.max(b.area_km2, 0.5);
    const tcHr = Math.max(b.tc_kirpich_min / 60.0, 0.15);
    const tpHr = 0.6 * tcHr + 0.5 * 1.0;
    const qRunoff = stormMmHr > ia ? Math.pow(stormMmHr - ia, 2) / (stormMmHr - ia + s) : 0.0;
    const qpBulked = bf * (0.208 * area * qRunoff) / tpHr;
    const ratio = qpBulked / Math.max(b.apex_channel_capacity_m3s, 0.1);
    return {{
      qRunoffMm: qRunoff,
      qpBulkedM3s: qpBulked,
      exceedanceRatio: ratio,
      isOverflowing: stormMmHr >= b.critical_1hr_rain_threshold_mm || ratio >= 1.0
    }};
  }}

  function initMap() {{
    map = L.map('map', {{
      center: [-17.385, -66.165],
      zoom: 12,
      preferCanvas: true
    }});

    const darkBase = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
      attribution: '&copy; OpenStreetMap &copy; CARTO | FABDEM V1-2 | Sentinel-1 & ALOS-2 | GAMC',
      maxZoom: 19
    }}).addTo(map);

    const satBase = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      attribution: 'Esri World Imagery',
      maxZoom: 19
    }});

    L.control.layers({{ "Dark Scientific Base": darkBase, "Satellite Imagery": satBase }}, null, {{ position: 'topright' }}).addTo(map);

    // Initialize layer groups
    ["distritos", "basins", "cota2750", "drenaje", "sinks", "paleochannels", "manzanas", "chokepoints", "infra", "emergencias"].forEach(k => {{
      layerGroups[k] = L.layerGroup().addTo(map);
    }});
    // Uncheck emergencias by default
    map.removeLayer(layerGroups["emergencias"]);

    // Static reference layers
    L.geoJSON(APP_DATA.layers.distritos, {{
      style: {{ color: "#475569", weight: 1, fillOpacity: 0.02, dashArray: "3,3" }}
    }}).addTo(layerGroups["distritos"]);

    L.geoJSON(APP_DATA.layers.cota2750, {{
      style: {{ color: "#22c55e", weight: 2.2, fillOpacity: 0.0, dashArray: "6,4" }},
      onEachFeature: (f, l) => l.bindTooltip("Cota 2750 m: Valid Mountain SAR Dielectric Domain Above / Urban Double-Bounce Masked Below")
    }}).addTo(layerGroups["cota2750"]);

    L.geoJSON(APP_DATA.layers.drenaje, {{
      style: {{ color: "#64748b", weight: 1.6, opacity: 0.75, dashArray: "2,4" }},
      onEachFeature: (f, l) => {{
        const nm = f.properties.nombre_ || "Canal / Torrentera";
        l.bindTooltip(`Mapped Channel: ${{nm}} (≤120m buffer excluded from novel hazard claims)`);
      }}
    }}).addTo(layerGroups["drenaje"]);

    // Sinks Layer (SINK-*)
    L.geoJSON(APP_DATA.layers.sinks, {{
      style: f => ({{
        color: f.properties.rocha_backwater_lock_sensitive ? "#0284c7" : "#38bdf8",
        fillColor: f.properties.rocha_backwater_lock_sensitive ? "#0284c7" : "#38bdf8",
        weight: 1.5,
        fillOpacity: 0.55
      }}),
      onEachFeature: (f, l) => {{
        const p = f.properties;
        l.on('click', () => showMechanismDossier('SINK', p));
        l.bindTooltip(`<strong>${{p.sink_id}}</strong> (${{p.hazard_type}})<br/>Dist. from River: ${{p.mean_distance_from_mapped_river_m}} m | Max Depth: ${{p.max_depression_depth_m}} m`);
      }}
    }}).addTo(layerGroups["sinks"]);

    // Paleochannels Layer (PALEO-*)
    L.geoJSON(APP_DATA.layers.paleochannels, {{
      style: {{
        color: "#ea580c",
        fillColor: "#fb923c",
        weight: 1.6,
        fillOpacity: 0.55
      }},
      onEachFeature: (f, l) => {{
        const p = f.properties;
        l.on('click', () => showMechanismDossier('PALEO', p));
        l.bindTooltip(`<strong>${{p.corridor_id}}</strong>: Off-Channel Paleochannel Breakout<br/>Dist. from River: ${{p.mean_distance_from_mapped_river_m}} m | Upslope Area: ${{p.upslope_contributing_area_km2}} km²`);
      }}
    }}).addTo(layerGroups["paleochannels"]);

    // Non-Obvious High-Risk Manzanas
    L.geoJSON(APP_DATA.layers.manzanas, {{
      style: f => {{
        const mech = f.properties.hazard_mechanism;
        const col = mech === "COMPOUND_AVULSION_TO_SINK_TRAP" ? "#a855f7" : (mech === "NON_OBVIOUS_AVULSION_PALEOCHANNEL" ? "#ef4444" : "#0ea5e9");
        return {{ color: col, fillColor: col, weight: 1.0, fillOpacity: 0.78 }};
      }},
      onEachFeature: (f, l) => {{
        const p = f.properties;
        l.on('click', () => showMechanismDossier('MANZANA', p));
        l.bindTooltip(`<strong>Manzana (${{p.distritos}})</strong>: ${{p.personas_num}} residents<br/>Mechanism: ${{p.hazard_mechanism}}<br/>Dist. to Mapped River: ${{p.dist_to_mapped_channel_m}} m (&gt;120m Non-Tautological)`);
      }}
    }}).addTo(layerGroups["manzanas"]);

    // Choke Points (AVN-*)
    L.geoJSON(APP_DATA.layers.chokepoints, {{
      pointToLayer: (f, latlng) => L.circleMarker(latlng, {{
        radius: 6.5,
        fillColor: "#dc2626",
        color: "#ffffff",
        weight: 1.5,
        fillOpacity: 0.95
      }}),
      onEachFeature: (f, l) => {{
        const p = f.properties;
        l.on('click', () => showMechanismDossier('AVN', p));
        l.bindTooltip(`<strong>${{p.node_id}}</strong>: Hydraulic Choke on ${{p.channel_name}}<br/>Bend: ${{p.bend_angle_deg}}° | Slope Drop: ${{p.slope_drop_ratio}}x | DSM Constriction: +${{p.building_constriction_dz_m}}m`);
      }}
    }}).addTo(layerGroups["chokepoints"]);

    // Critical Infrastructure (32 Schools + 12 Health Centers)
    L.geoJSON(APP_DATA.layers.schools_exposed, {{
      pointToLayer: (f, latlng) => L.circleMarker(latlng, {{
        radius: 5.5,
        fillColor: "#facc15",
        color: "#0f172a",
        weight: 1.5,
        fillOpacity: 0.95
      }}),
      onEachFeature: (f, l) => {{
        const p = f.properties;
        l.bindTooltip(`<strong>School: ${{p.nombre || p.unidad_edu || 'Unidad Educativa'}}</strong><br/>Off-Channel Hazard: ${{p.hazard_mechanism}}<br/>Dist. from River: ${{p.dist_to_mapped_channel_m}} m`);
      }}
    }}).addTo(layerGroups["infra"]);

    L.geoJSON(APP_DATA.layers.health_exposed, {{
      pointToLayer: (f, latlng) => L.circleMarker(latlng, {{
        radius: 6.5,
        fillColor: "#ec4899",
        color: "#ffffff",
        weight: 1.5,
        fillOpacity: 0.95
      }}),
      onEachFeature: (f, l) => {{
        const p = f.properties;
        l.bindTooltip(`<strong>Health Center: ${{p.nombre || 'Centro de Salud'}}</strong><br/>Off-Channel Hazard: ${{p.hazard_mechanism}}<br/>Dist. from River: ${{p.dist_to_mapped_channel_m}} m`);
      }}
    }}).addTo(layerGroups["infra"]);

    // GAMC Emergencias
    L.geoJSON(APP_DATA.layers.emergencias, {{
      pointToLayer: (f, latlng) => L.circleMarker(latlng, {{
        radius: 5,
        fillColor: "#c084fc",
        color: "#0f172a",
        weight: 1,
        fillOpacity: 0.9
      }}),
      onEachFeature: (f, l) => {{
        const p = f.properties;
        l.bindTooltip(`<strong>GAMC Emergency: ${{p.tipo}}</strong><br/>${{p.descripcion}}<br/>Category: ${{p.hazard_category}}`);
      }}
    }}).addTo(layerGroups["emergencias"]);

    renderDynamicBasinsAndKpis();
  }}

  function toggleMapLayer(key, visible) {{
    if (!layerGroups[key]) return;
    if (visible) {{
      map.addLayer(layerGroups[key]);
    }} else {{
      map.removeLayer(layerGroups[key]);
    }}
  }}

  function toggleGamcLiveWms(enabled) {{
    if (enabled) {{
      if (!gamcWmsLayer) {{
        gamcWmsLayer = L.tileLayer.wms("https://serviciosgamc.cochabamba.bo/api/gs/wms", {{
          layers: "zonas_de_inundacion",
          format: "image/png",
          transparent: true,
          version: "1.1.1",
          service_id: "b7a13df8-544e-4b03-9214-05a8d1a40b71",
          key: "$2y$10$2fd33273234c0a043d6b0O353564c9778b7ca4b03d94f3a1ab8e."
        }});
      }}
      gamcWmsLayer.addTo(map);
    }} else if (gamcWmsLayer) {{
      map.removeLayer(gamcWmsLayer);
    }}
  }}

  function getBasinMapForScenario(scKey) {{
    const list = APP_DATA.hydro_scenarios[scKey] || [];
    const out = {{}};
    list.forEach(b => {{ out[b.basin_id] = b; }});
    return out;
  }}

  function renderDynamicBasinsAndKpis() {{
    const stormMmHr = parseFloat(document.getElementById("stormSlider").value);
    document.getElementById("stormValLabel").textContent = `${{stormMmHr}} mm/hr`;

    const bMap = getBasinMapForScenario(activeScenarioKey);
    const basinList = APP_DATA.hydro_scenarios[activeScenarioKey] || [];

    let precondCount = 0;
    let triggeredCount = 0;

    layerGroups["basins"].clearLayers();

    L.geoJSON(APP_DATA.layers.basins, {{
      style: f => {{
        const bid = f.properties.ogc_fid || f.properties.basin_id;
        const b = bMap[bid];
        if (!b) return {{ color: "#475569", weight: 1, fillOpacity: 0.2 }};
        const sim = simulateStormForBasin(b, stormMmHr);
        const baseColor = getTierColor(b.alert_tier);
        return {{
          color: sim.isOverflowing ? "#ef4444" : baseColor,
          fillColor: baseColor,
          weight: sim.isOverflowing ? 2.8 : 1.4,
          fillOpacity: sim.isOverflowing ? 0.52 : 0.32
        }};
      }},
      onEachFeature: (f, l) => {{
        const bid = f.properties.ogc_fid || f.properties.basin_id;
        const b = bMap[bid];
        if (!b) return;
        const sim = simulateStormForBasin(b, stormMmHr);
        l.on('click', () => {{
          selectedBasinId = bid;
          showBasinDossier(b, stormMmHr);
        }});
        l.bindTooltip(
          `<strong>${{b.basin_name}}</strong> (${{b.process_regime}})<br/>` +
          `Antecedent Tier: <b>${{b.alert_tier}}</b> (W_ant = ${{b.antecedent_wetness_index}})<br/>` +
          `Critical 1-Hr Trigger P_crit = <b>${{b.critical_1hr_rain_threshold_mm}} mm/hr</b><br/>` +
          `At ${{stormMmHr}} mm/hr: Q_p,bulked = ${{sim.qpBulkedM3s.toFixed(1)}} m³/s (${{(sim.exceedanceRatio*100).toFixed(0)}}% of apex capacity)`
        );
      }}
    }}).addTo(layerGroups["basins"]);

    // Update Ranking Table & KPIs
    const tbody = document.getElementById("basinRankingBody");
    tbody.innerHTML = "";
    const sorted = [...basinList].sort((a, b) => a.critical_1hr_rain_threshold_mm - b.critical_1hr_rain_threshold_mm);

    sorted.forEach(b => {{
      if (b.alert_tier === "ORANGE_HIGH_SUSCEPTIBILITY" || b.alert_tier === "RED_CRITICAL_PRECONDITIONED") {{
        precondCount++;
      }}
      const sim = simulateStormForBasin(b, stormMmHr);
      if (sim.isOverflowing) triggeredCount++;

      const tr = document.createElement("tr");
      tr.style.cursor = "pointer";
      tr.style.borderBottom = "1px solid rgba(51,65,85,0.4)";
      if (b.basin_id === selectedBasinId) {{
        tr.style.background = "rgba(56, 189, 248, 0.14)";
      }}
      tr.onclick = () => {{
        selectedBasinId = b.basin_id;
        showBasinDossier(b, stormMmHr);
      }};
      const col = getTierColor(b.alert_tier);
      tr.innerHTML = `
        <td style="padding:5px 4px; font-weight:600; color:${{col}};">${{b.basin_name}}</td>
        <td style="padding:5px 4px; text-align:right;">${{b.antecedent_wetness_index.toFixed(2)}}</td>
        <td style="padding:5px 4px; text-align:right;">${{b.debris_bulking_factor_bf.toFixed(2)}}x</td>
        <td style="padding:5px 4px; text-align:right; font-weight:700;">${{b.critical_1hr_rain_threshold_mm.toFixed(1)}} mm</td>
        <td style="padding:5px 4px; text-align:right; color:${{sim.isOverflowing ? '#f87171' : '#94a3b8'}}; font-weight:700;">
          ${{(sim.exceedanceRatio * 100).toFixed(0)}}%
        </td>
      `;
      tbody.appendChild(tr);
    }});

    document.getElementById("kpiPrecondBasins").textContent = `${{precondCount}} / ${{basinList.length}}`;
    document.getElementById("kpiTriggeredBasins").textContent = `${{triggeredCount}} / ${{basinList.length}}`;

    if (bMap[selectedBasinId]) {{
      showBasinDossier(bMap[selectedBasinId], stormMmHr);
    }}
  }}

  function showBasinDossier(b, stormMmHr) {{
    const sim = simulateStormForBasin(b, stormMmHr);
    const sarMap = {{}};
    APP_DATA.sar_summary.basin_sar_metrics.forEach(s => {{ sarMap[s.basin_id] = s; }});
    const sar = sarMap[b.basin_id] || {{}};

    const el = document.getElementById("inspectorContent");
    el.innerHTML = `
      <div class="dossier-header">${{b.basin_name}} <span style="font-size:0.76rem; color:var(--text-muted);">(${{b.area_km2}} km²)</span></div>
      <div class="tier-pill tier-${{b.alert_tier}}">${{b.alert_tier.replace(/_/g, ' ')}}</div>
      <div style="font-size:0.76rem; color:#cbd5e1; margin-bottom:8px;">
        <strong>Process Regime:</strong> ${{b.process_regime}}
      </div>
      <table class="metric-table">
        <tr><td>Elevation Range (FABDEM V1-2)</td><td>${{b.z_min_m}} – ${{b.z_max_m}} m</td></tr>
        <tr><td>Melton Ruggedness Index (R_m)</td><td>${{b.melton_ruggedness_rm}}</td></tr>
        <tr><td>Mean Slope / 90th Pct Slope</td><td>${{b.slope_mean_deg}}° / ${{b.slope_p90_deg}}°</td></tr>
        <tr><td>Kirpich Concentration Time (T_c)</td><td>${{b.tc_kirpich_min}} min</td></tr>
        <tr><td>Valid Non-Urban SAR Domain (&gt;2750m)</td><td>${{((sar.sar_valid_pixel_fraction || 0)*100).toFixed(1)}}% of basin</td></tr>
        <tr><td>S1 C-Band Wetting Δγ°_VV (Wet−Dry)</td><td>${{(sar.s1_seasonal_delta_vv_db >= 0 ? '+' : '') + (sar.s1_seasonal_delta_vv_db || 0).toFixed(2)}} dB</td></tr>
        <tr><td>ALOS-2/NISAR L-Band HH / RVI</td><td>${{(sar.alos_lband_hh_db || 0).toFixed(1)}} dB / ${{(sar.alos_lband_rvi || 0).toFixed(2)}}</td></tr>
        <tr><td><strong>Antecedent Wetness Index W_ant(t)</strong></td><td><strong>${{b.antecedent_wetness_index}}</strong></td></tr>
        <tr><td>Remaining Soil Storage S(t) [Loss %]</td><td>${{b.remaining_soil_storage_s_mm}} mm (-${{b.storage_capacity_lost_pct}}%)</td></tr>
        <tr><td>Debris-Flow Bulking Factor BF(t)</td><td>${{b.debris_bulking_factor_bf}}x (C_v = ${{b.sediment_volume_conc_cv}})</td></tr>
        <tr><td>Downstream Apex Safe Capacity Q_cap</td><td>${{b.apex_channel_capacity_m3s}} m³/s</td></tr>
        <tr><td><strong>Critical 1-Hr Trigger Rainfall P_crit</strong></td><td style="color:var(--accent-yellow); font-weight:800;">${{b.critical_1hr_rain_threshold_mm}} mm/hr</td></tr>
        <tr><td>Simulated Q_p,bulked at ${{stormMmHr}} mm/hr</td><td style="color:${{sim.isOverflowing ? '#f87171' : '#4ade80'}}; font-weight:800;">
          ${{sim.qpBulkedM3s.toFixed(1)}} m³/s (${{(sim.exceedanceRatio*100).toFixed(0)}}% of Q_cap)
        </td></tr>
      </table>
    `;
  }}

  function showMechanismDossier(type, p) {{
    const el = document.getElementById("inspectorContent");
    if (type === 'PALEO') {{
      el.innerHTML = `
        <div class="dossier-header">${{p.corridor_id}}: Off-Channel Paleochannel Breakout</div>
        <div class="tier-pill tier-ORANGE_HIGH_SUSCEPTIBILITY">NON-TAUTOLOGICAL MECHANISM A (&gt;120m FROM RIVER)</div>
        <p style="font-size:0.78rem; color:#cbd5e1; margin-bottom:8px;">${{p.non_tautological_justification}}</p>
        <table class="metric-table">
          <tr><td>Mean Distance from Mapped Channel</td><td>${{p.mean_distance_from_mapped_river_m}} m</td></tr>
          <tr><td>Corridor Polygon Area</td><td>${{p.area_ha}} ha</td></tr>
          <tr><td>Upslope Bare-Earth Contributing Area</td><td>${{p.upslope_contributing_area_km2}} km²</td></tr>
          <tr><td>Mean Elevation (FABDEM V1-2)</td><td>${{p.mean_elevation_m}} m</td></tr>
          <tr><td>Mean DSM Building Obstruction ΔZ</td><td>+${{p.urban_obstruction_dz_m}} m</td></tr>
        </table>
      `;
    }} else if (type === 'SINK') {{
      el.innerHTML = `
        <div class="dossier-header">${{p.sink_id}}: Off-Channel Topographic / Backwater Sink</div>
        <div class="tier-pill tier-RED_CRITICAL_PRECONDITIONED">${{p.hazard_type}}</div>
        <p style="font-size:0.78rem; color:#cbd5e1; margin-bottom:8px;">${{p.non_tautological_justification}}</p>
        <table class="metric-table">
          <tr><td>Mean Distance from Mapped Channel</td><td>${{p.mean_distance_from_mapped_river_m}} m</td></tr>
          <tr><td>Depression Area</td><td>${{p.area_ha}} ha</td></tr>
          <tr><td>Max Bare-Earth Pooling Depth</td><td>${{p.max_depression_depth_m}} m</td></tr>
          <tr><td>Retention Volume Capacity</td><td>${{Number(p.retention_volume_m3).toLocaleString()}} m³</td></tr>
          <tr><td>Mean HAND (Height Above Nearest Drainage)</td><td>${{p.mean_hand_m}} m</td></tr>
          <tr><td>Río Rocha Backwater Lock Sensitive</td><td>${{p.rocha_backwater_lock_sensitive ? 'YES (Drainage Flap-Lock)' : 'No (Internal Endorheic)'}}</td></tr>
        </table>
      `;
    }} else if (type === 'AVN') {{
      el.innerHTML = `
        <div class="dossier-header">${{p.node_id}}: Alluvial Fan Apex Hydraulic Choke Point</div>
        <div class="tier-pill tier-RED_CRITICAL_PRECONDITIONED">DEBRIS-FLOW PLUGGING &amp; AVULSION NODE</div>
        <p style="font-size:0.78rem; color:#cbd5e1; margin-bottom:8px;">${{p.physical_mechanism}}</p>
        <table class="metric-table">
          <tr><td>Channel Name</td><td>${{p.channel_name}} (${{p.channel_class}})</td></tr>
          <tr><td>Apex Elevation (FABDEM V1-2)</td><td>${{p.elevation_m}} m</td></tr>
          <tr><td>Channel Deflection Bend Angle</td><td>${{p.bend_angle_deg}}°</td></tr>
          <tr><td>Upslope-to-Local Slope Drop Ratio</td><td>${{p.slope_drop_ratio}}x</td></tr>
          <tr><td>Local DSM Building/Tree Constriction</td><td>+${{p.building_constriction_dz_m}} m</td></tr>
          <tr><td>Composite Avulsion Breakout Index</td><td>${{p.avulsion_Breakout_index}}</td></tr>
        </table>
      `;
    }} else if (type === 'MANZANA') {{
      el.innerHTML = `
        <div class="dossier-header">Urban Block (Manzana) — District ${{p.distritos}}</div>
        <div class="tier-pill tier-RED_CRITICAL_PRECONDITIONED">${{p.hazard_mechanism}}</div>
        <table class="metric-table">
          <tr><td>Resident Population (GAMC Censo)</td><td>${{p.personas_num}} inhabitants</td></tr>
          <tr><td>Dwellings (Viviendas)</td><td>${{p.viviendas_num}}</td></tr>
          <tr><td>Distance to Nearest Mapped Channel</td><td>${{p.dist_to_mapped_channel_m}} m (&gt;120m Non-Tautological)</td></tr>
          <tr><td>Distance to Nearest Avulsion Choke Node</td><td>${{p.dist_to_avulsion_node_m}} m</td></tr>
          <tr><td>Composite Off-Channel Risk Score</td><td>${{p.composite_risk_score}}</td></tr>
        </table>
      `;
    }}
  }}

  function onScenarioChange() {{
    activeScenarioKey = document.getElementById("scenarioSelect").value;
    renderDynamicBasinsAndKpis();
  }}

  function onStormSliderChange() {{
    renderDynamicBasinsAndKpis();
  }}

  function initChartsAndTables() {{
    // Populate District Table
    const dBody = document.getElementById("districtTableBody");
    APP_DATA.hazard_summary.district_ranking.forEach(d => {{
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${{d.distrito}}</strong></td>
        <td>${{d.novel_off_channel_exposed_manzanas.toLocaleString()}}</td>
        <td style="font-weight:700; color:var(--accent-orange);">${{d.novel_off_channel_exposed_population.toLocaleString()}}</td>
        <td>${{d.avulsion_paleochannel_population.toLocaleString()}}</td>
        <td>${{d.endorheic_sink_population.toLocaleString()}}</td>
        <td>${{d.compound_trap_population.toLocaleString()}}</td>
        <td style="color:var(--text-muted);">${{d.tautological_channel_buffer_population_excluded.toLocaleString()}}</td>
      `;
      dBody.appendChild(tr);
    }});

    // Populate Emergencias Hydraulic & Obstruction Incidents
    const eBody = document.getElementById("emergTableBody");
    const incidents = APP_DATA.validation_report.gamc_ground_truth_audit.hydraulic_and_obstruction_incidents || [];
    incidents.forEach(inc => {{
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${{inc.type}}</strong></td>
        <td>${{inc.description}}</td>
        <td>${{inc.dist_to_channel_m}} m</td>
        <td>PALEO: ${{inc.dist_to_paleo_corridor_m}}m | SINK: ${{inc.dist_to_pluvial_sink_m}}m</td>
      `;
      eBody.appendChild(tr);
    }});

    // Initialize Backtest Charts
    const t18 = APP_DATA.taquina_trajectories["2018_taquina_disaster"].filter(d => d.date <= "2018-02-06").slice(-20);
    const t20 = APP_DATA.taquina_trajectories["2020_taquina_disaster"].filter(d => d.date <= "2020-02-21").slice(-20);
    const labels = t18.map((_, idx) => `Day ${{idx - (t18.length - 1)}}`);

    const ctxW = document.getElementById("chartBacktestWetness").getContext("2d");
    new Chart(ctxW, {{
      type: "line",
      data: {{
        labels: labels,
        datasets: [
          {{
            label: "2018 Taquiña W_ant (0–1)",
            data: t18.map(d => d.antecedent_wetness_index),
            borderColor: "#ef4444",
            backgroundColor: "rgba(239,68,68,0.15)",
            tension: 0.25
          }},
          {{
            label: "2020 Taquiña W_ant (0–1)",
            data: t20.map(d => d.antecedent_wetness_index),
            borderColor: "#f97316",
            backgroundColor: "rgba(249,115,22,0.15)",
            tension: 0.25
          }}
        ]
      }},
      options: {{
        plugins: {{ legend: {{ labels: {{ color: "#f8fafc" }} }} }},
        scales: {{
          x: {{ ticks: {{ color: "#94a3b8" }}, grid: {{ color: "rgba(148,163,184,0.15)" }} }},
          y: {{ min: 0.2, max: 1.0, ticks: {{ color: "#94a3b8" }}, grid: {{ color: "rgba(148,163,184,0.15)" }} }}
        }}
      }}
    }});

    const ctxP = document.getElementById("chartBacktestPcrit").getContext("2d");
    new Chart(ctxP, {{
      type: "line",
      data: {{
        labels: labels,
        datasets: [
          {{
            label: "2018 Taquiña Critical Rain P_crit (mm/hr)",
            data: t18.map(d => d.critical_1hr_rain_threshold_mm),
            borderColor: "#ef4444",
            tension: 0.25
          }},
          {{
            label: "2020 Taquiña Critical Rain P_crit (mm/hr)",
            data: t20.map(d => d.critical_1hr_rain_threshold_mm),
            borderColor: "#f97316",
            tension: 0.25
          }},
          {{
            label: "Dry Baseline P_crit (48.7 mm/hr)",
            data: labels.map(() => 48.7),
            borderColor: "#64748b",
            borderDash: [5, 5],
            pointRadius: 0
          }}
        ]
      }},
      options: {{
        plugins: {{ legend: {{ labels: {{ color: "#f8fafc" }} }} }},
        scales: {{
          x: {{ ticks: {{ color: "#94a3b8" }}, grid: {{ color: "rgba(148,163,184,0.15)" }} }},
          y: {{ min: 12, max: 52, ticks: {{ color: "#94a3b8" }}, grid: {{ color: "rgba(148,163,184,0.15)" }} }}
        }}
      }}
    }});
  }}

  window.addEventListener("DOMContentLoaded", () => {{
    initMap();
    initChartsAndTables();
  }});
</script>
</body>
</html>
"""

    out_path = DOCS_DIR / "index.html"
    out_path.write_text(html_content, encoding="utf-8")
    print(f"[Dashboard Builder] Generated self-contained WebGIS at {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")
    return out_path


if __name__ == "__main__":
    build_webgis_dashboard()
