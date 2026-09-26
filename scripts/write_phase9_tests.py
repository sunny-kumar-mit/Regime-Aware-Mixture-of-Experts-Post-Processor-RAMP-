"""Write backend/tests/unit/spatial/test_phase9_suite.py with 28 comprehensive unit tests.
"""
import os

os.makedirs("backend/tests/unit/spatial", exist_ok=True)

test_code = '''"""
Phase 9 Spatial Forecast Products & District Aggregation Test Suite
SIH26080 | 28 Comprehensive Unit Tests
MoES / NCMRWF
"""

import json
import os
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import box, Polygon

from ramp.main import app
from ml.spatial.grid import GridCell, SpatialGridEngine
from ml.spatial.validation import SpatialValidator
from ml.spatial.boundaries import AdministrativeBoundaryProvider, DistrictBoundary, compute_physical_area_km2
from ml.spatial.intersection import GridDistrictIntersectionEngine, IntersectionRecord
from ml.spatial.aggregation import DistrictAggregationEngine
from ml.spatial.products import DistrictForecastProduct, StateForecastProduct, NationalForecastSummary
from ml.spatial.risk import DistrictRiskClassifier, RiskClassificationRule
from ml.spatial.uncertainty import SpatialUncertaintyEngine
from ml.spatial.fss import FractionsSkillScoreService
from ml.spatial.export import GISExportService
from ml.spatial.registry import SpatialProductRegistry, SPATIAL_PRODUCT_VERSION
from ml.dataset.leakage_guard import LeakageGuard
from ml.operational.registry import OperationalModelRegistry

client = TestClient(app)


def _make_dummy_cell(
    grid_id: str = "GRID_21.000N_078.000E",
    lat: float = 21.0,
    lon: float = 78.0,
    rain: float = 25.0,
    p_rain: float = 0.90,
    p_heavy: float = 0.30,
    p_vh: float = 0.10,
    p_ext: float = 0.02,
    lead: int = 24,
    valid_time: str = "2026-07-15T00:00:00Z",
) -> GridCell:
    return GridCell(
        grid_id=grid_id,
        latitude=lat,
        longitude=lon,
        forecast_valid_time=valid_time,
        initialization_time="2026-07-14T00:00:00Z",
        lead_time_hours=lead,
        rainfall_prediction_mm=rain,
        rainfall_probability=p_rain,
        heavy_probability=p_heavy,
        very_heavy_probability=p_vh,
        extreme_probability=p_ext,
        regime="ACTIVE_MONSOON",
        regime_probabilities={"ACTIVE_MONSOON": 0.85, "TRANSITION_OTHER": 0.15},
        uncertainty=0.12,
        data_mode="SYNTHETIC_DEMO",
        model_version="ramp_v1.0.0",
        raw_nwp_rainfall_mm=rain * 0.85,
        global_ml_rainfall_mm=rain * 0.95,
    )


# 1. Grid validation
def test_grid_validation():
    valid_cell = _make_dummy_cell()
    passed, errs = SpatialValidator.validate_grid_cell(valid_cell)
    assert passed
    assert len(errs) == 0

    # Test out of bounds latitude
    invalid_cell = _make_dummy_cell(lat=45.0)
    passed, errs = SpatialValidator.validate_grid_cell(invalid_cell)
    assert not passed
    assert any("Latitude" in e for e in errs)

    # Test negative rainfall
    neg_cell = _make_dummy_cell(rain=-5.0)
    passed, errs = SpatialValidator.validate_grid_cell(neg_cell)
    assert not passed
    assert any("Negative rainfall" in e for e in errs)


# 2. Duplicate grid detection
def test_duplicate_grid_detection():
    c1 = _make_dummy_cell(grid_id="GRID_DUP", lat=21.0, lon=78.0, valid_time="2026-07-15T00:00:00Z", lead=24)
    c2 = _make_dummy_cell(grid_id="GRID_DUP", lat=21.0, lon=78.0, valid_time="2026-07-15T00:00:00Z", lead=24)
    res = SpatialValidator.validate_grid_collection([c1, c2])
    assert not res["passed"]
    assert res["invalid_cells"] > 0


# 3. Probability monotonicity
def test_probability_monotonicity():
    # Monotonicity violation: P(Heavy) > P(Rain)
    bad_prob_cell = _make_dummy_cell(p_rain=0.20, p_heavy=0.50)
    passed, errs = SpatialValidator.validate_grid_cell(bad_prob_cell)
    assert not passed
    assert any("Monotonicity violation" in e for e in errs)


# 4. CRS validation
def test_crs_validation():
    bp = AdministrativeBoundaryProvider()
    assert bp.geographic_crs == "EPSG:4326"
    assert "EPSG:7755" in bp.projected_crs or "Albers" in bp.projected_crs


# 5. Boundary loading
def test_boundary_loading():
    bp = AdministrativeBoundaryProvider()
    districts = bp.list_districts()
    assert len(districts) >= 15
    nagpur = bp.get_district("NAGPUR")
    assert nagpur is not None
    assert nagpur.state_name == "Maharashtra"
    assert nagpur.area_km2 > 5000.0  # Physical area in km2


# 6. Grid/boundary intersection
def test_grid_boundary_intersection():
    bp = AdministrativeBoundaryProvider()
    nagpur = bp.get_district("NAGPUR")
    assert nagpur is not None
    cell = _make_dummy_cell(lat=21.25, lon=78.75)  # Inside Nagpur bounds [78.4, 20.8, 79.5, 21.8]
    recs = GridDistrictIntersectionEngine.intersect_district_with_cells(nagpur, [cell])
    assert len(recs) == 1
    assert recs[0].district_id == "NAGPUR"
    assert recs[0].intersection_area_km2 > 0.0


# 7. Intersection fractions
def test_intersection_fractions():
    bp = AdministrativeBoundaryProvider()
    nagpur = bp.get_district("NAGPUR")
    assert nagpur is not None
    cell = _make_dummy_cell(lat=21.25, lon=78.75)
    recs = GridDistrictIntersectionEngine.intersect_district_with_cells(nagpur, [cell])
    rec = recs[0]
    assert 0.0 <= rec.intersection_fraction <= 1.0
    assert 0.0 <= rec.district_coverage_fraction <= 1.0


# 8. Area-weighted aggregation
def test_area_weighted_aggregation():
    bp = AdministrativeBoundaryProvider()
    district = bp.get_district("NAGPUR")
    assert district is not None

    # Two cells with different weights and rainfalls
    c1 = _make_dummy_cell(grid_id="C1", lat=21.0, lon=78.5, rain=10.0)
    c2 = _make_dummy_cell(grid_id="C2", lat=21.25, lon=78.75, rain=50.0)

    # Mock intersection records with explicit areas
    rec1 = IntersectionRecord("C1", "NAGPUR", "MH", 200.0, 0.5, 0.02, c1)
    rec2 = IntersectionRecord("C2", "NAGPUR", "MH", 800.0, 1.0, 0.08, c2)

    agg = DistrictAggregationEngine()
    prod = agg.aggregate_district(district, [rec1, rec2], aggregation_method="AREA_WEIGHTED")

    # Weighted mean: (200*10 + 800*50) / 1000 = (2000 + 40000) / 1000 = 42.0 mm
    # Simple mean would be (10 + 50) / 2 = 30.0 mm
    assert np.isclose(prod.rainfall_mm, 42.0, atol=0.1)
    assert prod.rainfall_mm != 30.0  # Proves it is not simple mean!


# 9. Missing grid cells handling
def test_missing_grid_cells_handling():
    bp = AdministrativeBoundaryProvider()
    district = bp.get_district("NAGPUR")
    assert district is not None

    c_valid = _make_dummy_cell(grid_id="C_VAL", rain=20.0)
    c_nan = _make_dummy_cell(grid_id="C_NAN", rain=float("nan"))
    rec_val = IntersectionRecord("C_VAL", "NAGPUR", "MH", 500.0, 1.0, 0.05, c_valid)
    rec_nan = IntersectionRecord("C_NAN", "NAGPUR", "MH", 500.0, 1.0, 0.05, c_nan)

    agg = DistrictAggregationEngine()
    prod = agg.aggregate_district(district, [rec_val, rec_nan])
    assert prod.valid_grid_cells == 1
    assert prod.total_grid_cells == 2
    assert np.isclose(prod.rainfall_mm, 20.0)


# 10. Coverage calculation
def test_coverage_calculation():
    bp = AdministrativeBoundaryProvider()
    district = bp.get_district("NAGPUR")
    assert district is not None

    c1 = _make_dummy_cell(rain=20.0)
    rec1 = IntersectionRecord("C1", "NAGPUR", "MH", 1000.0, 1.0, 0.1, c1)
    agg = DistrictAggregationEngine()
    prod = agg.aggregate_district(district, [rec1])
    expected_cov = min(1.0, 1000.0 / district.area_km2)
    assert np.isclose(prod.coverage_fraction, expected_cov, atol=0.01)


# 11. District statistics
def test_district_statistics():
    bp = AdministrativeBoundaryProvider()
    district = bp.get_district("NAGPUR")
    assert district is not None

    rains = [10.0, 20.0, 30.0, 80.0, 150.0]
    recs = []
    for idx, r in enumerate(rains):
        c = _make_dummy_cell(grid_id=f"C_{idx}", rain=r)
        recs.append(IntersectionRecord(f"C_{idx}", "NAGPUR", "MH", 200.0, 0.5, 0.02, c))

    agg = DistrictAggregationEngine()
    prod = agg.aggregate_district(district, recs)
    assert prod.min_rainfall_mm == 10.0
    assert prod.max_rainfall_mm == 150.0
    assert prod.median_rainfall_mm == 30.0
    assert prod.p95_rainfall_mm >= prod.median_rainfall_mm


# 12. Hotspot detection
def test_hotspot_detection():
    bp = AdministrativeBoundaryProvider()
    district = bp.get_district("NAGPUR")
    assert district is not None

    c1 = _make_dummy_cell(grid_id="C1", lat=21.0, lon=78.5, rain=15.0)
    c2 = _make_dummy_cell(grid_id="C2", lat=21.5, lon=78.8, rain=210.0)  # Extreme convective burst!

    rec1 = IntersectionRecord("C1", "NAGPUR", "MH", 500.0, 1.0, 0.05, c1)
    rec2 = IntersectionRecord("C2", "NAGPUR", "MH", 500.0, 1.0, 0.05, c2)

    agg = DistrictAggregationEngine()
    prod = agg.aggregate_district(district, [rec1, rec2])

    assert prod.hotspot_rainfall_mm == 210.0
    assert prod.hotspot_latitude == 21.5
    assert prod.hotspot_longitude == 78.8
    assert prod.hotspot_intensity > 1.5


# 13. Probability aggregation
def test_probability_aggregation():
    bp = AdministrativeBoundaryProvider()
    district = bp.get_district("NAGPUR")
    assert district is not None

    c1 = _make_dummy_cell(p_rain=0.90, p_heavy=0.40, p_vh=0.20, p_ext=0.05)
    c2 = _make_dummy_cell(p_rain=0.80, p_heavy=0.30, p_vh=0.10, p_ext=0.02)
    rec1 = IntersectionRecord("C1", "NAGPUR", "MH", 500.0, 1.0, 0.05, c1)
    rec2 = IntersectionRecord("C2", "NAGPUR", "MH", 500.0, 1.0, 0.05, c2)

    agg = DistrictAggregationEngine()
    prod = agg.aggregate_district(district, [rec1, rec2])

    assert prod.rain_probability >= prod.heavy_probability
    assert prod.heavy_probability >= prod.very_heavy_probability
    assert prod.very_heavy_probability >= prod.extreme_probability


# 14. State aggregation
def test_state_aggregation():
    res = client.get("/api/spatial/states?lead_hours=24")
    assert res.status_code == 200
    data = res.json()
    assert "states" in data
    assert len(data["states"]) > 0
    mh = next((s for s in data["states"] if s["state_id"] == "MH"), None)
    assert mh is not None
    assert mh["district_count"] >= 4
    assert mh["area_weighted_rainfall_mm"] >= 0.0


# 15. Risk classification
def test_risk_classification():
    clf = DistrictRiskClassifier()
    # Extreme risk test
    ext_res = clf.classify_district(rainfall_mm=215.0, heavy_prob=0.90, very_heavy_prob=0.70, extreme_prob=0.45)
    assert ext_res["risk_category"] == "EXTREME_RAINFALL"
    assert ext_res["color_hex"] == "#990000"

    # Normal risk test
    norm_res = clf.classify_district(rainfall_mm=5.0, heavy_prob=0.05, very_heavy_prob=0.01, extreme_prob=0.0)
    assert norm_res["risk_category"] == "NORMAL"


# 16. Provenance
def test_provenance():
    registry = SpatialProductRegistry()
    manifest = registry.record_spatial_run(
        dataset_id="test_ds",
        dataset_version="v0.3.0",
        model_version="ramp_v1.0.0",
        boundary_version="v1.0.0",
        lead_time_hours=24,
        valid_time="2026-07-15T00:00:00Z",
        aggregation_method="AREA_WEIGHTED",
        total_districts=21,
        total_cells=360,
    )
    assert "run_id" in manifest
    assert manifest["product_version"] == SPATIAL_PRODUCT_VERSION
    assert os.path.exists(os.path.join(registry.audit_dir, f"{manifest['run_id']}.json"))


# 17. Versioning
def test_versioning():
    assert SPATIAL_PRODUCT_VERSION == "spatial_product_v1.0.0"


# 18. Cache invalidation
def test_cache_invalidation():
    k1 = SpatialProductRegistry.build_cache_key("v1", "ramp_v1", "b1", "2026-07-15T00:00:00Z", 24, "AREA_WEIGHTED")
    k2 = SpatialProductRegistry.build_cache_key("v1", "ramp_v1", "b1", "2026-07-15T00:00:00Z", 48, "AREA_WEIGHTED")
    assert k1 != k2


# 19. GeoJSON export
def test_geojson_export(tmp_path):
    exporter = GISExportService(export_dir=str(tmp_path))
    bp = AdministrativeBoundaryProvider()
    d = bp.get_district("NAGPUR")
    assert d is not None
    c = _make_dummy_cell()
    rec = IntersectionRecord("C1", "NAGPUR", "MH", 500.0, 1.0, 0.05, c)
    agg = DistrictAggregationEngine()
    prod = agg.aggregate_district(d, [rec])
    path = exporter.export_district_forecast_geojson([prod], bp, filename="test.geojson")
    assert os.path.exists(path)
    with open(path, "r", encoding="utf-8") as f:
        geo = json.load(f)
    assert geo["type"] == "FeatureCollection"
    assert len(geo["features"]) == 1


# 20. CSV export
def test_csv_export(tmp_path):
    exporter = GISExportService(export_dir=str(tmp_path))
    bp = AdministrativeBoundaryProvider()
    d = bp.get_district("NAGPUR")
    assert d is not None
    c = _make_dummy_cell()
    rec = IntersectionRecord("C1", "NAGPUR", "MH", 500.0, 1.0, 0.05, c)
    agg = DistrictAggregationEngine()
    prod = agg.aggregate_district(d, [rec])
    path = exporter.export_district_csv([prod], filename="test.csv")
    assert os.path.exists(path)
    df = pd.read_csv(path)
    assert len(df) == 1
    assert "rainfall_mm" in df.columns


# 21. API contracts
def test_api_contracts():
    res_status = client.get("/api/spatial/status")
    assert res_status.status_code == 200
    assert res_status.json()["status"] == "OPERATIONAL"

    res_dist = client.get("/api/spatial/districts?lead_hours=24")
    assert res_dist.status_code == 200
    assert "districts" in res_dist.json()

    res_sum = client.get("/api/spatial/summary?lead_hours=24")
    assert res_sum.status_code == 200
    assert "total_districts_evaluated" in res_sum.json()

    res_geo = client.get("/api/spatial/geojson?layer=districts&lead_hours=24")
    assert res_geo.status_code == 200
    assert res_geo.json()["type"] == "FeatureCollection"

    res_exp = client.get("/api/spatial/export?lead_hours=24")
    assert res_exp.status_code == 200
    assert res_exp.json()["status"] == "SUCCESS"


# 22. FSS calculation
def test_fss_calculation():
    grid_f = np.array([[0, 0, 0], [0, 50, 0], [0, 0, 0]], dtype=float)
    grid_o = np.array([[0, 0, 0], [0, 50, 0], [0, 0, 0]], dtype=float)
    res = FractionsSkillScoreService.compute_fss_single(grid_f, grid_o, threshold=25.0, window_size=3)
    assert np.isclose(res["fss"], 1.0)
    assert res["status"] == "PASS"


# 23. FSS sample insufficiency handling
def test_fss_sample_insufficiency_handling():
    # Only 2 points, insufficient for 2D spatial filtering
    df_small = pd.DataFrame([
        {"latitude": 21.0, "longitude": 78.0, "ramp_pred": 10.0, "observed_rainfall_mm": 12.0},
        {"latitude": 21.25, "longitude": 78.25, "ramp_pred": 15.0, "observed_rainfall_mm": 18.0},
    ])
    res = FractionsSkillScoreService.evaluate_spatial_fss(df_small)
    assert res["status"] == "SAMPLE_LIMITED"


# 24. Synthetic-data honesty
def test_synthetic_data_honesty():
    res = client.get("/api/spatial/status")
    assert res.status_code == 200
    assert res.json()["data_mode"] == "SYNTHETIC_DEMO"
    assert "SYNTHETIC DEMONSTRATION" in res.json()["banner"]


# 25. Phase 8 compatibility
def test_phase8_compatibility():
    reg = OperationalModelRegistry()
    assert reg.is_locked("ramp_v1.0.0")
    assert reg.is_locked("extreme_prob_v1.0.0")


# 26. Leakage protection
def test_leakage_protection():
    features_clean = ["air_temperature_2m", "relative_humidity", "wind_u_850", "pressure_surface"]
    features_leaked = ["air_temperature_2m", "future_observed_rainfall", "observed_regime_label"]
    passed_clean, _ = LeakageGuard.audit_real_data_features(features_clean)
    assert passed_clean
    passed_leaked, errs = LeakageGuard.audit_real_data_features(features_leaked)
    assert not passed_leaked
    assert len(errs) >= 2


# 27. Lead-time handling
def test_lead_time_handling():
    for lead in [24, 48, 72, 96, 120]:
        res = client.get(f"/api/spatial/districts?lead_hours={lead}")
        assert res.status_code == 200
        assert res.json()["lead_time_hours"] == lead


# 28. Model version protection
def test_model_version_protection():
    # Ensure frozen models are not modified
    op_reg = OperationalModelRegistry()
    ramp_entry = op_reg.get_model_entry("ramp_v1.0.0")
    assert ramp_entry is not None
    assert ramp_entry.status == "FROZEN"
    assert ramp_entry.version_id == "ramp_v1.0.0"
'''

with open("backend/tests/unit/spatial/test_phase9_suite.py", "w", encoding="utf-8") as f:
    f.write(test_code)
print("Wrote backend/tests/unit/spatial/test_phase9_suite.py successfully!")
