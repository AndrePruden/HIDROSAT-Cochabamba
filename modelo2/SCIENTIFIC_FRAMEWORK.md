# Epistemological & Physical Framework: Cochabamba Multi-Day Flood & Debris-Flow Pre-Conditioning System

## 1. Core Epistemological Premise: Matching Every Sensor to Its True Physical Scale

A common failure in satellite-based flood hazard systems is **scale overstatement**: using digital surface models (DSMs) as if they were bare earth, applying Synthetic Aperture Radar (SAR) inside dense brick-and-concrete cities where double-bounce corner reflections dominate, or claiming street-level flash-flood nowcasting from ~10 km satellite precipitation pixels.

This system enforces strict **physical and epistemological bounds** across four domains:

| Physical Domain | Dataset Used | Spatial / Temporal Resolution | What It CAN Physically Resolve (Used Here) | What It CANNOT Resolve (Explicitly Excluded) |
| :--- | :--- | :--- | :--- | :--- |
| **1. Bare-Earth Topography** | **FABDEM V1-2** (Forest And Buildings removed DEM) + **Copernicus GLO-30 DSM** | ~30 m (`29.5 m × 30.7 m` at $17.4^\circ\text{S}$) | Watershed geomorphometry (Melton $R_m$, hypsometry, Kirpich $T_c$), decameter-scale alluvial fan paleochannel swales (`PALEO-*`), apex slope breaks (`AVN-*`), valley-floor endorheic depressions (`SINK-*`), and building/canopy hydraulic constriction ($\Delta Z = Z_{\text{DSM}} - Z_{\text{FABDEM}}$). | Sub-meter street curbs, storm-drain grates, or individual house perimeter walls. Evaluated strictly at watershed, fan-corridor, and urban-block (`Manzana`) scales. |
| **2. Synthetic Aperture Radar (C-Band & L-Band)** | **Sentinel-1 C-Band RTC** ($\lambda=5.6\text{ cm}$, Asc Orbit 003 + Desc Orbit 156) & **ALOS-2 PALSAR-2 L-Band** ($\lambda=23.6\text{ cm}$, NISAR L-band equivalent) | 20–25 m spatial; 6–12 day orbital revisit | Multi-day dielectric soil wetting ($\epsilon_r: 4 \to 30$) in **non-urban Upper Tunari catchments above `Cota 2750 m`** (pajonal, shrubland, colluvial hollows, and *bofedales*) after **Dual-Orbit (Asc+Desc) aspect-weighted fusion**, plus open agricultural ponding in southern La Maica / Tamborada. | **Dense urban areas (`Límite Urbano` / WorldCover Class 50)** where dihedral brick/concrete corner reflectors pin C-band $\gamma^0_{VV}$ at $-4.73\text{ dB}$ (dry) vs. $-4.91\text{ dB}$ (wet) ($\Delta = -0.19\text{ dB}$ noise, $52.1\%$ double-bounce contaminated). Also cannot provide sub-hourly flash-flood detection due to orbital revisit. |
| **3. Mesoscale Precipitation & Soil Moisture** | **GPM IMERG / ERA5-Land** (6 mesoscale sectors) & **GloFAS** Río Rocha discharge | ~9–11 km ($\sim 100\text{ km}^2$ pixel); daily / multi-hour latency | **Multi-day Antecedent Pre-Conditioning** over the previous 3–21 days: Antecedent Precipitation Index ($\text{API}_{k=0.85}$, $\text{API}_{k=0.92}$), root-zone soil moisture ($0\text{–}100\text{ cm}$), dynamic SCS Curve Number storage collapse $S(t)$, debris-flow sediment bulking $BF(t)$, and critical 1-hour trigger threshold $P_{\text{crit}}(t)$. | Pinpointing which individual 2–15 $\text{km}^2$ Tunari micro-canyon receives a 30-minute convective cloudburst in real time (**22 of 23 Tunari watersheds are smaller than a single ~100 $\text{km}^2$ satellite rainfall pixel**, and **16 of 23 have $T_c < 60\text{ min}$**). |
| **4. Municipal Cadastre & Ground Truth** | **GAMC GeoServer API** (15 vector layers + `red_monica.zip`) | Block (`Manzana`) & facility point level | Block-level off-channel exposure (`14,145 Manzanas`, `264 Schools`, `67 Health Centers`), `Cota 2750` conservation boundary, `Cuencas de Influencia` (23 basins), and field reports (`Emergencias`) of anthropogenic canal filling and drainage blockages. | `red_monica.zip` was audited and proved to contain atmospheric $\text{PM}_{10}$ air quality (`estacion, pm10, fecha_medicion`), **not** rain gauges; it is excluded from hydrological forcing. |

