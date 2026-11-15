"""
Parser and cleaner for Gobierno Autónomo Municipal de Cochabamba (GAMC)
WMS/KML vector layers and static resource files.

Key scientific & engineering features:
1. Properly separates GeoServer KML label-placement <Point> nodes from true
   <Polygon> and <LineString> geometries inside <MultiGeometry>.
2. Extracts all HTML attribute tables embedded in KML <description> elements
   and casts numeric fields accurately.
3. Performs domain-specific classification of the 97 GAMC 'Emergencias' records,
   explicitly distinguishing anthropogenic channel/gutter obstructions and flood
   events from wet-season root-saturation treefalls (avoiding false flood labels).
"""
import html
import json
import os
import re
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Point, Polygon
from shapely.validation import make_valid

from src.config import CRS_UTM19S, CRS_WGS84, DATA_PROCESSED, DATA_RAW

ATTR_PATTERN = re.compile(
    r'atr-name">(.*?)</span>.*?atr-value">(.*?)</span>', re.DOTALL
)
PLACEMARK_PATTERN = re.compile(r"<Placemark[^>]*>(.*?)</Placemark>", re.DOTALL)
DESC_PATTERN = re.compile(r"<description>(.*?)</description>", re.DOTALL)
POLYGON_PATTERN = re.compile(r"<Polygon>(.*?)</Polygon>", re.DOTALL)
OUTER_RING_PATTERN = re.compile(
    r"<outerBoundaryIs>.*?<coordinates>(.*?)</coordinates>.*?</outerBoundaryIs>",
    re.DOTALL,
)
INNER_RING_PATTERN = re.compile(
    r"<innerBoundaryIs>.*?<coordinates>(.*?)</coordinates>.*?</innerBoundaryIs>",
    re.DOTALL,
)
LINESTRING_PATTERN = re.compile(
    r"<LineString>.*?<coordinates>(.*?)</coordinates>.*?</LineString>", re.DOTALL
)
POINT_PATTERN = re.compile(
    r"<Point>.*?<coordinates>(.*?)</coordinates>.*?</Point>", re.DOTALL
)


def _parse_coord_string(coord_str: str) -> List[Tuple[float, float]]:
    coords = []
    for token in coord_str.strip().split():
        parts = token.split(",")
        if len(parts) >= 2:
            coords.append((float(parts[0]), float(parts[1])))
    return coords


def _extract_geometry(placemark_xml: str):
    """
    Extract highest-dimension geometry from a GeoServer KML Placemark
    (Polygon > LineString > Point), ignoring label centroid Points when
    Polygon or LineString geometry is present.
    """
    poly_blocks = POLYGON_PATTERN.findall(placemark_xml)
    if poly_blocks:
        polys = []
        for pb in poly_blocks:
            outer_m = OUTER_RING_PATTERN.search(pb)
            if not outer_m:
                continue
            shell = _parse_coord_string(outer_m.group(1))
            if len(shell) < 3:
                continue
            holes = []
            for inner_str in INNER_RING_PATTERN.findall(pb):
                ring = _parse_coord_string(inner_str)
                if len(ring) >= 3:
                    holes.append(ring)
            try:
                p = Polygon(shell, holes)
                if not p.is_valid:
                    p = make_valid(p)
                if p.geom_type == "Polygon":
                    polys.append(p)
                elif p.geom_type == "MultiPolygon":
                    polys.extend(list(p.geoms))
            except Exception:
                continue
        if len(polys) == 1:
            return polys[0]
        elif len(polys) > 1:
            return MultiPolygon(polys)

    line_blocks = LINESTRING_PATTERN.findall(placemark_xml)
    if line_blocks:
        lines = []
        for lb in line_blocks:
            pts = _parse_coord_string(lb)
            if len(pts) >= 2:
                lines.append(LineString(pts))
        if len(lines) == 1:
            return lines[0]
        elif len(lines) > 1:
            return MultiLineString(lines)

    pt_blocks = POINT_PATTERN.findall(placemark_xml)
    if pt_blocks:
        pts = _parse_coord_string(pt_blocks[0])
        if pts:
            return Point(pts[0])

    return None


