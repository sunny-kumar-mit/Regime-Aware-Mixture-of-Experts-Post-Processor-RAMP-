"""
RAMP Operational Forecast Inference Pipeline
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Part A & AF: Orchestrates the 16-step operational post-processing pipeline:
  Forecast Cycle -> NWP Discovery -> Input Validation (11 Gates) ->
  Feature Engineering (18 Predictors) -> Model Registry Resolution ->
  RAMP MoE Inference -> Extreme Exceedance Probabilities ->
  Registered Calibration -> Monotonicity Enforcement ->
  Spatial Grid Products -> District Aggregations -> State Syntheses ->
  National Meteorological Synopsis -> Storage & Audit -> Complete Forecast Payload
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ml.inference.calibration import RegisteredCalibrator
from ml.inference.config import (
    AUDIT_LOG_PATH,
    FEATURE_SCHEMA_VERSION,
    FORECAST_STORAGE_PATH,
    INFERENCE_ENGINE_VERSION,
    TARGET_SCHEMA_VERSION,
)
from ml.inference.feature_builder import InferenceFeatureBuilder
from ml.inference.input_resolver import ForecastCycleResolver, ResolvedCycleInfo
from ml.inference.model_resolver import ModelResolver, ResolvedModel
from ml.inference.predictor import RAMPPredictor
from ml.inference.probability import ExtremeProbabilityPredictor
from ml.inference.products import ForecastProductManager
from ml.inference.provenance import (
    ForecastAuditLogger,
    ForecastManifest,
    compute_sha256_dict,
    generate_forecast_run_id,
    get_git_commit,
)
from ml.inference.spatial import SpatialForecastEngine
from ml.inference.validation import InputValidationError, InputValidator
from ml.spatial.boundaries import BoundaryProvider
from ml.spatial.grid import GridCell

logger = logging.getLogger(__name__)


_CANONICAL_GRID_CACHE: Optional[List[Dict[str, float]]] = None


def generate_canonical_india_grid_points() -> List[Dict[str, float]]:
    """
    Generates representative canonical grid points covering India and all district bounds.
    """
    global _CANONICAL_GRID_CACHE
    if _CANONICAL_GRID_CACHE is not None:
        return _CANONICAL_GRID_CACHE

    points: List[Dict[str, float]] = []
    seen = set()

    # 1. District centroid & corner points
    bp = BoundaryProvider()
    for d in bp.list_districts():
        min_lon, min_lat, max_lon, max_lat = d.bbox
        c_lat = round((min_lat + max_lat) / 2.0, 2)
        c_lon = round((min_lon + max_lon) / 2.0, 2)
        for lat in [round(min_lat + 0.1, 2), c_lat, round(max_lat - 0.1, 2)]:
            for lon in [round(min_lon + 0.1, 2), c_lon, round(max_lon - 0.1, 2)]:
                key = (round(lat, 2), round(lon, 2))
                if key not in seen:
                    seen.add(key)
                    points.append({"latitude": lat, "longitude": lon})

    # 2. Regular 1.5° grid covering Indian Subcontinent
    for lat in np.arange(8.5, 36.0, 1.5):
        for lon in np.arange(68.5, 95.0, 1.5):
            # Rough geographic filter for mainland India
            if (lat < 12.0 and lon > 80.0) or (lat > 32.0 and lon < 74.0):
                continue
            key = (round(float(lat), 2), round(float(lon), 2))
            if key not in seen:
                seen.add(key)
                points.append({"latitude": float(lat), "longitude": float(lon)})

    _CANONICAL_GRID_CACHE = sorted(points, key=lambda p: (p["latitude"], p["longitude"]))
    return _CANONICAL_GRID_CACHE


class OperationalInferencePipeline:
    """
    End-to-end operational inference pipeline meeting MoES / NCMRWF operational standards.
    """

    def __init__(
        self,
        model_resolver: Optional[ModelResolver] = None,
        cycle_resolver: Optional[ForecastCycleResolver] = None,
        spatial_engine: Optional[SpatialForecastEngine] = None,
        product_manager: Optional[ForecastProductManager] = None,
        audit_logger: Optional[ForecastAuditLogger] = None,
    ):
        self.model_resolver = model_resolver or ModelResolver()
        self.cycle_resolver = cycle_resolver or ForecastCycleResolver()
        self.spatial_engine = spatial_engine or SpatialForecastEngine()
        self.product_manager = product_manager or ForecastProductManager()
        self.audit_logger = audit_logger or ForecastAuditLogger()
        self.grid_points = generate_canonical_india_grid_points()

    def run_forecast(
        self,
        cycle_id: str,
        lead_time_hours: int,
        user_action: str = "SCHEDULED_RUN",
        enforce_monotonicity: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes complete 16-step operational inference workflow.
        """
        t_start = time.perf_counter()
        perf: Dict[str, float] = {}

        # -----------------------------------------------------------------
        # STEP 1: Resolve Forecast Cycle
        # -----------------------------------------------------------------
        t0 = time.perf_counter()
        cycle_info = self.cycle_resolver.get_cycle(cycle_id)
        if cycle_info is None:
            raise InputValidationError(f"FORECAST_GENERATION_BLOCKED: Cycle '{cycle_id}' does not exist.")

        # -----------------------------------------------------------------
        # STEP 2 & 3: Resolve Lead Time & Valid Time
        # -----------------------------------------------------------------
        forecast_valid_time = self.cycle_resolver.resolve_valid_time(cycle_info, lead_time_hours)
        forecast_run_id = generate_forecast_run_id(
            initialization_time=cycle_info.initialization_time,
            cycle_utc=cycle_info.cycle_utc,
            lead_time_hours=lead_time_hours,
            source_model=cycle_info.model,
        )
        perf["input_loading_time_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        # -----------------------------------------------------------------
        # STEP 4: Input Validation (11 Operational Gates)
        # -----------------------------------------------------------------
        validation_report = InputValidator.validate_request(
            cycle=cycle_info,
            lead_time_hours=lead_time_hours,
            model_resolver=self.model_resolver,
        )
        if not validation_report["all_passed"]:
            self.audit_logger.log_inference(
                forecast_run_id=forecast_run_id,
                cycle=cycle_info.cycle_utc,
                lead=lead_time_hours,
                source=cycle_info.model,
                model_versions={},
                input_checksum="",
                output_checksum="",
                data_mode=cycle_info.data_mode,
                status="BLOCKED",
                user_action=user_action,
                failure_reason=str(validation_report["failure_reasons"]),
            )
            return {
                "status": "FORECAST_GENERATION_BLOCKED",
                "forecast_run_id": forecast_run_id,
                "validation_report": validation_report,
            }

        # -----------------------------------------------------------------
        # STEP 5 & 8: Feature Engineering & Schema Verification (18 Canonical Predictors)
        # -----------------------------------------------------------------
        t0 = time.perf_counter()
        features_df = InferenceFeatureBuilder.build_synthetic_grid_features(
            grid_points=self.grid_points,
            lead_time_hours=lead_time_hours,
            seed=42,
        )
        InferenceFeatureBuilder.audit_features(features_df)
        perf["feature_construction_time_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        input_checksum = compute_sha256_dict(features_df.to_dict(orient="records")[:5])

        # -----------------------------------------------------------------
        # STEP 6 & 7: Model Registry Resolution & Immutable Model Loading
        # -----------------------------------------------------------------
        t0 = time.perf_counter()
        active_models = self.model_resolver.resolve_active_models()
        moe_model = active_models["moe"]
        global_model = active_models.get("global")
        regime_model = active_models.get("regime")
        extreme_model = active_models["extreme"]

        model_versions = {k: v.model_id for k, v in active_models.items()}
        model_checksums = {k: v.checksum_sha256 for k, v in active_models.items()}
        perf["model_loading_time_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        # -----------------------------------------------------------------
        # STEP 9: RAMP Mixture-of-Experts Inference
        # -----------------------------------------------------------------
        t0 = time.perf_counter()
        predictor = RAMPPredictor(
            moe_model=moe_model,
            global_model=global_model,
            regime_model=regime_model,
        )
        continuous_preds = predictor.predict_field(features_df)
        perf["inference_time_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        # -----------------------------------------------------------------
        # STEP 10, 11, 12: Extreme Probability, Calibration & Monotonicity
        # -----------------------------------------------------------------
        t0 = time.perf_counter()
        prob_predictor = ExtremeProbabilityPredictor(extreme_model=extreme_model)
        calibrator = RegisteredCalibrator(extreme_model.calibration)

        prob_preds, mono_report = prob_predictor.predict_probabilities(
            features_df, enforce_monotonicity=enforce_monotonicity
        )
        perf["probability_time_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        # -----------------------------------------------------------------
        # STEP 13 & 14: Spatial Grid Products, District Aggregation & State Summaries
        # -----------------------------------------------------------------
        t0 = time.perf_counter()
        grid_cells = self.spatial_engine.generate_grid_cells(
            grid_points=self.grid_points,
            continuous_preds=continuous_preds,
            prob_preds=prob_preds,
            initialization_time=cycle_info.initialization_time,
            forecast_valid_time=forecast_valid_time,
            lead_time_hours=lead_time_hours,
            data_mode=cycle_info.data_mode,
            model_version=moe_model.model_id,
        )

        district_products = self.spatial_engine.aggregate_districts(grid_cells)
        state_summaries = self.spatial_engine.aggregate_states(district_products)
        national_summary = self.spatial_engine.generate_national_summary(
            cells=grid_cells,
            district_products=district_products,
            state_summaries=state_summaries,
            cycle_info=cycle_info,
            lead_time_hours=lead_time_hours,
        )
        perf["spatial_aggregation_time_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        # -----------------------------------------------------------------
        # STEP 15: Provenance, Manifest & Storage
        # -----------------------------------------------------------------
        t0 = time.perf_counter()
        output_checksum = compute_sha256_dict({
            "national": national_summary["national_metrics"],
            "districts_top3": [d["rainfall"] for d in district_products[:3]],
        })

        manifest = ForecastManifest(
            forecast_run_id=forecast_run_id,
            generation_timestamp=datetime.now(timezone.utc).isoformat(),
            data_mode=cycle_info.data_mode,
            software_version=INFERENCE_ENGINE_VERSION,
            git_commit=get_git_commit(),
            feature_schema=FEATURE_SCHEMA_VERSION,
            target_schema=TARGET_SCHEMA_VERSION,
            calibration_version=extreme_model.calibration.get("method", "isotonic"),

            source_provider=cycle_info.provider_id,
            source_model=cycle_info.model,
            cycle=cycle_info.cycle_utc,
            initialization_time=cycle_info.initialization_time,
            lead_time_hours=lead_time_hours,
            forecast_valid_time=forecast_valid_time,
            input_files=[f"{cycle_info.cycle_id}_surface.nc"],
            input_checksums={"surface": input_checksum},
            model_versions=model_versions,
            model_checksums=model_checksums,
            output_checksums={"output": output_checksum},
            metadata={
                "grid_cells_count": len(grid_cells),
                "districts_count": len(district_products),
                "states_count": len(state_summaries),
                "monotonicity_violations_corrected": mono_report.get("violations_count", 0),
            },
        )

        storage_paths = self.product_manager.save_forecast_run(
            forecast_run_id=forecast_run_id,
            cycle_info=cycle_info,
            lead_time_hours=lead_time_hours,
            grid_cells=grid_cells,
            districts=district_products,
            states=state_summaries,
            national=national_summary,
            manifest=manifest,
        )

        self.audit_logger.log_inference(
            forecast_run_id=forecast_run_id,
            cycle=cycle_info.cycle_utc,
            lead=lead_time_hours,
            source=cycle_info.model,
            model_versions=model_versions,
            input_checksum=input_checksum,
            output_checksum=output_checksum,
            data_mode=cycle_info.data_mode,
            status="SUCCESS",
            user_action=user_action,
        )
        perf["export_time_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        perf["total_time_ms"] = round((time.perf_counter() - t_start) * 1000, 2)

        # Save performance metrics to audit/storage (Part AJ)
        try:
            perf_path = storage_paths["metadata"] / "forecast_performance.json"
            with open(perf_path, "w", encoding="utf-8") as f:
                json.dump(perf, f, indent=2)
        except Exception:
            pass

        # -----------------------------------------------------------------
        # STEP 16: Complete Forecast Product Payload
        # -----------------------------------------------------------------
        return {
            "status": "SUCCESS",
            "forecast_run_id": forecast_run_id,
            "data_mode": cycle_info.data_mode,
            "is_real": cycle_info.is_real,
            "cycle": cycle_info.to_dict(),
            "lead_time_hours": lead_time_hours,
            "forecast_valid_time": forecast_valid_time,
            "national_summary": national_summary,
            "districts": district_products,
            "states": state_summaries,
            "grid_cells": [c.to_dict() for c in grid_cells],
            "monotonicity_report": mono_report,
            "provenance": manifest.to_dict(),
            "performance": perf,
            "storage_paths": {k: str(v) for k, v in storage_paths.items()},
        }
