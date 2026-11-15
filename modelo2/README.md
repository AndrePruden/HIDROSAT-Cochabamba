# Cochabamba Hydro-Geomorphic Pre-Conditioning & Non-Tautological Flood Early Warning System

A scientifically rigorous, physically grounded multi-day flood and debris-flow (*mazamorra*) pre-conditioning early warning and off-channel hazard discovery system for **Cochabamba, Bolivia**.

Built with real **FABDEM V1-2** bare-earth topography, **Copernicus GLO-30 DSM**, **Sentinel-1 C-band Dual-Orbit (Ascending + Descending) RTC SAR**, **ALOS-2 PALSAR-2 L-band SAR** (NISAR L-band equivalent), **ESA WorldCover 10m**, **ERA5-Land / Open-Meteo / GloFAS** hydro-meteorological series, and **15 official GAMC municipal geospatial layers**.

---

## Key Innovations & Scientific Rigor

1. **Strict Epistemological Consistency (Zero Overstatement of Sensor Reach)**:
   - **Bare-Earth FABDEM V1-2 vs. Standard DSMs**: Proves that Copernicus GLO-30 DSM introduces a **$+2.45\text{ m}$ mean ($+8.24\text{ m}$ 90th-percentile)** building and riparian tree canopy bias along Cochabamba's 90 m channel corridors, creating **9,328 false dam pixels** and **476.8 ha of artificial street-canyon sinks**. All overland MFD routing and depression analysis is performed on bare-earth **FABDEM V1-2**, while $\Delta Z = Z_{\text{DSM}} - Z_{\text{FABDEM}}$ is used specifically to quantify urban hydraulic constriction at channel bends.
   - **Physics-Based SAR Masking (`Cota 2750 m` & Dual-Orbit Fusion)**: Demonstrates empirically that inside `Límite Urbano`, dihedral corner reflections between brick/concrete walls and streets pin Sentinel-1 C-band $\gamma^0_{VV}$ at $-4.73\text{ dB}$ (dry) vs. $-4.91\text{ dB}$ (wet) ($\Delta = -0.19\text{ dB}$ clutter noise, $52.1\%$ double-bounce contaminated). Urban SAR is strictly masked out. Conversely, in non-urban Upper Tunari catchments above `Cota 2750 m`, aspect-weighted **Dual-Orbit (Ascending Orbit 003 + Descending Orbit 156)** fusion reduces topographic layover loss from $11.0\%$ to **$1.5\%$** and captures **$+1.06\text{ to }+2.04\text{ dB}$ mean ($+6.57\text{ dB}$ P90 in colluvial hollows)** seasonal dielectric soil wetting.
   - **Multi-Day Antecedent Pre-Conditioning vs. False Flash-Flood Nowcasting**: Because **22 of 23 Tunari watersheds** (median area $10.5\text{ km}^2$) are smaller than a single ~10 km ($100\text{ km}^2$) satellite precipitation pixel and **16 of 23** have Kirpich concentration times $T_c < 60\text{ min}$ (median $36.1\text{ min}$), coarse satellite rainfall cannot pinpoint real-time street-level flash floods. Instead, we use previous days' cumulative rainfall ($\text{API}_{k=0.85}$), root-zone soil moisture, and Cota-2750 SAR wetness to track **dynamic soil storage collapse $S(t)$**, **debris-flow sediment bulking $BF(t)$**, and the **Critical 1-Hour Rainfall Trigger Threshold $P_{\text{crit}}(t)$**.

2. **Anti-Tautology Off-Channel Hazard Discovery ($>120\text{ m}$ from Mapped Rivers)**:
   - Trivial proximity to rivers ($\le 120\text{ m}$ buffer: `5,155 Manzanas` / `191,307 residents`) is explicitly excluded from novel hazard discovery.
   - Strictly outside the 120 m channel buffer, the system discovers **693 non-obvious high-risk urban blocks (`61,833 inhabitants`, `24,008 dwellings`), 32 schools (`Unidades Educativas`), and 12 health centers (`Centros de Salud`)** across three physical mechanisms:
     - **28 Alluvial Fan Apex Hydraulic Choke Points (`AVN-01`..`AVN-28`)** & **45 Off-Channel Bare-Earth Paleochannel Breakout Corridors (`PALEO-001`..`PALEO-045`)**: Exposing **437 Manzanas (`38,118 people`)** at a mean distance of **397.9 m** from mapped rivers.
     - **45 Off-Channel Endorheic & Río Rocha Backwater-Locked Pluvial Sinks (`SINK-001`..`SINK-045`)**: Exposing **240 Manzanas (`22,063 people`)** at a mean distance of **844.8 m** from mapped rivers.
     - **Compound Avulsion-to-Sink Traps**: Exposing **16 Manzanas (`1,652 people`)** at a mean distance of **1,411.6 m** from mapped rivers.