def _cast_value(val: str):
    val = val.strip()
    if val == "" or val.lower() == "null":
        return None
    try:
        if "." in val:
            return float(val)
        return int(val)
    except ValueError:
        return val


def parse_kml_layer(kml_path: Path, keep_codes_as_str: Tuple[str, ...] = ("cod", "num", "telf", "nivel_1", "nivel_2", "nivel_3", "nivel_4", "nivel_5", "nivel_6", "nivel_7", "nivel_8")) -> gpd.GeoDataFrame:
    """Parse a GeoServer KML file into a clean GeoDataFrame in EPSG:4326."""
    text = kml_path.read_text(encoding="utf-8", errors="replace")
    records = []
    geoms = []

    for pm in PLACEMARK_PATTERN.findall(text):
        geom = _extract_geometry(pm)
        if geom is None or geom.is_empty:
            continue
        desc_m = DESC_PATTERN.search(pm)
        attrs = {}
        if desc_m:
            unescaped = html.unescape(desc_m.group(1))
            for k, v in ATTR_PATTERN.findall(unescaped):
                k_clean = k.strip().lower().replace(" ", "_")
                v_clean = html.unescape(v).replace("\xa0", " ").strip()
                if k_clean in keep_codes_as_str:
                    attrs[k_clean] = v_clean
                else:
                    attrs[k_clean] = _cast_value(v_clean)
        records.append(attrs)
        geoms.append(geom)

    gdf = gpd.GeoDataFrame(records, geometry=geoms, crs=CRS_WGS84)
    return gdf


def classify_emergency_record(desc: str) -> Dict[str, str]:
    """
    Scientifically honest classification of GAMC UGR / EMAVRA emergency reports.
    Rather than falsely treating all 97 municipal emergency points as flood depth
    observations, we classify them by physical mechanism:
      1. ANTHROPOGENIC_DRAINAGE_OBSTRUCTION: Filling of canals with earth/trash,
         blocking gutters/cunetas with concrete/bricks, construction mud in storm drains.
      2. ACTIVE_FLOOD_OR_PIPE_INUNDATION: Direct flooding of avenues or houses.
      3. CONVECTIVE_STORM_TREE_HAZARD: Fallen/tilted trees during wet-season storms
         (indicator of root-zone saturation + wind gust + woody debris supply).
      4. OTHER_MUNICIPAL_REPORT: Public space or policy complaints.
    """
    d = (desc or "").upper()
    if any(w in d for w in ["TAPARON CON TIERRA EL CANAL", "DESEMBOCARON AGUA MEZCLADA CON LODO", "TAPANDO TODO EL PASO DEL AGUA", "CUNETA QUE ESTA SIENDO OBSTRUIDA", "ALCANTARILLA CUANDO LLUEVA"]):
        return {
            "hazard_category": "ANTHROPOGENIC_DRAINAGE_OBSTRUCTION",
            "hydrological_relevance": "Direct hydraulic constriction / blockage of channel or storm drain prior to rain",
            "is_flood_or_drainage_hazard": True,
        }
    if any(w in d for w in ["PLENA TORRENCIAL INUNDACIÓN", "INUNDACIONES DENTRO DE MI CASA", "INUNDACIÓN DE LA PLANTA BAJA"]):
        return {
            "hazard_category": "ACTIVE_FLOOD_OR_WATER_INGRESS",
            "hydrological_relevance": "Observed surface or sewer/pipe inundation impact on buildings/transport",
            "is_flood_or_drainage_hazard": True,
        }
    if "ARBOL" in d or "ÁRBOL" in d or "RAMAS" in d:
        return {
            "hazard_category": "CONVECTIVE_STORM_TREE_HAZARD",
            "hydrological_relevance": "Root-zone saturation windthrow & potential woody debris jam hazard near channels",
            "is_flood_or_drainage_hazard": False,
        }
    return {
        "hazard_category": "OTHER_MUNICIPAL_REPORT",
        "hydrological_relevance": "Non-hydrological citizen report (excluded from flood validation)",
        "is_flood_or_drainage_hazard": False,
    }


