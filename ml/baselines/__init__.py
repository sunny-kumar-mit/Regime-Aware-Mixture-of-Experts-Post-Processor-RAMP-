"""
RAMP Baseline Rainfall Post-Processing & Benchmarking Package
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

Provides the four global baseline models:
  1. Raw NWP Baseline (RawNWPBaseline)
  2. Mean Bias Corrector (MeanBiasCorrector)
  3. Empirical Quantile Mapping (EmpiricalQuantileMapper)
  4. Global Machine Learning Post-Processor (GlobalMLPostProcessor)
"""

from ml.baselines.models.raw_nwp import RawNWPBaseline
from ml.baselines.models.mean_bias import MeanBiasCorrector
from ml.baselines.models.quantile_mapping import EmpiricalQuantileMapper
from ml.baselines.models.global_ml import GlobalMLPostProcessor

__all__ = [
    "RawNWPBaseline",
    "MeanBiasCorrector",
    "EmpiricalQuantileMapper",
    "GlobalMLPostProcessor",
]
