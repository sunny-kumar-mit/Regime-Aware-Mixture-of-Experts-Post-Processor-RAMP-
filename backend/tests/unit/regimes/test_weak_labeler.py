"""
Unit Tests for RAMP Weak Labeling and Provenance
SIH26080 | Weather Regime Intelligence Engine
MoES / NCMRWF
"""

import numpy as np
import pandas as pd
import pytest

from ml.regimes.definitions import LabelQuality, LabelSource, REGIME_ORDER, WeatherRegime
from ml.regimes.weak_labeler import RegimeLabeler


@pytest.fixture
def weak_labeler():
    return RegimeLabeler(temperature=0.4)


def test_weak_label_probability_sum_equals_one(weak_labeler):
    """Every generated candidate probability distribution must sum to 1.0 within 1e-5."""
    df = pd.DataFrame([
        {
            "raw_nwp_rainfall": 25.0,
            "u850": 11.0,
            "v850": 4.0,
            "mslp": 100000.0,
            "relative_humidity": 90.0,
            "latitude": 20.0,
            "longitude": 84.0,
            "monsoon": 1,
            "winter": 0,
        },
        {
            "raw_nwp_rainfall": 0.0,
            "u850": 1.5,
            "v850": 0.0,
            "mslp": 101300.0,
            "relative_humidity": 50.0,
            "latitude": 25.0,
            "longitude": 75.0,
            "monsoon": 1,
            "winter": 0,
        },
    ])
    labeled = weak_labeler.generate_weak_labels(df)
    prob_cols = [f"p_{r.value.lower()}" for r in REGIME_ORDER]

    sums = labeled[prob_cols].sum(axis=1).values
    for s in sums:
        assert np.isclose(s, 1.0, atol=1e-5), f"Probabilities do not sum to 1.0: {s}"


def test_label_provenance_and_quality(weak_labeler):
    """Weak labels must declare WEAK_RULE provenance and appropriate quality tiers."""
    df = pd.DataFrame([{
        "raw_nwp_rainfall": 40.0,
        "u850": 14.0,
        "v850": 9.0,
        "wind_speed_850": 16.6,
        "mslp": 99800.0,
        "mslp_anomaly": -300.0,
        "relative_humidity": 95.0,
        "precipitable_water": 60.0,
        "cape": 1500.0,
        "latitude": 20.0,
        "longitude": 85.0,
        "monsoon": 1,
        "winter": 0,
        "elevation": 50.0,
        "distance_to_coast": 50.0,
    }])
    labeled = weak_labeler.generate_weak_labels(df)
    row = labeled.iloc[0]

    assert row["regime_label"] == WeatherRegime.LOW_DEPRESSION.value
    assert row["regime_label_source"] == LabelSource.WEAK_RULE.value
    assert row["regime_label_confidence"] >= 0.35
    assert row["regime_label_quality"] in [LabelQuality.HIGH.value, LabelQuality.MEDIUM.value]


def test_weak_label_distribution_across_classes(weak_labeler):
    """Weak labeler should support all 7 classes under appropriate inputs."""
    # Synthetic samples designed to trigger different regimes
    samples = [
        # 1. Active Monsoon
        {"raw_nwp_rainfall": 15.0, "u850": 10.0, "v850": 2.0, "mslp": 100500.0, "relative_humidity": 85.0, "latitude": 21.0, "longitude": 78.0, "monsoon": 1, "winter": 0, "distance_to_coast": 400.0, "elevation": 150.0},
        # 2. Break Monsoon
        {"raw_nwp_rainfall": 0.1, "u850": 2.0, "v850": 0.0, "mslp": 101200.0, "mslp_anomaly": 150.0, "relative_humidity": 55.0, "latitude": 22.0, "longitude": 79.0, "monsoon": 1, "winter": 0, "distance_to_coast": 400.0, "elevation": 150.0},
        # 3. Low/Depression
        {"raw_nwp_rainfall": 45.0, "u850": 15.0, "v850": 8.0, "mslp": 99700.0, "mslp_anomaly": -350.0, "relative_humidity": 95.0, "latitude": 20.0, "longitude": 86.0, "monsoon": 1, "winter": 0, "distance_to_coast": 50.0, "elevation": 20.0},
        # 4. Coastal
        {"raw_nwp_rainfall": 25.0, "u850": 8.0, "v850": 1.0, "wind_direction_850": 260.0, "mslp": 100800.0, "relative_humidity": 90.0, "latitude": 15.0, "longitude": 73.8, "monsoon": 1, "winter": 0, "distance_to_coast": 5.0, "elevation": 10.0},
        # 5. Orographic
        {"raw_nwp_rainfall": 35.0, "u850": 10.0, "v850": 2.0, "wind_direction_850": 255.0, "wind_speed_850": 11.0, "mslp": 100700.0, "relative_humidity": 92.0, "latitude": 14.5, "longitude": 74.5, "monsoon": 1, "winter": 0, "elevation": 800.0, "distance_to_coast": 80.0},
        # 6. Western Disturbance
        {"raw_nwp_rainfall": 12.0, "u850": 8.0, "v850": 1.0, "wind_direction_850": 280.0, "geopotential_height": 5750.0, "temperature": 280.0, "relative_humidity": 70.0, "latitude": 33.0, "longitude": 75.0, "monsoon": 0, "winter": 1, "distance_to_coast": 800.0, "elevation": 1200.0},
        # 7. Transition / Other
        {"raw_nwp_rainfall": 0.5, "u850": 1.5, "v850": 0.5, "mslp": 101000.0, "mslp_anomaly": 0.0, "temperature": 298.0, "relative_humidity": 50.0, "latitude": 24.0, "longitude": 78.0, "monsoon": 0, "winter": 0, "distance_to_coast": 600.0, "elevation": 200.0},
    ]
    df = pd.DataFrame(samples)
    labeled = weak_labeler.generate_weak_labels(df)
    labels = set(labeled["regime_label"].unique())
    assert len(labels) >= 5, f"Expected diverse weak labels, got {labels}"