def process_all_gamc_layers() -> Dict[str, Dict]:
    """Parse all downloaded GAMC KML layers and save clean GeoJSONs + summary metadata."""
    out_dir = DATA_PROCESSED / "gamc"
    out_dir.mkdir(parents=True, exist_ok=True)
    kml_dir = DATA_RAW / "gamc_kml"

    summary = {}
    layers_to_parse = [
        "cuencas_influencia",
        "drenaje_influencia",
        "cuencas_uh7",
        "cuencas_uh8",
        "cota_2750",
        "periurbanos",
        "limite_distritos",
        "limite_urbano",
        "limite_cercado",
        "emergencias",
        "unidades_educativas",
        "centros_salud",
        "areas_verdes",
        "areas_equipamiento",
        "poblacion_manzanas",
    ]

    for name in layers_to_parse:
        kml_path = kml_dir / f"{name}.kml"
        if not kml_path.exists():
            continue
        gdf = parse_kml_layer(kml_path)

        # Compute accurate metric area / length in UTM 19S (EPSG:32719)
        gdf_utm = gdf.to_crs(CRS_UTM19S)
        geom_types = gdf.geometry.geom_type.unique().tolist()
        if any("Polygon" in gt for gt in geom_types):
            gdf["area_m2_utm"] = gdf_utm.geometry.area.round(2)
            gdf["area_km2_utm"] = (gdf_utm.geometry.area / 1e6).round(4)
        elif any("Line" in gt for gt in geom_types):
            gdf["length_m_utm"] = gdf_utm.geometry.length.round(2)

        if name == "emergencias" and "descripcion" in gdf.columns:
            classifications = gdf["descripcion"].apply(classify_emergency_record)
            gdf["hazard_category"] = [c["hazard_category"] for c in classifications]
            gdf["hydrological_relevance"] = [c["hydrological_relevance"] for c in classifications]
            gdf["is_flood_or_drainage_hazard"] = [c["is_flood_or_drainage_hazard"] for c in classifications]

        out_geojson = out_dir / f"{name}.geojson"
        gdf.to_file(out_geojson, driver="GeoJSON")
        summary[name] = {
            "feature_count": int(len(gdf)),
            "geom_types": geom_types,
            "columns": [c for c in gdf.columns if c != "geometry"],
            "bounds_wgs84": [round(float(x), 5) for x in gdf.total_bounds],
        }
        print(f"[GAMC Parser] {name:22s}: {len(gdf):6d} features -> {out_geojson.name}", flush=True)

    # Also inspect Red MONICA zip to document its exact contents (PM10 air quality)
    monica_zip = DATA_RAW / "red_monica.zip"
    if monica_zip.exists():
        monica_info = {}
        with zipfile.ZipFile(monica_zip) as z:
            for fname in z.namelist():
                with z.open(fname) as f:
                    df = pd.read_csv(f)
                    monica_info[fname] = {
                        "rows": int(len(df)),
                        "columns": df.columns.tolist(),
                        "date_min": str(df["fecha_medicion"].min()) if "fecha_medicion" in df else None,
                        "date_max": str(df["fecha_medicion"].max()) if "fecha_medicion" in df else None,
                        "scientific_note": "Contains PM10 particulate matter concentrations (ug/m3), NOT precipitation. Excluded from hydrological forcing to maintain strict scientific consistency.",
                    }
        summary["red_monica_audit"] = monica_info

    summary_path = out_dir / "gamc_catalog_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


if __name__ == "__main__":
    process_all_gamc_layers()
