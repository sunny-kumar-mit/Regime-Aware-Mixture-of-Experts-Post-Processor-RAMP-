"""
RAMP Physics-Informed Regime Indicators Engine
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Calculates composite physical indicators for the 7 canonical weather regimes
from Phase 3 NWP predictor features.

Strict Constraints:
  - NEVER use ground-truth observations (observed_rainfall_mm, etc.) in indicators.
  - Gracefully degrade when optional auxiliary features (e.g. DEM elevation) are missing.
  - Distinguish model regime signals from official IMD meteorological declarations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from ml.regimes.definitions import WeatherRegime, regime_registry


class RegimeIndicatorEngine:
    """
    Computes rule-based, physics-informed indicator scores for each sample.
    """

    def __init__(self) -> None:
        self.registry = regime_registry

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms input forecast features into regime indicator scores.
        Output columns:
          - active_score
          - break_score
          - low_depression_score
          - coastal_score
          - orographic_score
          - western_disturbance_score
          - transition_score
          - missing_indicator_count
          - indicator_confidence
        """
        out = df.copy()
        n = len(out)

        # Pre-allocate score columns
        active_scores = np.zeros(n, dtype=np.float32)
        break_scores = np.zeros(n, dtype=np.float32)
        low_dep_scores = np.zeros(n, dtype=np.float32)
        coastal_scores = np.zeros(n, dtype=np.float32)
        orographic_scores = np.zeros(n, dtype=np.float32)
        wd_scores = np.zeros(n, dtype=np.float32)
        transition_scores = np.zeros(n, dtype=np.float32)
        missing_counts = np.zeros(n, dtype=np.int32)
        confidences = np.zeros(n, dtype=np.float32)

        # Feature extraction with safe defaults
        rain = out["raw_nwp_rainfall"].fillna(0.0).values if "raw_nwp_rainfall" in out.columns else np.zeros(n)
        u850 = out["u850"].fillna(0.0).values if "u850" in out.columns else np.zeros(n)
        v850 = out["v850"].fillna(0.0).values if "v850" in out.columns else np.zeros(n)
        calc_wspd = np.sqrt(u850**2 + v850**2)
        wspd = out["wind_speed_850"].fillna(pd.Series(calc_wspd, index=out.index)).values if "wind_speed_850" in out.columns else calc_wspd
        wdir = out["wind_direction_850"].fillna(270.0).values if "wind_direction_850" in out.columns else np.full(n, 270.0)

        mslp = out["mslp"].values if "mslp" in out.columns else np.full(n, 101000.0)
        mslp_anom = out["mslp_anomaly"].values if "mslp_anomaly" in out.columns else np.zeros(n)
        t2m = out["temperature"].values if "temperature" in out.columns else np.full(n, 300.0)
        rh = out["relative_humidity"].values if "relative_humidity" in out.columns else np.full(n, 70.0)
        pw = out["precipitable_water"].values if "precipitable_water" in out.columns else np.full(n, 40.0)
        cape = out["cape"].values if "cape" in out.columns else np.full(n, 500.0)
        gh500 = out["geopotential_height"].values if "geopotential_height" in out.columns else np.full(n, 5860.0)

        lat = out["latitude"].values if "latitude" in out.columns else np.full(n, 20.0)
        lon = out["longitude"].values if "longitude" in out.columns else np.full(n, 78.0)

        # Check auxiliary features availability
        has_elev = "elevation" in out.columns and out["elevation"].notnull().any()
        elev = out["elevation"].fillna(0.0).values if has_elev else np.zeros(n)

        has_dist_coast = "distance_to_coast" in out.columns and out["distance_to_coast"].notnull().any()
        dist_coast = out["distance_to_coast"].fillna(999.0).values if has_dist_coast else np.full(n, 999.0)

        is_monsoon = out["monsoon"].values if "monsoon" in out.columns else np.ones(n, dtype=int)
        is_winter = out["winter"].values if "winter" in out.columns else np.zeros(n, dtype=int)

        # Missing indicator counter per sample
        base_missing = (
            (1 if not has_elev else 0)
            + (1 if not has_dist_coast else 0)
            + (1 if "cape" not in out.columns else 0)
            + (1 if "precipitable_water" not in out.columns else 0)
        )

        for i in range(n):
            missing_counts[i] = base_missing
            m_flag = is_monsoon[i]
            w_flag = is_winter[i]

            # -----------------------------------------------------------------
            # 1. Active Monsoon Indicator
            # -----------------------------------------------------------------
            act_pts = 0.0
            if m_flag == 1:
                act_pts += 0.25
                if u850[i] >= 6.0:  # strong Somali jet westerlies
                    act_pts += 0.25
                if rain[i] >= 5.0:  # widespread active rain
                    act_pts += 0.25
                if pw[i] >= 45.0 or rh[i] >= 75.0:  # high moisture
                    act_pts += 0.25
            active_scores[i] = act_pts

            # -----------------------------------------------------------------
            # 2. Break Monsoon Indicator
            # -----------------------------------------------------------------
            brk_pts = 0.0
            if m_flag == 1:
                brk_pts += 0.20
                if rain[i] < 2.0:  # rain deficit in central India
                    brk_pts += 0.30
                if u850[i] < 4.0:  # weakened westerlies
                    brk_pts += 0.25
                if mslp_anom[i] > 100.0 or rh[i] < 68.0:  # high pressure / lower humidity
                    brk_pts += 0.25
            break_scores[i] = brk_pts

            # -----------------------------------------------------------------
            # 3. Monsoon Low / Depression Indicator
            # -----------------------------------------------------------------
            dep_pts = 0.0
            if mslp[i] < 100400.0 or mslp_anom[i] < -150.0:  # low pressure signature
                dep_pts += 0.35
            if mslp[i] < 100000.0 or mslp_anom[i] < -250.0:  # deep depression signature
                dep_pts += 0.20
            if wspd[i] >= 10.0:  # cyclonic circulation wind speed
                dep_pts += 0.25
            if cape[i] >= 800.0 or rain[i] >= 20.0:  # intense convective activity
                dep_pts += 0.20
            if pw[i] >= 50.0:
                dep_pts += 0.20
            low_dep_scores[i] = min(1.0, dep_pts)

            # -----------------------------------------------------------------
            # 4. Coastal Rainfall Indicator
            # -----------------------------------------------------------------
            cst_pts = 0.0
            # Proximity proxy: either explicit distance or India coastal bounding margins
            is_near_coast = (dist_coast[i] <= 100.0) if has_dist_coast else (
                (lon[i] <= 76.5 and 8.0 <= lat[i] <= 21.5)  # West Coast corridor
                or (lon[i] >= 79.0 and 10.0 <= lat[i] <= 22.0) # East Coast corridor
            )
            if is_near_coast:
                cst_pts += 0.40
                if rh[i] >= 78.0 or pw[i] >= 45.0:
                    cst_pts += 0.30
                # Onshore westerly component for West Coast
                if lon[i] <= 77.0 and 200.0 <= wdir[i] <= 300.0:
                    cst_pts += 0.30
                elif lon[i] > 77.0:
                    cst_pts += 0.20
            coastal_scores[i] = min(1.0, cst_pts)

            # -----------------------------------------------------------------
            # 5. Orographic Rainfall Indicator
            # -----------------------------------------------------------------
            oro_pts = 0.0
            # If DEM elevation exists, use it; otherwise use Western Ghats / NE / Himalayan foothills terrain corridor
            is_mountainous = (elev[i] >= 300.0) if has_elev else (
                (73.0 <= lon[i] <= 76.5 and 8.5 <= lat[i] <= 21.0)  # Western Ghats corridor
                or (lon[i] >= 88.0 and lat[i] >= 24.5)               # Meghalaya / Northeast
                or (lat[i] >= 28.0 and lon[i] <= 80.0)               # Sub-Himalayan foothills
            )
            if is_mountainous:
                oro_pts += 0.40
                # Perpendicular moisture flow (Southwesterly against Western Ghats)
                if 220.0 <= wdir[i] <= 290.0 and wspd[i] >= 8.0:
                    oro_pts += 0.35
                if rh[i] >= 80.0:
                    oro_pts += 0.25
            orographic_scores[i] = min(1.0, oro_pts)

            # Physics interaction: Dampen background active monsoon if a specific localized or synoptic system dominates
            if dep_pts >= 0.70:
                act_pts *= 0.50
            elif cst_pts >= 0.70 and not (elev[i] >= 500.0):
                act_pts *= 0.60
            elif oro_pts >= 0.70:
                act_pts *= 0.60
            active_scores[i] = min(1.0, act_pts)

            # -----------------------------------------------------------------
            # 6. Western Disturbance Indicator
            # -----------------------------------------------------------------
            wd_pts = 0.0
            if lat[i] >= 26.0:  # Northwest / North India
                wd_pts += 0.25
                if w_flag == 1 or m_flag == 0:  # Winter or non-monsoon
                    wd_pts += 0.25
                if gh500[i] <= 5840.0:  # Upper-level trough
                    wd_pts += 0.25
                if t2m[i] <= 295.0 or u850[i] >= 5.0:  # Westerlies / lower temp
                    wd_pts += 0.25
            western_disturbance_scores = wd_scores  # alias reference
            wd_scores[i] = wd_pts

            # -----------------------------------------------------------------
            # 7. Transition / Other Indicator
            # -----------------------------------------------------------------
            # Elevated if no single regime dominates, or if top regimes conflict
            scores = [act_pts, brk_pts, dep_pts, cst_pts, oro_pts, wd_pts]
            max_s = max(scores)
            sorted_s = sorted(scores, reverse=True)

            if max_s < 0.40:
                trans_pts = 0.70
            elif (sorted_s[0] - sorted_s[1]) < 0.10:  # Ambiguous close contest
                trans_pts = 0.60
            else:
                trans_pts = max(0.05, 1.0 - max_s)
            transition_scores[i] = trans_pts

            # Composite confidence score
            confidences[i] = max_s * (1.0 - 0.08 * missing_counts[i])

        out["active_score"] = active_scores
        out["break_score"] = break_scores
        out["low_depression_score"] = low_dep_scores
        out["coastal_score"] = coastal_scores
        out["orographic_score"] = orographic_scores
        out["western_disturbance_score"] = wd_scores
        out["transition_score"] = transition_scores
        out["missing_indicator_count"] = missing_counts
        out["indicator_confidence"] = np.clip(confidences, 0.1, 1.0)

        return out