---

## 2. Quantitative Proofs from Real Satellite & Municipal Data

### Proof 1: Why Bare-Earth FABDEM V1-2 Is Mandatory Over Standard DSMs
Comparing co-registered **Copernicus GLO-30 DSM** ($Z_{\text{DSM}}$) against **FABDEM V1-2** ($Z_{\text{FABDEM}}$) across the $1008 \times 936$ Cochabamba grid (`[-66.30, -17.51, -66.03, -17.23]`):
- Inside the **90 m riparian corridor** along GAMC's 47 mapped torrenteras and rivers, riparian *Eucalyptus*/*Molle* canopy and streamside buildings introduce a mean positive elevation bias of **$+2.45\text{ m}$** and a **90th-percentile bias of $+8.24\text{ m}$** (up to $+34.9\text{ m}$).
- This creates **9,328 false dam pixels ($\Delta Z > 3.0\text{ m}$)** directly across drainage channels and **476.8 ha of artificial street-canyon sinks** on a standard DSM.
- Bare-earth **FABDEM V1-2** removes these artificial dams while uncovering **632.2 ha of true geomorphic valley-floor depressions** and paleochannel distributaries.

### Proof 2: SAR Urban Double-Bounce Exclusion & Dual-Orbit Steep-Slope Fusion
- **Urban Domain (`Límite Urbano`)**: $52.1\%$ of pixels exceed the $-3.5\text{ dB}$ dihedral corner-reflector threshold in dry winter. Mean Sentinel-1 C-band $\gamma^0_{VV}$ is $-4.73\text{ dB}$ (Aug 2026 dry) vs. $-4.91\text{ dB}$ (Feb 2026 wet) — a seasonal difference of **$-0.19\text{ dB}$ (pure clutter)**. Urban pixels are strictly masked out.
- **Upper Tunari Domain (Above `Cota 2750 m`)**: In natural tussock grass (*pajonal*), shrubland, and colluvial hollows (e.g., `C. Taquiña` $96.2\%$ valid, `C. Wara Wara` $97.7\%$ valid, `C. Khora` $94.9\%$ valid, `C. Pintu Mayu` $93.9\%$ valid), C-band $\gamma^0_{VV}$ increases by **$+1.06\text{ dB}$ cordillera-wide (up to $+2.04\text{ dB}$ basin-wide mean and $+6.57\text{ dB}$ 90th-percentile in colluvial hollows/*bofedales*)** from dry to wet season.
- **Dual-Orbit RTC Fusion**: Single-orbit Descending (Orbit 156) loses **$11.0\%$** of Tunari slopes to layover/shadow and Ascending (Orbit 003) loses **$8.2\%$**. Aspect-weighted fusion of Ascending + Descending orbits reduces unrecoverable steep-cliff loss to **$1.5\%$** ($98.5\%$ valid coverage).

---

## 3. Anti-Tautology Formulation: Discovering Off-Channel Hazard Zones ($>120\text{ m}$ from Rivers)

A system that merely flags a buffer around mapped rivers states a trivial tautology (*"there is flood risk near rivers"*). We explicitly **exclude the $\le 120\text{ m}$ channel corridor** (`5,155 Manzanas` / `191,307 inhabitants`) from novel hazard discovery and model three distinct **off-channel physical hazard mechanisms**:

1. **Mechanism A — Alluvial Fan Apex Hydraulic Choke Points (`AVN-01`..`AVN-28`) & Bare-Earth Paleochannel Breakout Corridors (`PALEO-001`..`PALEO-045`)**:
   - Where steep Tunari canyons ($18^\circ\text{–}28^\circ$) exit onto the Cochabamba piedemonte ($2\^\circ\text{–}6^\circ$), abrupt slope reduction drops sediment transport capacity while sharp artificial channel deflections ($>22^\circ$) and urban building encroachments ($\Delta Z > 3\text{ m}$) constrict the cross-section.
   - When a debris flow (*mazamorra*) plugs an apex choke point, flow avulses out of the engineered canal and follows **relict bare-earth Holocene paleochannel swales** across the urban fan hundreds of meters away from the mapped canal.
   - Our MFD bare-earth routing identifies **45 off-channel paleochannel breakout corridors (`PALEO-001`..`PALEO-045`)** strictly $>120\text{ m}$ from mapped channels, exposing **437 urban blocks (`38,118 inhabitants`)** at a mean distance of **397.9 m** from the nearest mapped river.

2. **Mechanism B — Valley-Floor Endorheic Depressions & Río Rocha Backwater-Locked Pluvial Bowls (`SINK-001`..`SINK-045`)**:
   - In the flat lacustrine valley floor (Distritos 4, 5, 6, 9, 10, 11), bare-earth FABDEM depressions with low Height Above Nearest Drainage ($\text{HAND} \le 2.8\text{ m}$) cannot drain by gravity when Río Rocha / Tamborada stage rises during multi-day wet periods (flap-gate / hydraulic head lock).
   - We identify **45 off-channel pluvial/backwater sinks (`SINK-001`..`SINK-045`)** strictly $>120\text{ m}$ from mapped channels, exposing **240 urban blocks (`22,063 inhabitants`)** at a mean distance of **844.8 m** from mapped rivers, plus **16 blocks (`1,652 inhabitants`)** in **Compound Avulsion-to-Sink Traps** (mean distance **1,411.6 m** from mapped rivers).

3. **Mechanism C — Multi-Day Antecedent Catchment Pre-Conditioning & Debris-Flow Bulking (`hydro_antecedent.py`)**:
   - Combines 14-day exponential Antecedent Precipitation Index ($\text{API}_{k=0.85}$), deep soil moisture ($\theta_{\text{rz}}$), and Cota-2750 SAR dielectric saturation ($S_{\text{SAR}}$) into the composite Antecedent Wetness Index $W_{\text{ant}}(t) \in [0, 1]$.
   - Computes dynamic SCS Curve Number remaining soil storage deficit $S(t)$, Iverson debris-flow sediment bulking factor $BF(t) = \frac{1}{1 - C_v(t)} \in [1.0, 2.15]$, and inverts the coupled runoff-bulking equation to solve for the **Critical 1-Hour Convective Rainfall Trigger Depth $P_{\text{crit}}(t)$ [mm/hr]** required to exceed downstream apex channel capacity.

---

## 4. Historical Backtest Validation: Feb 6, 2018 & Feb 21, 2020 Taquiña *Mazamorra* Disasters

| Metric in `C. Taquiña` ($18.18\text{ km}^2$, $R_m = 0.432$) | Dry Winter Baseline (`2026-08-03`) | Current Pre-Wet State (`2026-11-15`) | **Feb 6, 2018 Taquiña Disaster** | **Feb 21, 2020 Taquiña Disaster** |
| :--- | :---: | :---: | :---: | :---: |
| **Previous 14-Day Cumulative Rain** | $0.8\text{ mm}$ | $33.9\text{ mm}$ | **$165.9\text{ mm}$** ($169.1\text{ mm}$ on Day -1) | **$132.1\text{ mm}$** ($103.5\text{ mm}$ on Day -1) |
| **Antecedent Wetness Index $W_{\text{ant}}(t)$** | $0.200$ | $0.585$ | **$0.831$** ($0.986$ on Day -1) | **$0.848$** ($0.861$ on Day -1) |
| **Remaining Soil Storage $S(t)$** | $157.1\text{ mm}$ | $89.4\text{ mm}$ ($-40.8\%$) | **$56.6\text{ mm}$** ($38.9\text{ mm}$ / **$-75.2\%$** on Day -1) | **$53.8\text{ mm}$** ($53.0\text{ mm}$ / **$-66.3\%$** on Day -1) |
| **Debris-Flow Bulking Factor $BF(t)$** | $1.00\times$ | $1.23\times$ | **$1.63\times$** ($2.11\times$ on Day -1) | **$1.69\times$** ($1.71\times$ on Day -1) |
| **Critical 1-Hr Trigger Rainfall $P_{\text{crit}}(t)$** | **$48.7\text{ mm/hr}$** | **$25.7\text{ mm/hr}$** | **$21.6\text{ mm/hr}$** (**$15.6\text{ mm/hr}$** on Day -1) | **$20.7\text{ mm/hr}$** (**$20.4\text{ mm/hr}$** on Day -1) |
| **Warning Tier & Pre-Disaster Lead Time** | `GREEN` | `ORANGE` | **`RED_CRITICAL` (9 Days Lead Time)** | **`RED_CRITICAL` (17 Days Lead Time)** |
