"""
Automated Scientific Consistency, Physical Bounds & Anti-Tautology Test Suite
=============================================================================
Verifies that all physical models, satellite remote sensing masks, GAMC municipal
datasets, non-tautological hazard zones, historical disaster backtests, and WebGIS
endpoints obey strict epistemological and physical constraints.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import geopandas as gpd
import tornado.testing

from src.app.server import compute_dynamic_basin_response, make_app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PROC = PROJECT_ROOT / "data" / "processed"
DOCS_DIR = PROJECT_ROOT / "docs"


class TestScientificConsistencyAndRigor(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.terrain_sum = json.loads(
            (DATA_PROC / "terrain_physics" / "terrain_physics_summary.json").read_text(
                encoding="utf-8"
            )
        )
        cls.sar_sum = json.loads(
            (DATA_PROC / "sar_analysis" / "sar_dielectric_summary.json").read_text(
                encoding="utf-8"
            )
        )
        cls.hydro_data = json.loads(
            (
                DATA_PROC / "antecedent_forecast" / "basin_antecedent_forecasts.json"
            ).read_text(encoding="utf-8")
        )
        cls.hazard_sum = json.loads(
            (DATA_PROC / "hazard_zones" / "hazard_synthesis_summary.json").read_text(
                encoding="utf-8"
            )
        )
        cls.val_report = json.loads(
            (DATA_PROC / "validation_audit_report.json").read_text(encoding="utf-8")
        )

    def test_01_dsm_vs_fabdem_epistemological_proof(self) -> None:
        """Verify that Copernicus GLO-30 DSM exhibits severe riparian positive bias removed by FABDEM."""
        proof = self.terrain_sum["dsm_vs_fabdem_proof"]
        self.assertGreater(
            proof["channel_corridor_p90_delta_z_m"],
            6.0,
            "Riparian 90th-percentile DSM building/tree bias must exceed +6.0m",
        )
        self.assertGreater(
            proof["false_dsm_dams_along_channels_count"],
            5000,
            "DSM must introduce thousands of false dam pixels (>3m) along channels",
        )
        self.assertGreater(
            proof["true_bare_earth_sink_area_ha"],
            proof["false_dsm_sink_area_ha"],
            "FABDEM bare-earth valley sinks must exceed artificial DSM street-wall sinks",
        )

    def test_02_sar_urban_exclusion_and_cota2750_validity(self) -> None:
        """Verify that SAR is noisy in urban Cochabamba (double-bounce) but sensitive to wetting above Cota 2750m."""
        urb = self.sar_sum["urban_vs_natural_proof"]["urban_builtup_domain"]
        tun = self.sar_sum["urban_vs_natural_proof"][
            "upper_tunari_watersheds_above_cota2750"
        ]

        # Urban backscatter must be dominated by corner reflections and show <0.4 dB seasonal signal
        self.assertGreater(urb["double_bounce_contaminated_fraction"], 0.45)
        self.assertLess(abs(urb["cband_seasonal_dynamic_range_db"]), 0.40)

        # Upper Tunari (>2750m) must show positive seasonal wetting (> +1.0 dB mean, > +5.0 dB P90)
        self.assertGreater(tun["cband_seasonal_dynamic_range_db"], 1.0)
        self.assertGreater(tun["cband_p90_dynamic_range_db"], 5.0)

        # Dual-orbit fusion must reduce steep-slope layover loss from >8% down to <2.5%
        self.assertGreater(tun["single_orbit_layover_fraction_desc"], 0.08)
        self.assertLess(tun["unrecoverable_cliff_fraction_after_dual_orbit"], 0.025)

    def test_03_anti_tautology_strict_off_channel_separation(self) -> None:
        """Verify that 100% of novel PALEO-* corridors, SINK-* bowls, and flagged Manzanas are >120m from rivers."""
        paleo_gdf = gpd.read_file(
            DATA_PROC / "terrain_physics" / "off_channel_paleochannel_corridors.geojson"
        )
        sinks_gdf = gpd.read_file(
            DATA_PROC / "terrain_physics" / "off_channel_pluvial_sinks.geojson"
        )
        manz_gdf = gpd.read_file(
            DATA_PROC / "hazard_zones" / "non_obvious_high_risk_manzanas.geojson"
        )

        self.assertEqual(len(paleo_gdf), 45)
        self.assertEqual(len(sinks_gdf), 45)
        self.assertGreater(float(paleo_gdf["mean_distance_from_mapped_river_m"].min()), 120.0)
        self.assertGreater(float(sinks_gdf["mean_distance_from_mapped_river_m"].min()), 120.0)
        self.assertGreater(float(manz_gdf["dist_to_mapped_channel_m"].min()), 120.0)

        # Verify total off-channel exposed population & exclusion of tautological channel buffer
        nov = self.hazard_sum["non_obvious_off_channel_discoveries"]
        excl = self.hazard_sum["excluded_tautological_channel_buffer"]
        self.assertEqual(nov["total_off_channel_exposed_manzanas"], 693)
        self.assertEqual(nov["total_off_channel_exposed_population"], 61833)
        self.assertEqual(excl["manzanas_near_channel_excluded"], 5155)

    def test_04_precipitation_scale_and_historical_taquina_backtests(self) -> None:
        """Verify precipitation scale limits and multi-day pre-conditioning lead time on 2018 & 2020 disasters."""
        ab3 = self.val_report["epistemological_ablations"][
            "ablation_3_precipitation_spatial_temporal_scale"
        ]
        self.assertEqual(ab3["watersheds_smaller_than_single_imerg_pixel"], "22/23")
        self.assertLess(ab3["tunari_kirpich_tc_median_minutes"], 45.0)

        bt18 = self.val_report["historical_disaster_backtests"][
            "historical_2018_02_06_taquina"
        ]["taquina_basin_metrics"]
        bt20 = self.val_report["historical_disaster_backtests"][
            "historical_2020_02_21_taquina"
        ]["taquina_basin_metrics"]

        # Both historical disasters must be flagged RED_CRITICAL_PRECONDITIONED at least 7 days prior
        self.assertEqual(bt18["alert_tier"], "RED_CRITICAL_PRECONDITIONED")
        self.assertEqual(bt20["alert_tier"], "RED_CRITICAL_PRECONDITIONED")
        self.assertGreaterEqual(bt18["lead_time_red_critical_days"], 7)
        self.assertGreaterEqual(bt20["lead_time_red_critical_days"], 7)

        # Soil storage S(t) must collapse by >60% and P_crit must drop from 48.7 mm/hr to <22 mm/hr
        self.assertLess(bt18["storage_collapse_pct"], -60.0)
        self.assertLess(bt20["storage_collapse_pct"], -60.0)
        self.assertLess(bt18["event_P_crit_1hr_mm"], 22.0)
        self.assertLess(bt20["event_P_crit_1hr_mm"], 22.0)
        self.assertGreaterEqual(bt18["debris_bulking_factor_BF"], 1.60)
        self.assertGreaterEqual(bt20["debris_bulking_factor_BF"], 1.60)

    def test_05_dynamic_storm_simulator_and_deliverables(self) -> None:
        """Verify monotonic storm response physics and existence of all figures and WebGIS artifacts."""
        taq_dry = next(
            b
            for b in self.hydro_data["scenarios"]["benchmark_dry_2026_08_03"]
            if b["basin_name"] == "C. Taquiña"
        )
        taq_18 = next(
            b
            for b in self.hydro_data["scenarios"]["historical_2018_02_06_taquina"]
            if b["basin_name"] == "C. Taquiña"
        )

        # A moderate 23 mm/hr storm must NOT trigger overflow in dry winter, but MUST trigger in Feb 2018
        res_dry = compute_dynamic_basin_response(taq_dry, 23.0)
        res_18 = compute_dynamic_basin_response(taq_18, 23.0)
        self.assertFalse(res_dry["apex_avulsion_triggered"])
        self.assertTrue(res_18["apex_avulsion_triggered"])
        self.assertGreater(
            res_18["simulated_bulked_peak_discharge_m3s"],
            2.5 * res_dry["simulated_bulked_peak_discharge_m3s"],
        )

        # Verify WebGIS HTML and all 5 figures exist
        self.assertTrue((DOCS_DIR / "index.html").exists())
        self.assertGreater((DOCS_DIR / "index.html").stat().st_size, 500_000)
        for fig_name in [
            "fig1_dsm_vs_fabdem_proof.png",
            "fig2_sar_epistemological_domains.png",
            "fig3_taquina_backtest_2018_2020_2026.png",
            "fig4_non_tautological_hazard_map.png",
            "fig5_district_exposure_and_critical_thresholds.png",
        ]:
            fig_path = DOCS_DIR / "figures" / fig_name
            self.assertTrue(fig_path.exists(), f"Missing figure {fig_name}")
            self.assertGreater(fig_path.stat().st_size, 100_000)


class TestEarlyWarningWebGisServerEndpoints(tornado.testing.AsyncHTTPTestCase):
    def get_app(self) -> tornado.web.Application:
        return make_app()

    def test_06_http_endpoints_and_rest_api(self) -> None:
        """Verify live HTTP WebGIS dashboard and REST API endpoints."""
        # 1. Health endpoint
        res_health = self.fetch("/api/v1/health")
        self.assertEqual(res_health.code, 200)
        health_json = json.loads(res_health.body.decode("utf-8"))
        self.assertEqual(health_json["status"], "ok")

        # 2. Epistemology & Validation Audit endpoint
        res_epist = self.fetch("/api/v1/epistemology")
        self.assertEqual(res_epist.code, 200)
        epist_json = json.loads(res_epist.body.decode("utf-8"))
        self.assertEqual(epist_json["metadata"]["status"], "VERIFIED_RIGOROUS")

        # 3. Dynamic Basins Pre-Conditioning & Storm Simulator endpoint
        res_basins = self.fetch(
            "/api/v1/basins?scenario=historical_2018_02_06_taquina&storm_mm_hr=22.0"
        )
        self.assertEqual(res_basins.code, 200)
        basins_json = json.loads(res_basins.body.decode("utf-8"))
        self.assertEqual(basins_json["total_basins"], 23)
        self.assertIn("C. Taquiña", basins_json["triggered_basins"])

        # 4. Non-Tautological Off-Channel Hazards endpoint
        res_haz = self.fetch("/api/v1/non_tautological_hazards")
        self.assertEqual(res_haz.code, 200)
        haz_json = json.loads(res_haz.body.decode("utf-8"))
        self.assertEqual(
            haz_json["hazard_synthesis_summary"][
                "non_obvious_off_channel_discoveries"
            ]["total_off_channel_exposed_population"],
            61833,
        )

        # 5. Root HTML WebGIS Dashboard
        res_root = self.fetch("/")
        self.assertEqual(res_root.code, 200)
        self.assertIn(b"COCHABAMBA HYDRO-GEOMORPHIC PRE-CONDITIONING", res_root.body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
