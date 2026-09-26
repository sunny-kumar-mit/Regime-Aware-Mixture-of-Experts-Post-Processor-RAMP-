"""
RAMP Spatial Verification Engine — Phase 10
SIH26080 | MoES / NCMRWF

Consumes Phase 9 spatial products.
Produces gridded verification, district-level errors, and spatial difference maps.
Does NOT alter or rewrite Phase 9 products.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class GridVerificationMetrics:
    n_grid_cells: int
    availability_status: str
    grid_rmse: Optional[float] = None
    grid_mae: Optional[float] = None
    grid_bias: Optional[float] = None
    grid_csi_rain: Optional[float] = None
    grid_pod_rain: Optional[float] = None
    grid_far_rain: Optional[float] = None
    data_mode: str = "SYNTHETIC_DEMO"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_grid_cells": self.n_grid_cells,
            "availability_status": self.availability_status,
            "grid_rmse": self.grid_rmse,
            "grid_mae": self.grid_mae,
            "grid_bias": self.grid_bias,
            "grid_csi_rain": self.grid_csi_rain,
            "grid_pod_rain": self.grid_pod_rain,
            "grid_far_rain": self.grid_far_rain,
            "data_mode": self.data_mode,
        }


@dataclass
class DistrictVerificationRecord:
    district_id: str
    district_name: str
    state_name: str
    n_valid_cells: int
    ramp_prediction_mm: float
    raw_nwp_mm: float
    global_ml_mm: float
    difference_ramp_nwp: float
    difference_ramp_globalml: float
    observed_mm: Optional[float] = None
    ramp_error_mm: Optional[float] = None
    nwp_error_mm: Optional[float] = None
    availability_status: str = "SYNTHETIC_DEMO"
    data_mode: str = "SYNTHETIC_DEMO"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "district_id": self.district_id,
            "district_name": self.district_name,
            "state_name": self.state_name,
            "n_valid_cells": self.n_valid_cells,
            "ramp_prediction_mm": self.ramp_prediction_mm,
            "raw_nwp_mm": self.raw_nwp_mm,
            "global_ml_mm": self.global_ml_mm,
            "difference_ramp_nwp": self.difference_ramp_nwp,
            "difference_ramp_globalml": self.difference_ramp_globalml,
            "observed_mm": self.observed_mm,
            "ramp_error_mm": self.ramp_error_mm,
            "nwp_error_mm": self.nwp_error_mm,
            "availability_status": self.availability_status,
            "data_mode": self.data_mode,
        }


class SpatialVerificationEngine:
    """
    Spatial verification layer consuming Phase 9 district/grid products.
    Returns difference maps, district errors, and hotspot verification.
    Real observation-based metrics return NOT_AVAILABLE when archives absent.
    """

    def __init__(self, data_mode: str = "SYNTHETIC_DEMO", random_seed: int = 42):
        self.data_mode = data_mode
        self.random_seed = random_seed

    def compute_grid_verification(
        self,
        grid_predictions_ramp: Optional[np.ndarray] = None,
        grid_observations: Optional[np.ndarray] = None,
        grid_predictions_nwp: Optional[np.ndarray] = None,
    ) -> GridVerificationMetrics:
        """
        Compute grid-level verification metrics.
        Returns NOT_AVAILABLE when observations absent.
        """
        if grid_observations is None:
            return GridVerificationMetrics(
                n_grid_cells=0,
                availability_status="NOT_AVAILABLE",
                data_mode=self.data_mode,
            )

        n = len(grid_observations)
        if n < 10:
            return GridVerificationMetrics(
                n_grid_cells=n,
                availability_status="SAMPLE_LIMITED",
                data_mode=self.data_mode,
            )

        r = grid_predictions_ramp - grid_observations
        grid_rmse = float(np.sqrt(np.mean(r ** 2)))
        grid_mae = float(np.mean(np.abs(r)))
        grid_bias = float(np.mean(r))

        obs_rain = grid_observations >= 0.1
        fcst_rain = grid_predictions_ramp >= 0.1
        h = int(np.sum(obs_rain & fcst_rain))
        ms = int(np.sum(obs_rain & ~fcst_rain))
        fa = int(np.sum(~obs_rain & fcst_rain))
        csi = h / (h + ms + fa) if (h + ms + fa) > 0 else None
        pod = h / (h + ms) if (h + ms) > 0 else None
        far = fa / (h + fa) if (h + fa) > 0 else None

        return GridVerificationMetrics(
            n_grid_cells=n,
            availability_status="AVAILABLE",
            grid_rmse=round(grid_rmse, 4),
            grid_mae=round(grid_mae, 4),
            grid_bias=round(grid_bias, 4),
            grid_csi_rain=round(csi, 4) if csi is not None else None,
            grid_pod_rain=round(pod, 4) if pod is not None else None,
            grid_far_rain=round(far, 4) if far is not None else None,
            data_mode=self.data_mode,
        )

    def compute_district_records(
        self,
        district_products: Optional[List[Dict[str, Any]]] = None,
    ) -> List[DistrictVerificationRecord]:
        """
        Generate district-level verification records from Phase 9 products.
        Real errors (ramp_error_mm) only computed when observed_mm available.
        """
        if district_products is None:
            return self._synthetic_district_records()

        records = []
        for dp in district_products:
            ramp = dp.get("rainfall_mm", 0.0)
            nwp = dp.get("raw_nwp_rainfall_mm", 0.0)
            gml = dp.get("global_ml_rainfall_mm", 0.0)
            obs = dp.get("observed_mm")

            records.append(DistrictVerificationRecord(
                district_id=dp.get("district_id", "UNKNOWN"),
                district_name=dp.get("district_name", "Unknown"),
                state_name=dp.get("state_name", "Unknown"),
                n_valid_cells=dp.get("valid_grid_cells", 0),
                ramp_prediction_mm=ramp,
                raw_nwp_mm=nwp,
                global_ml_mm=gml,
                difference_ramp_nwp=round(ramp - nwp, 4),
                difference_ramp_globalml=round(ramp - gml, 4),
                observed_mm=obs,
                ramp_error_mm=round(ramp - obs, 4) if obs is not None else None,
                nwp_error_mm=round(nwp - obs, 4) if obs is not None else None,
                availability_status="AVAILABLE" if obs is not None else "SYNTHETIC_DEMO",
                data_mode=self.data_mode,
            ))
        return records

    def _synthetic_district_records(self) -> List[DistrictVerificationRecord]:
        """Synthetic district records from Phase 9 canonical 21-district catalog."""
        rng = np.random.RandomState(self.random_seed)
        canonical = [
            ("MH-NAG", "Nagpur", "Maharashtra"),
            ("MH-PUN", "Pune", "Maharashtra"),
            ("MH-MUM", "Mumbai", "Maharashtra"),
            ("KA-BAN", "Bangalore Rural", "Karnataka"),
            ("KA-MYS", "Mysuru", "Karnataka"),
            ("KA-MNG", "Mangaluru", "Karnataka"),
            ("TN-CHE", "Chennai", "Tamil Nadu"),
            ("TN-MDD", "Madurai", "Tamil Nadu"),
            ("KL-THR", "Thiruvananthapuram", "Kerala"),
            ("KL-KCH", "Kochi", "Kerala"),
            ("GJ-AHM", "Ahmedabad", "Gujarat"),
            ("GJ-SUR", "Surat", "Gujarat"),
            ("MP-BHP", "Bhopal", "Madhya Pradesh"),
            ("MP-IND", "Indore", "Madhya Pradesh"),
            ("UP-LKN", "Lucknow", "Uttar Pradesh"),
            ("RJ-JYP", "Jaipur", "Rajasthan"),
            ("WB-KOL", "Kolkata", "West Bengal"),
            ("OR-BHU", "Bhubaneswar", "Odisha"),
            ("AP-VIZ", "Visakhapatnam", "Andhra Pradesh"),
            ("HR-GGN", "Gurugram", "Haryana"),
            ("AS-GUW", "Guwahati", "Assam"),
        ]

        records = []
        for did, dname, sname in canonical:
            nwp = float(np.abs(rng.exponential(12.0)))
            ramp = float(np.abs(nwp + rng.normal(-1.0, 3.0)))
            gml = float(np.abs(nwp + rng.normal(-0.5, 4.0)))

            records.append(DistrictVerificationRecord(
                district_id=did,
                district_name=dname,
                state_name=sname,
                n_valid_cells=int(rng.randint(3, 12)),
                ramp_prediction_mm=round(ramp, 4),
                raw_nwp_mm=round(nwp, 4),
                global_ml_mm=round(gml, 4),
                difference_ramp_nwp=round(ramp - nwp, 4),
                difference_ramp_globalml=round(ramp - gml, 4),
                observed_mm=None,  # NOT_AVAILABLE in SYNTHETIC_DEMO mode
                ramp_error_mm=None,
                nwp_error_mm=None,
                availability_status="SYNTHETIC_DEMO",
                data_mode=self.data_mode,
            ))
        return records

    def get_spatial_summary(
        self,
        district_records: List[DistrictVerificationRecord],
    ) -> Dict[str, Any]:
        """Summarize spatial verification across all districts."""
        n_districts = len(district_records)
        ramp_preds = [d.ramp_prediction_mm for d in district_records]
        nwp_preds = [d.raw_nwp_mm for d in district_records]
        diffs = [d.difference_ramp_nwp for d in district_records]

        return {
            "n_districts": n_districts,
            "mean_ramp_mm": round(float(np.mean(ramp_preds)), 4) if ramp_preds else None,
            "max_ramp_mm": round(float(np.max(ramp_preds)), 4) if ramp_preds else None,
            "mean_difference_ramp_nwp_mm": round(float(np.mean(diffs)), 4) if diffs else None,
            "mean_nwp_mm": round(float(np.mean(nwp_preds)), 4) if nwp_preds else None,
            "observations_available": any(d.observed_mm is not None for d in district_records),
            "availability_status": "SYNTHETIC_DEMO",
            "data_mode": self.data_mode,
        }
