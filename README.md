# HIDROSAT Cochabamba · Basin Early Warning & Multi-Temporal SAR System

[![NASA Space Apps Challenge](https://img.shields.io/badge/NASA%20Space%20Apps-Dancing%20with%20the%20SAR-0B3D91?style=for-the-badge&logo=nasa)](https://www.spaceappschallenge.org/)
[![Municipality](https://img.shields.io/badge/Local%20Focus-Cochabamba%20(GAMC)-green?style=for-the-badge)](https://recursosgamc.cochabamba.bo/)
[![Live WebGIS](https://img.shields.io/badge/Live%20Demo-GitHub%20Pages-blue?style=for-the-badge&logo=github)](https://andrepruden.github.io/HIDROSAT-Cochabamba/)
[![Methodology](https://img.shields.io/badge/Methodology-Physical%20Hydro--Geomorphic%20Model-orange?style=for-the-badge)](#the-solution-physical-hydrology--radar-physics)

**An operational, physically grounded multi-day flood and debris-flow (*mazamorra*) early warning platform for the Tunari cordillera and urban river basins of Cochabamba, Bolivia.**

Developed for the **NASA International Space Apps Challenge (Cochabamba Hub)** under the global challenge **"Dancing with the SAR"**, in direct coordination with the disaster risk management and climate resilience priorities of the **Autonomous Municipal Government of Cochabamba (GAMC)**.

🌐 **Live Interactive WebGIS:** [https://andrepruden.github.io/HIDROSAT-Cochabamba/](https://andrepruden.github.io/HIDROSAT-Cochabamba/)

---

## 🏔️ Background & The Problem in Cochabamba

The Cochabamba metropolitan valley is nestled directly at the foot of the massive Cordillera del Tunari, where elevations plunge abruptly from over 4,600 meters down to 2,550 meters in less than 8 kilometers. In this complex topography, climate change has dramatically intensified localized, short-duration, high-intensity convective storm cells (30 to 60 minutes).

These extreme rainfall bursts trigger catastrophic hydrologic and geotechnical disasters:
1. **Destructive Debris Flows (*Mazamorras*)**: Rapid mobilization of millions of cubic meters of saturated colluvial sediment, boulders, and mud through steep mountain torrents (*torrenteras*), devastating alluvial fans in **Tiquipaya (Río Taquiña 2018 and 2020)** and **Sacaba (Torrentera Ch'aki Mayu 2024)**.
2. **Severe Urban Channel Overtopping & Pluvial Flooding**: Immediate hydraulic choking of underpasses, culverts, and main avenues across **Cochabamba Cercado (Pintumayu, Pajcha, Río Rocha)** and downstream backwater retention in **Colcapirhua (Chijllawiri, Duralit)**.

### The Scientific Dilemma
- **Why Flash-Flood Satellite Nowcasting Fails**: Tunari micro-watersheds have times of concentration $T_c < 60\text{ minutes}$ (median $36.1\text{ min}$) and basin areas of $2\text{–}15\text{ km}^2$. In contrast, satellite precipitation products (NASA GPM IMERG) have a coarse footprint of ~10 km ($100\text{ km}^2$) and several hours of latency. A 40-minute cloudburst will overtop urban channels long before a satellite precipitation pixel updates.
- **Why Urban SAR is Blind**: Synthetic Aperture Radar (SAR) signals inside urban street canyons below Cota 2750 m suffer from intense dihedral and trihedral corner reflections (double-bounce) between masonry walls and paved surfaces. This clutter noise masks the ground dielectric constant, making urban SAR unable to detect surface water saturation reliably.
- **Why Naive Machine Learning Fails**: With a limited historical sample of confirmed disaster events, training black-box machine learning algorithms invariably causes overfitting, false correlations, and fatal blind spots.

---

## 💡 The Solution: Physical Hydro-Geomorphic Pre-Conditioning

HIDROSAT solves this crisis by combining **radar physics**, **satellite earth observation**, and **classical physical hydrology**, avoiding black-box approximations and using real historical incident data strictly as an independent **Ground-Truth Verification Set**.

Rather than attempting impossible minute-by-minute satellite rainfall nowcasting, HIDROSAT tracks **multi-day antecedent pre-conditioning**. Disasters in Cochabamba do not happen spontaneously: they occur when several days of preceding rainfall progressively collapse the soil's retention buffer, activate steep colluvial hollows, and drastically lower the critical rainfall threshold required to unleash a catastrophe.

```
                    DATA FUSION INGESTION
 ┌────────────────────────────────────────────────────────┐
 │ • Sentinel-1 SAR (C-band RTC) & ALOS-2 (NISAR L-band)  │
 │ • NASA GPM IMERG Calibrated Multi-Day Precipitation    │
 │ • NASA SMAP Root-Zone Soil Moisture Assimilation       │
 │ • FABDEM V1-2 Bare-Earth DTM (Non-Urban Slopes)        │
 │ • GAMC 15 Official Geospatial Layers (WMS Catalog)     │
 └──────────────────────────┬─────────────────────────────┘
                            │
                            ▼
              PHYSICAL HYDROLOGICAL CORE
 ┌────────────────────────────────────────────────────────┐
 │ 1. Non-Urban SAR Dielectric Wetting above Cota 2750m   │
 │ 2. Multi-Day Antecedent Precipitation Index (API)      │
 │ 3. Dynamic SCS-CN Soil Storage Deficit S(t)            │
 │ 4. Iverson/Takahashi Debris-Flow Bulking Factor BF(t)  │
 │ 5. Critical 1-Hour Convective Rainfall Threshold Pcrit │
 └──────────────────────────┬─────────────────────────────┘
                            │
                            ▼
           EARLY WARNING & DECISION PLATFORM
 ┌────────────────────────────────────────────────────────┐
 │ • Fluid 60 FPS Day-by-Day Radar Loop Simulator         │
 │ • Historical Multi-Day Disaster Backtests              │
 │ • Real-Time Live Monitoring for Today & Forecast       │
 │ • On-Demand Satellite Evaluation for Any Custom Date   │
 │ • Automated Official Advisory Bulletin for UGR GAMC    │
 └────────────────────────────────────────────────────────┘
```

---

## 🛠️ Data, Instruments & Technologies Utilized

### 1. Active Radar Remote Sensing (SAR)
- **Sentinel-1 Dual-Orbit (Ascending 003 + Descending 156) C-Band RTC**: Weighted by bare-earth aspect angles to eliminate topographic layover loss on steep mountain faces (reducing layover shadows from $11.0\%$ to $1.5\%$).
- **ALOS-2 PALSAR-2 L-Band ($\lambda = 23.6\text{ cm}$)**: Serves as the direct scientific and polarimetric analog for the upcoming **NASA-ISRO SAR (NISAR)** mission, offering deep subsurface penetration in coarse colluvial gravels.
- **Physics-Based Cota 2750 m Urban Mask**: Urban double-bounce reflections are strictly filtered out. SAR backscatter change detection ($\gamma^0_{VV}$) is applied solely in non-urban Tunari headwaters above 2,750 m, capturing $+1.06\text{ to }+4.5\text{ dB}$ seasonal wetting.

### 2. NASA Precipitation & Soil Moisture Missions
- **NASA GPM (Global Precipitation Measurement)**: IMERG multi-day cumulative series (3-day, 7-day, and 14-day rainfall), providing the synoptic-scale moisture forcing across 6 distinct mesoscale sectors in the Cochabamba valley.
- **NASA SMAP (Soil Moisture Active Passive)**: Volumetric soil moisture assimilation across surface ($0\text{–}7\text{ cm}$) and root-zone ($7\text{–}28\text{ cm}$) soil profiles, calibrated against Andean soil characteristics.

### 3. Bare-Earth Geomorphometry & Municipal GIS
- **FABDEM V1-2 (1 arc-sec ~30 m Bare-Earth DTM)**: Unlike standard Digital Surface Models (Copernicus GLO-30 DSM) that suffer from up to $+8.24\text{ m}$ of artificial building and canopy damming, FABDEM enables realistic hydraulic flow routing, true slope computation, and Melton Ruggedness calculation.
- **Autonomous Municipal Government of Cochabamba (GAMC)**: 15 official geospatial layers integrated via WMS proxy, including UH8 hydrographic catchments, primary drainage networks, urban district polygons, and critical alluvial fan apex chokepoints.

### 4. Real Ground-Truth Scraping Dataset (Verification)
- An authentic dataset of **18 confirmed historical disaster and emergency events (2018–2026)** with verified coordinates, elevation, phenomenon classification, and news source confirmation. Used strictly as independent Ground Truth to evaluate the physical model's accuracy.

---

## ⚙️ Mathematical & Physical Principles

1. **Antecedent Catchment Wetness Index ($W_{\text{ant}}$)**:
   Combines multi-day shallow colluvial memory ($\text{API}_{k=0.85}$), deep root-zone memory ($\text{API}_{k=0.92}$), SMAP soil moisture, and Cota-2750 SAR dielectric saturation:
   $$W_{\text{ant}}(t) = w_{\text{api}} S_{\text{api}} + w_{\text{sm}} S_{\text{sm}} + w_{\text{sar}} S_{r,\text{SAR}}$$

2. **Dynamic Soil Retention Storage ($S(t)$)**:
   Calculates the daily collapse of infiltration capacity using SCS-CN steep mountain adjustments (Hawkins et al., 2002) with mountain initial abstraction $I_a(t) = 0.10 \cdot S(t)$:
   $$\text{CN}_{\text{eff}}(t) = \text{CN}_1 + W_{\text{ant}}(t) \cdot (\text{CN}_3 - \text{CN}_1) \quad \Longrightarrow \quad S(t) = \frac{25400}{\text{CN}_{\text{eff}}(t)} - 254\text{ [mm]}$$

3. **Sediment Bulking Mechanics ($BF(t)$)**:
   Debris flows multiply clear-water discharge through sediment entrainment. Based on the Melton Ruggedness Number ($R_m = \frac{\Delta H}{\sqrt{A}} > 0.30$) and colluvial hollow fraction, we determine the dynamic sediment volume concentration $C_v(t)$ (Iverson, 1997; Takahashi, 2004) and the sediment bulking factor:
   $$BF(t) = \frac{1}{1 - C_v(t)} \quad (\text{multiplying peak discharge up to } 2.12\times)$$

4. **Inversion of Critical 1-Hour Trigger Depth ($P_{\text{crit}}$)**:
   Inverts the runoff formulation against downstream urban fan apex channel safe capacity $Q_{\text{cap}}$:
   $$P_{\text{crit}}(t) = I_a(t) + \frac{1}{2}\left(Q_{\text{req}} + \sqrt{Q_{\text{req}}^2 + 4 \cdot Q_{\text{req}} \cdot S(t)}\right)$$
   While a dry catchment requires $P_{\text{crit}} \approx 48.7\text{ mm/h}$ to cause channel overtopping, multi-day saturation drops this threshold to **$15.5\text{–}18.0\text{ mm/h}$** prior to disasters.

---

## 🖥️ Platform Capabilities & User Experience

The interactive WebGIS dashboard runs entirely in the browser with **zero installation or setup required**:

- **Dual Synchronized Geospatial View**:
  - *Left View (Regional Context)*: Macro-basin UH8 view with drainage networks, urban district borders, and regional thermal saturation plumes.
  - *Right View (Focal Lens)*: High-resolution satellite lens that automatically snaps to the active threatened basin (Taquiña, Pintumayu, Sacaba / Ch'aki Mayu, Colcapirhua / Tamborada, Chutakawa / Khora).
- **60 FPS Fluid Animation Engine**:
  Uses sinusoidal ease-in/ease-out interpolation to smoothly expand and contract saturation heatmaps day-by-day, providing a fluid Doppler weather radar visual experience (similar to *Weather.com*).
- **Three Operational Exploration Modes**:
  1. **Historical Disaster Simulations**: Sequential day-by-day playback showing how stable green conditions accumulate moisture, turn yellow, and explode into red critical alerts during landmark disasters (e.g., Feb 17–22, 2020 Taquiña Mazamorra).
  2. **Live Real-Time Monitoring**: Assesses today's live satellite moisture and current weather forecasts, showing that Cochabamba is currently in a stable green state.
  3. **Custom Date Explorer**: Enables authorities or citizens to select any date on the calendar to trigger an on-the-fly NASA reanalysis and physical evaluation.
- **Institutional Early Warning Bulletin**:
  Automatically generates a technical advisory ready to copy and dispatch to the GAMC Risk Management Unit (UGR), including key physical metrics ($W_{\text{ant}}$, $S(t)$, $BF$, $P_{\text{crit}}$) and recommended civil protection actions.

---

## 🚀 Live Demo & Access

The platform is hosted and fully functional on **GitHub Pages**:

👉 **[https://andrepruden.github.io/HIDROSAT-Cochabamba/](https://andrepruden.github.io/HIDROSAT-Cochabamba/)**

*(Simply open the link in any web browser on desktop or mobile — no local Python or software installation is required).*

---

## 👥 Authors

**Xel'Naga**  
*NASA International Space Apps Challenge 2026 · Cochabamba Hub*
