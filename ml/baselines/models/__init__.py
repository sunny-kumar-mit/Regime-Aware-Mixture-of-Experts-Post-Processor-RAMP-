"""
RAMP Baseline Models Package
"""

from ml.baselines.models.base import BaseBaselineModel
from ml.baselines.models.raw_nwp import RawNWPBaseline
from ml.baselines.models.mean_bias import MeanBiasCorrector
from ml.baselines.models.quantile_mapping import EmpiricalQuantileMapper
from ml.baselines.models.global_ml import GlobalMLPostProcessor

__all__ = [
    "BaseBaselineModel",
    "RawNWPBaseline",
    "MeanBiasCorrector",
    "EmpiricalQuantileMapper",
    "GlobalMLPostProcessor",
]
