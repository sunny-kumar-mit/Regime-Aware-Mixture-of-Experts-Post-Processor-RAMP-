# RAMP Observation Target Definitions

**Project:** SIH26080 — Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts  
**Organization:** Ministry of Earth Sciences (MoES)  
**Department:** National Centre for Medium Range Weather Forecasting (NCMRWF)  
**Module:** `ml.dataset.targets.TargetBuilder`

---

## 1. Overview

The RAMP pipeline constructs six canonical observation targets from ground-truth IMD $0.25^\circ$ daily gridded rainfall observations.

Every target corresponds strictly to the **forecast valid time** ($T_{\text{valid}} = T_{\text{init}} + \text{lead}$).

---

## 2. Canonical Target Specifications

| Target Name | Type | Threshold / Definition | Scientific Justification |
| :--- | :--- | :--- | :--- |
| `observed_rainfall_mm` | Continuous | Accumulated rainfall in mm / 24h | Ground-truth IMD continuous target for regression baselines and MoE experts. |
| `rainfall_occurrence` | Binary | $\ge 0.1\text{ mm}$ (0 = dry/trace, 1 = event) | Standard IMD threshold for measurable precipitation. Rainfall $<0.1\text{ mm}$ represents non-measurable trace. |
| `heavy_rainfall` | Binary | $\ge 64.5\text{ mm} / 24\text{h}$ | IMD standard criteria for "Heavy Rainfall" alert category. |
| `very_heavy_rainfall` | Binary | $\ge 115.6\text{ mm} / 24\text{h}$ | IMD standard criteria for "Very Heavy Rainfall" alert category. |
| `extremely_heavy_rainfall` | Binary | $\ge 204.5\text{ mm} / 24\text{h}$ | IMD standard criteria for "Extremely Heavy Rainfall" catastrophic event category. |
| `rainfall_anomaly` | Continuous | $\text{Observed} - \text{Climatology}_{\text{train}}$ | Departure from normal daily rainfall fitted strictly on the training period. |

---

## 3. Climatology Baseline & Zero-Leakage Guarantee

To compute `rainfall_anomaly`, a daily climatological baseline is required.
$$\text{rainfall\_anomaly}(s, t) = \text{observed\_rainfall}(s, t) - \text{climatology}(s, \text{doy}(t))$$

### Strict Invariant:
1. `ClimatologyBaseline.fit()` is executed **only on the training split** (`split_label="TRAIN"`).
2. It is mathematically forbidden to include validation or test observations in the climatological lookup table.
3. Attempting to fit climatology on `TEST` raises `DataLeakageError`.

---

## 4. Extreme Rainfall Preservation Policy

In standard tabular machine learning, values in the 99.9th percentile (e.g. 250–400 mm) are often truncated as outliers.

**In RAMP, extreme rainfall preservation is paramount:**
- Extreme monsoon events cause flash floods and severe damage.
- Target values $\ge 204.5\text{ mm}$ are flagged `VALID_EXTREME`.
- Outlier diagnostics are reported separately, but values are **never clipped or deleted**.

---

## 5. Phase 4 Regime Placeholders

The following regime columns are present in the target schema but deliberately initialized to `None` in Phase 3:
- `regime_label`: Reserved for Phase 4 regime classifier.
- `regime_label_source`: Provenance of assigned regime.
- `regime_label_confidence`: Classifier posterior probability.

*No regime labels are fabricated in Phase 3.*
