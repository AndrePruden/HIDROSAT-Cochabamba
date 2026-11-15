"""
Cochabamba Hydro-Geomorphic Pre-Conditioning & Avulsion Early Warning Server
============================================================================
Provides both the interactive WebGIS dashboard (`GET /`) and a programmatic REST API:
- GET /api/v1/health
- GET /api/v1/epistemology
- GET /api/v1/basins?scenario=current_2026_11_15&storm_mm_hr=22.0
- GET /api/v1/non_tautological_hazards
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import tornado.ioloop
import tornado.web

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PROC = PROJECT_ROOT / "data" / "processed"
DOCS_DIR = PROJECT_ROOT / "docs"


def compute_dynamic_basin_response(
    basin_record: dict[str, Any], storm_mm_hr: float
) -> dict[str, Any]:
    """Evaluate SCS-CN runoff + Iverson debris bulking for a given 1-hr storm depth."""
    ia = float(basin_record["initial_abstraction_ia_mm"])
    s = float(basin_record["remaining_soil_storage_s_mm"])
    bf = float(basin_record["debris_bulking_factor_bf"])
    area = max(float(basin_record["area_km2"]), 0.5)
    tc_hr = max(float(basin_record["tc_kirpich_min"]) / 60.0, 0.15)
    tp_hr = 0.6 * tc_hr + 0.5 * 1.0
    q_cap = max(float(basin_record["apex_channel_capacity_m3s"]), 0.1)

    q_runoff_mm = ((storm_mm_hr - ia) ** 2) / (storm_mm_hr - ia + s) if storm_mm_hr > ia else 0.0
    qp_bulked_m3s = bf * (0.208 * area * q_runoff_mm) / tp_hr
    exceedance_ratio = qp_bulked_m3s / q_cap

    return {
        **basin_record,
        "simulated_storm_1hr_mm": round(storm_mm_hr, 1),
        "simulated_clear_runoff_mm": round(q_runoff_mm, 2),
        "simulated_bulked_peak_discharge_m3s": round(qp_bulked_m3s, 2),
        "simulated_capacity_exceedance_ratio": round(exceedance_ratio, 3),
        "apex_avulsion_triggered": bool(
            storm_mm_hr >= float(basin_record["critical_1hr_rain_threshold_mm"])
            or exceedance_ratio >= 1.0
        ),
    }


class BaseJsonHandler(tornado.web.RequestHandler):
    def set_default_headers(self) -> None:
        self.set_header("Content-Type", "application/json; charset=utf-8")
        self.set_header("Access-Control-Allow-Origin", "*")

    def write_json(self, payload: dict[str, Any], status: int = 200) -> None:
        self.set_status(status)
        self.write(json.dumps(payload, indent=2, ensure_ascii=False))


class HealthHandler(BaseJsonHandler):
    def get(self) -> None:
        self.write_json(
            {
                "status": "ok",
                "system": "Cochabamba Flood & Mazamorra Pre-Conditioning Early Warning System",
                "scientific_mode": "Multi-Day Antecedent Pre-Conditioning & Non-Tautological Off-Channel Hazard Discovery",
            }
        )


class EpistemologyHandler(BaseJsonHandler):
    def get(self) -> None:
        report = json.loads(
            (DATA_PROC / "validation_audit_report.json").read_text(encoding="utf-8")
        )
        self.write_json(report)


class BasinsForecastHandler(BaseJsonHandler):
    def get(self) -> None:
        hydro = json.loads(
            (DATA_PROC / "antecedent_forecast" / "basin_antecedent_forecasts.json").read_text(
                encoding="utf-8"
            )
        )
        scenarios = hydro["scenarios"]
        sc_key = self.get_argument("scenario", "current_2026_11_15")
        if sc_key not in scenarios:
            self.write_json(
                {
                    "error": f"Unknown scenario '{sc_key}'",
                    "available_scenarios": list(scenarios.keys()),
                },
                status=400,
            )
            return

        storm_mm_hr = float(self.get_argument("storm_mm_hr", "22.0"))
        evaluated = [
            compute_dynamic_basin_response(b, storm_mm_hr) for b in scenarios[sc_key]
        ]
        triggered = [b["basin_name"] for b in evaluated if b["apex_avulsion_triggered"]]
        self.write_json(
            {
                "scenario": sc_key,
                "simulated_storm_1hr_mm": storm_mm_hr,
                "total_basins": len(evaluated),
                "triggered_basins_count": len(triggered),
                "triggered_basins": triggered,
                "basins": evaluated,
            }
        )


class NonTautologicalHazardsHandler(BaseJsonHandler):
    def get(self) -> None:
        haz_sum = json.loads(
            (DATA_PROC / "hazard_zones" / "hazard_synthesis_summary.json").read_text(
                encoding="utf-8"
            )
        )
        terrain_sum = json.loads(
            (DATA_PROC / "terrain_physics" / "terrain_physics_summary.json").read_text(
                encoding="utf-8"
            )
        )
        self.write_json(
            {
                "anti_tautology_policy": "All novel off-channel hazard polygons (PALEO-* and SINK-*) strictly exclude the trivial <=120m river/torrentera buffer.",
                "dsm_vs_fabdem_proof": terrain_sum["dsm_vs_fabdem_proof"],
                "hazard_synthesis_summary": haz_sum,
            }
        )


def make_app() -> tornado.web.Application:
    return tornado.web.Application(
        [
            (r"/api/v1/health", HealthHandler),
            (r"/api/v1/epistemology", EpistemologyHandler),
            (r"/api/v1/basins", BasinsForecastHandler),
            (r"/api/v1/non_tautological_hazards", NonTautologicalHazardsHandler),
            (
                r"/figures/(.*)",
                tornado.web.StaticFileHandler,
                {"path": str(DOCS_DIR / "figures")},
            ),
            (
                r"/(.*)",
                tornado.web.StaticFileHandler,
                {"path": str(DOCS_DIR), "default_filename": "index.html"},
            ),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Cochabamba Early Warning WebGIS Server")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind (default: 8765)")
    args = parser.parse_args()

    app = make_app()
    app.listen(args.port)
    print(f"[Early Warning Server] Listening on http://localhost:{args.port}")
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
