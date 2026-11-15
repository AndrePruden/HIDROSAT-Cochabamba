"""
Physical constants, coordinate reference systems, spatial bounds, and epistemological
constraints for the Cochabamba Hydro-Geomorphic & Multi-Day Antecedent Warning System.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR = PROJECT_ROOT / "docs" / "figures"
DASHBOARD_DIR = PROJECT_ROOT / "docs"

# Coordinate Reference Systems
CRS_WGS84 = "EPSG:4326"
CRS_UTM19S = "EPSG:32719"  # Metric projection for Cochabamba (UTM Zone 19 South)

# Core Spatial Bounding Boxes (west, south, east, north) in EPSG:4326
BBOX_COCHABAMBA_METRO = (-66.30, -17.52, -66.04, -17.24)
BBOX_TUNARI_CATCHMENTS = (-66.28, -17.39, -66.06, -17.24)
BBOX_VALLEY_FLOOR = (-66.26, -17.49, -66.08, -17.34)
BBOX_REGIONAL_UH7 = (-66.54, -17.87, -65.57, -17.18)

# GAMC Official WMS Proxy Endpoint & Keys
GAMC_WMS_ENDPOINT = "https://serviciosgamc.cochabamba.bo/api/gs/wms"
GAMC_KEYS = {
    "master": "1b2cc0dd523c886abcc11bcca8c0ca3758a548c35b2983bb",
    "project_1_microclimas": "1a3d2d9c6e1d6a94062d11a9021a48b24ae0e05e8183e9d8",
    "project_2_sar_cuencas": "15a5f168e26bd9270fc975b90aa09339b1706c9c8b290a6f",
    "project_3_incendios": "8da30122933ced2174ebe3e8b03198731d9cae6dc3230d32",
    "project_4_agro": "37f574a3292eafd287024269399aafa51b7cf55932603e2f",
    "project_5_distrital": "49ad041b9792482a8e3413e045a05520496a048030182e0d",
}

GAMC_SERVICES = {
    "cuencas_uh8": "4499e961-2b2e-4cf3-84dd-30789c31ec96",
    "cuencas_uh7": "fb368617-f2fd-43e8-867a-4456364efb52",
    "cuencas_influencia": "02ddf5a6-4d80-4ed3-8c73-b531b0574e81",
    "drenaje_influencia": "d4cea6e3-fc7f-482a-94ad-bd377df78886",
    "cota_2750": "297cefa4-0832-42bb-a98e-2cbea989fd9d",
    "limite_distritos": "7eb13092-bf0e-493b-aae6-03c43eedda2c",
    "emergencias": "e105a6ed-74bb-41a5-8c85-9360711ddf69",
    "periurbanos": "c52066a1-32fd-4925-81e0-c2dcb8f4238f",
    "limite_urbano": "fd77d463-9729-4c66-b686-23dccbb4ab8f",
    "areas_verdes": "47360ddc-e35f-4ece-a995-59e90eb79cc6",
    "poblacion_manzanas": "194a02a0-a73a-48c1-a260-82847c5c905d",
    "areas_equipamiento": "97a589fe-595e-45dd-91d4-38524877f1ed",
    "unidades_educativas": "7655ba3d-5d9e-44ff-bf65-26f81f83d7ec",
    "centros_salud": "e40fa280-f649-4614-9526-1b3dcce596b3",
    "limite_cercado": "6d93e1ac-8aa3-4b4c-865c-48c9af4f4afe",
}

# Epistemological & Physical Validity Thresholds
EPISTEMOLOGICAL_RULES = {
    "dem_source": "FABDEM V1-2 (1 arc-sec ~30m bare-earth DTM, Hawker et al. 2022)",
    "dem_min_resolvable_scale_m": 90.0,  # Minimum 3x3 grid cells (~90m) for reliable hydraulic gradient
    "sar_urban_exclusion_dB": -2.5,      # VV > -2.5 dB or inside Limite Urbano = dihedral double-bounce contamination
    "sar_layover_shadow_slope_deg": 35.0, # Slopes facing radar > incidence angle suffer layover
    "precip_min_resolvable_scale_km": 10.0, # GPM IMERG (0.1 deg ~11km) / ERA5-Land (9km) cannot resolve single <15 km2 micro-basins
    "non_tautological_buffer_m": 120.0,  # Hazard zones within 120m of mapped channel are flagged as 'Known Channel Proximity' and separated from novel off-channel Avulsion / Sink hazards
    "melton_debris_flow_threshold": 0.30, # Rm = dH / sqrt(A) > 0.30 indicates debris-flow / mazamorra regime (Wilford et al. 2004)
}
