"""
RAMP Spatial Uncertainty Propagation Engine
SIH26080 | Spatial Forecast Products & District Aggregation
MoES / NCMRWF
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np


class SpatialUncertaintyEngine:
    """
    Quantifies and propagates grid-level meteorological and regime uncertainty
    to district and state aggregations.
    """

    @staticmethod
    def calculate_district_uncertainty(
        rainfall_values: np.ndarray,
        weights: np.ndarray,
        regime_entropies: Optional[np.ndarray] = None,
        coverage_fraction: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Computes composite uncertainty metrics:
          1. Spatial variance / spread of rainfall across district
          2. Area-weighted standard deviation
          3. Coverage penalty (uncertainty rises when grid coverage is low)
          4. Mean regime entropy (atmospheric state ambiguity)
        """
        if len(rainfall_values) == 0:
            return {
                "uncertainty_available": False,
                "spatial_std_mm": 0.0,
                "coverage_uncertainty": 1.0,
                "composite_uncertainty_score": 1.0,
            }

        w_norm = weights / np.maximum(1e-6, np.sum(weights))
        weighted_mean = float(np.sum(w_norm * rainfall_values))
        weighted_var = float(np.sum(w_norm * (rainfall_values - weighted_mean) ** 2))
        spatial_std = float(np.sqrt(max(0.0, weighted_var)))

        # Coverage uncertainty penalty: 0.0 when 100% coverage, 1.0 when 0%
        cov_penalty = float(np.clip(1.0 - coverage_fraction, 0.0, 1.0))

        # Regime entropy spread
        mean_entropy = float(np.mean(regime_entropies)) if regime_entropies is not None and len(regime_entropies) > 0 else 0.15

        # Composite normalized uncertainty [0, 1]
        norm_spread = float(np.clip(spatial_std / max(1.0, weighted_mean + 10.0), 0.0, 1.0))
        composite = float(np.clip(0.5 * norm_spread + 0.3 * cov_penalty + 0.2 * mean_entropy, 0.0, 1.0))

        return {
            "uncertainty_available": True,
            "weighted_mean_mm": round(weighted_mean, 2),
            "spatial_std_mm": round(spatial_std, 2),
            "coefficient_of_variation": round(spatial_std / max(1e-3, weighted_mean), 3),
            "coverage_fraction": round(coverage_fraction, 4),
            "coverage_penalty": round(cov_penalty, 4),
            "mean_regime_entropy": round(mean_entropy, 4),
            "composite_uncertainty_score": round(composite, 4),
            "uncertainty_tier": "LOW" if composite < 0.25 else ("MEDIUM" if composite < 0.60 else "HIGH"),
        }