3. **Validated on the 2018 & 2020 Taquiña *Mazamorra* Disasters**:
   - Backtesting on the **Feb 6, 2018** and **Feb 21, 2020** Taquiña debris-flow disasters shows that multi-day antecedent pre-conditioning crossed into `RED_CRITICAL_PRECONDITIONED` **9 days in advance (2018)** and **17 days in advance (2020)**, collapsing remaining soil storage $S(t)$ by **$64\%\text{–}75\%$** and dropping the critical 1-hour trigger threshold $P_{\text{crit}}$ from **$48.7\text{ mm/hr}$ (dry baseline) down to $15.6\text{–}20.4\text{ mm/hr}$** on the eve of the catastrophes.

---

## Repository Structure

- [SCIENTIFIC_FRAMEWORK.md](file:///home/mobilebat/Projects/early_warning/SCIENTIFIC_FRAMEWORK.md) — Detailed epistemological matrix, mathematical equations, and validation tables.
- [docs/index.html](file:///home/mobilebat/Projects/early_warning/docs/index.html) — Self-contained interactive WebGIS dashboard & storm trigger simulator.
- `docs/figures/` — High-resolution publication diagnostic figures:
  - [fig1_dsm_vs_fabdem_proof.png](file:///home/mobilebat/Projects/early_warning/docs/figures/fig1_dsm_vs_fabdem_proof.png)
  - [fig2_sar_epistemological_domains.png](file:///home/mobilebat/Projects/early_warning/docs/figures/fig2_sar_epistemological_domains.png)
  - [fig3_taquina_backtest_2018_2020_2026.png](file:///home/mobilebat/Projects/early_warning/docs/figures/fig3_taquina_backtest_2018_2020_2026.png)
  - [fig4_non_tautological_hazard_map.png](file:///home/mobilebat/Projects/early_warning/docs/figures/fig4_non_tautological_hazard_map.png)
  - [fig5_district_exposure_and_critical_thresholds.png](file:///home/mobilebat/Projects/early_warning/docs/figures/fig5_district_exposure_and_critical_thresholds.png)
- `src/` — Modular physical modeling & application codebase:
  - [src/data_ingestion/gamc_parser.py](file:///home/mobilebat/Projects/early_warning/src/data_ingestion/gamc_parser.py) — Parses all 15 GAMC KML layers & audits `emergencias` and `red_monica.zip`.
  - [src/data_ingestion/meteo_fetcher.py](file:///home/mobilebat/Projects/early_warning/src/data_ingestion/meteo_fetcher.py) — Fetches 6-sector mesoscale precipitation, root-zone soil moisture, and GloFAS discharge across operational and historical disaster windows.
  - [src/physics/terrain_fabdem.py](file:///home/mobilebat/Projects/early_warning/src/physics/terrain_fabdem.py) — FABDEM V1-2 vs. Copernicus GLO-30 DSM proof, MFD bare-earth flow routing, Tunari basin geomorphometry, `AVN-*` choke points, `PALEO-*` corridors, and `SINK-*` depressions.
  - [src/physics/sar_dielectric.py](file:///home/mobilebat/Projects/early_warning/src/physics/sar_dielectric.py) — Sentinel-1 C-band dual-orbit fusion, ALOS-2 L-band analysis, urban corner-reflector exclusion proof, and Cota-2750 dielectric wetting retrieval.
  - [src/physics/hydro_antecedent.py](file:///home/mobilebat/Projects/early_warning/src/physics/hydro_antecedent.py) — Multi-day API, dynamic SCS-CN soil storage $S(t)$, Iverson debris-flow bulking $BF(t)$, and critical 1-hr rainfall trigger $P_{\text{crit}}(t)$.
  - [src/physics/hazard_synthesizer.py](file:///home/mobilebat/Projects/early_warning/src/physics/hazard_synthesizer.py) — Non-tautological ($>120\text{ m}$) synthesis across 14,145 `Manzanas`, 264 schools, 67 health centers, and 97 emergency reports.
  - [src/validation/scientific_audit.py](file:///home/mobilebat/Projects/early_warning/src/validation/scientific_audit.py) — Quantitative historical backtesting & 4-part epistemological ablation study.
  - [src/visualization/figures.py](file:///home/mobilebat/Projects/early_warning/src/visualization/figures.py) — Generates the 5 diagnostic figures.
  - [src/visualization/dashboard_builder.py](file:///home/mobilebat/Projects/early_warning/src/visualization/dashboard_builder.py) — Builds `docs/index.html`.
  - [src/app/server.py](file:///home/mobilebat/Projects/early_warning/src/app/server.py) — Tornado WebGIS & REST API server.
- [tests/test_scientific_consistency.py](file:///home/mobilebat/Projects/early_warning/tests/test_scientific_consistency.py) — Automated scientific verification test suite.

---

## Reproducing the Pipeline & Running the WebGIS Server (Pixi Environment)

```bash
# 1. Run the automated scientific consistency & anti-tautology test suite
pixi run test

# 2. Re-run any stage of the physical pipeline
pixi run terrain-physics
pixi run sar-physics
pixi run hydro-antecedent
pixi run synthesize-hazards
pixi run validate
pixi run figures
pixi run build-webgis

# 3. Launch the interactive WebGIS & REST API server (http://localhost:8765)
pixi run serve
```
