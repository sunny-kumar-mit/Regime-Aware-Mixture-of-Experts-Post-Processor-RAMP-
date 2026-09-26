# RAMP Data Leakage Protection & Invariant Guard

**Project:** SIH26080 — Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts  
**Organization:** Ministry of Earth Sciences (MoES)  
**Department:** National Centre for Medium Range Weather Forecasting (NCMRWF)  
**Module:** `ml.dataset.leakage_guard.LeakageGuard`

---

## 1. Overview & Threat Model

Data leakage occurs when information from outside the training partition influences feature generation, model calibration, or evaluation. In meteorological post-processing, temporal autocorrelation and backward time travel represent severe scientific risks.

The `LeakageGuard` module audits the pipeline against **10 strict scientific invariants**. If any invariant is violated, the pipeline **FAILS LOUDLY** by raising `DataLeakageError`.

---

## 2. The 10 Audited Invariants

| # | Invariant Rule | Description & Enforcement | Failure Action |
| :- | :--- | :--- | :--- |
| **1** | **No Target in Predictors** | Target variables (`observed_rainfall_mm`, binary threshold flags, anomaly) must never be present in feature matrix $X$. | Raises `DataLeakageError` |
| **2** | **No Future Observations** | Target observation timestamps must exactly match forecast valid time ($T_{\text{valid}}$), never a future timestamp. | Raises `DataLeakageError` |
| **3** | **No Test Statistics in Preprocessing** | Missing value imputations and normalization scalers must not use validation or test data. | Raises `DataLeakageError` |
| **4** | **No Future Data in Climatology** | The climatological baseline lookup must be fitted strictly on the `TRAIN` partition. | Raises `DataLeakageError` |
| **5** | **Scalers Fitted on Train Only** | Normalization means and standard deviations are computed strictly on `TRAIN`. | Raises `DataLeakageError` |
| **6** | **Categorical Mappings Fitted on Train Only** | All encoders or dictionary indices are trained on `TRAIN`. | Raises `DataLeakageError` |
| **7** | **Imputation Fitted on Train Only** | Medians or mode values for missing data imputation are extracted strictly from `TRAIN`. | Raises `DataLeakageError` |
| **8** | **Quantiles Fitted on Train Only** | Verification quantiles or calibration bins must not be fitted across pooled test data. | Raises `DataLeakageError` |
| **9** | **No Forecast Error in Predictors** | Diagnostic forecast error ($Y - \hat{Y}$) is strictly forbidden from $X$. | Raises `DataLeakageError` |
| **10** | **No Observation Spatial Pooling in Predictors** | Spatial neighborhood statistics ($3 \times 3$ mean, max) must be calculated strictly from NWP predictors. | Raises `DataLeakageError` |

---

## 3. Auditing Interface

```python
from ml.dataset.leakage_guard import LeakageGuard, DataLeakageError

guard = LeakageGuard()

# 1. Feature column audit
guard.audit_features(feature_columns)

# 2. Spatio-temporal causality audit
guard.audit_temporal_alignment(dataframe)

# 3. Climatology split verification
guard.audit_climatology(climatology.fitted_split, train_split_name="TRAIN")

# 4. Preprocessing manifest audit
guard.audit_preprocessing_manifest(preprocessing_manifest)

# 5. Generate auditable report
report = guard.generate_report()
assert report.status == "PASS"
```
