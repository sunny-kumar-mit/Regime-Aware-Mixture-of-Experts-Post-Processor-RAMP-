# PHASE 4 PROJECT REPORT — Weather Regime Intelligence Engine

**Project:** RAMP (Regime-Aware Mixture-of-Experts Post-Processor)  
**Problem Statement:** SIH26080 — Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts  
**Organization:** Ministry of Earth Sciences (MoES)  
**Department:** National Centre for Medium Range Weather Forecasting (NCMRWF)  
**Status:** COMPLETE  

---

## 1. Executive Summary
Phase 4 developed and validated the **Weather Regime Intelligence Engine** for RAMP. Rather than treating meteorological regimes as arbitrary machine learning classes or assigning brittle hard labels, the engine operates on a rigorous hybrid framework: **Physics-Informed Indicators + Documented Regime Definitions + Data-Driven Multiclass Classification + Validation-Fitted Probability Calibration + Information-Theoretic Uncertainty Estimation + Sequential Regime Transition Tracking**.

The engine classifies forecast states into the 7 canonical Indian weather regimes:
1. `ACTIVE_MONSOON`
2. `BREAK_MONSOON`
3. `LOW_DEPRESSION`
4. `COASTAL`
5. `OROGRAPHIC`
6. `WESTERN_DISTURBANCE`
7. `TRANSITION_OTHER`

The primary output is a continuous, strictly normalized probability distribution vector ($p \in \mathbb{R}^7, \sum_{i=1}^7 p_i = 1.0$), paired with Shannon entropy $H(p)$, uncertainty tier (`LOW`, `MEDIUM`, `HIGH`), and sequential transition trajectory indicators. The entire pipeline was verified through 41 new unit and integration tests (bringing the cumulative project test suite to 184 tests, 0 failures), along with a full frontend build (`tsc && vite build`) and 8 production REST endpoints.

**Critical Meteorological Integrity Notice:**
Real observational training data is currently unavailable in the local environment. All models and diagnostics have been verified on `SYNTHETIC_DEMO` data. The system explicitly reports `REAL TRAINING DATA: NOT AVAILABLE` across APIs and the frontend UI. No scientific performance has been fabricated.

---

## 2. Problem Addressed
Standard post-processing schemes apply uniform statistical bias corrections (such as quantile mapping or global regression) across all meteorological conditions. However, the Indian monsoon exhibits stark systematic bias bifurcations across distinct synoptic regimes:
- **Active Monsoon:** Strong Somali Low-Level Jet ($u_{850} > 15$ m/s) with excessive wet biases in central India.
- **Break Monsoon:** Suppressed convection and severe model overforecasting in central India with localized foothills deluge.
- **Monsoon Low/Depression:** Cyclonic vortex track displacement errors creating dipole bias patterns.
- **Coastal & Orographic:** Sub-grid marine convergence and steep topographic ascent smoothed by global NWP grids.
- **Western Disturbance:** Extratropical upper-level troughs over northwest India.

Without regime awareness, global post-processing models overcorrect during active phases and undercorrect during depressions. Phase 4 provides the regime probability vector required to dynamically gate specialized experts in Phase 6.

---

## 3. Objective
- Build a configurable regime definition registry (`config/regimes.yaml`).
- Implement the `RegimeIndicatorEngine` to compute physics-informed composite scores for all 7 regimes from Phase 3 NWP predictor features.
- Build a weak-label generation engine (`RegimeLabeler`) with explicit provenance (`WEAK_RULE`), confidence scoring, and quality tiering (`HIGH`, `MEDIUM`, `LOW`).
- Provide an extensible `AuthoritativeRegimeLabelProvider` interface with honest unavailable reporting when real IMD bulletins are absent.
- Build 3 candidate classifiers: Rule-based Physics Baseline, Random Forest, and LightGBM with balanced class weights.
- Enforce strict zero-leakage constraints: target variables (`observed_rainfall_mm`, `heavy_rainfall`, etc.) must never enter $X$.
- Implement One-vs-Rest probability calibration (Isotonic Regression and Platt Sigmoid) fitted **strictly on the validation split** (never on test data).
- Enforce that all output probability vectors sum strictly to $1.0 \pm 10^{-5}$.
- Build the `UncertaintyEngine` using information-theoretic Shannon entropy ($H(p) = -\sum p_i \log_2 p_i$).
- Build the `RegimeTransitionDetector` tracking distribution shift ($TVD$) across sequential forecast horizons.
- Build the `EnsembleRegimeEvaluator` aggregating ensemble member probabilities into consensus and spread metrics.
- Expose 8 production REST API endpoints under `/api/regime/*`.
- Upgrade the frontend `/regime` page with probability bar charts, "Why this regime?" model attribution, transition timeline, spatial layer preview, and persistent synthetic demo notices.

---

## 4. Architecture
```
                                 NWP DATA
                                    │
                                    ▼
                             Phase 3 Dataset
                      (27 Active Tabular Predictors)
                                    │
                                    ▼
                         PHYSICS INDICATORS ENGINE
                 ┌──────────────────┼──────────────────┐
                 ▼                  ▼                  ▼
              Monsoon          Circulation          Terrain
              Signals            Signals            Signals
           (Rain/Somali)     (MSLP Anomaly/Wspd)  (DEM/Coast)
                 └──────────────────┬──────────────────┘
                                    ▼
                            WEAK LABEL ENGINE
                       (Temperature Softmax, WEAK_RULE)
                                    │
                                    ▼
                         ML REGIME CLASSIFIERS
                   [Rule Baseline | Random Forest | LightGBM]
                                    │
                                    ▼
                          PROBABILITY CALIBRATION
                    (Isotonic Fitted Strictly on Validation)
                                    │
                                    ▼
                        REGIME PROBABILITY VECTOR
                       P = [p₁, p₂, p₃, p₄, p₅, p₆, p₇]ᵀ
                               (Σ pᵢ = 1.0)
                                    │
                 ┌──────────────────┴──────────────────┐
                 ▼                                     ▼
        UNCERTAINTY ENGINE                     TRANSITION ENGINE
      (Shannon Entropy H(p))               (Sequential TVD t₀ -> t₁)
                 └──────────────────┬──────────────────┘
                                    │
                                    ▼
                       INPUT TO PHASE 6 RAMP (MoE)
```

---

## 5. Implementation
- **Registry (`ml/regimes/definitions.py` & `config/regimes.yaml`):** Bijective integer-to-enum mapping, definition metadata, threshold configurations, confidence rules.
- **Physics Indicators (`ml/regimes/indicators.py`):** Calculates composite scores for Active, Break, Low/Depression, Coastal, Orographic, Western Disturbance, and Transition/Other. Evaluates missing indicator counts and gracefully degrades when DEM or coastal distance features are missing.
- **Weak Labeler (`ml/regimes/weak_labeler.py`):** Applies temperature-scaled softmax over indicator scores. Assigns provenance `WEAK_RULE` and quality tiers (`HIGH`, `MEDIUM`, `LOW`).
- **Authoritative Provider (`ml/regimes/authoritative.py`):** Abstract provider interface and `IMDMonsoonBulletinProvider`. Reports `is_available = False` honestly.
- **Classifiers (`ml/regimes/classifier.py`):**
  - `RuleBasedBaselineClassifier`: Rule-based reference.
  - `RandomForestRegimeClassifier`: 100 trees, balanced class weighting.
  - `LightGBMRegimeClassifier`: Gradient boosted trees with balanced multiclass objective.
- **Probability Calibration (`ml/regimes/calibration.py`):** One-vs-Rest Isotonic Regression fitted strictly on validation predictions; enforces row normalization $\sum p_i = 1.0$.
- **Uncertainty (`ml/regimes/uncertainty.py`):** Shannon entropy $H(p)$, normalized entropy $H(p)/\log_2(7)$, categorized into `LOW`, `MEDIUM`, `HIGH`.
- **Transition Detection (`ml/regimes/transition.py`):** Total Variation Distance ($TVD$) over sequential lead times; identifies model-identified transitions when $TVD \ge 0.20$.
- **Ensemble Evaluation (`ml/regimes/ensemble_regime.py`):** Aggregates member probabilities to consensus distribution and member agreement ratios.
- **Model Registry (`ml/regimes/model_registry.py`):** Safe joblib serialization and metadata JSON tracking.
- **Inference Service (`ml/regimes/inference.py`):** Supports single-sample inference and 2D India grid layer generation.

---

## 6. Data Flow
1. **Input:** Tabular forecast feature record or spatial grid containing Phase 3 NWP predictor features.
2. **Audit:** `LeakageGuard` verifies that no future observation targets are present in $X$.
3. **Indicator Evaluation:** `RegimeIndicatorEngine` computes the 7 physics scores and flags missing auxiliary features.
4. **Classifier Posteriors:** Trained `LightGBMRegimeClassifier` generates raw multiclass probabilities.
5. **Validation Calibration:** `RegimeCalibrator` scales raw probabilities using validation-fitted isotonic functions and normalizes rows to strictly sum to 1.0.
6. **Uncertainty & Transition:** `UncertaintyEngine` computes Shannon entropy; `RegimeTransitionDetector` logs trajectory stability.
7. **Attribution:** Model gradient/split importances are sorted to provide "Top model-attribution features".
8. **Delivery:** Structured JSON returned via FastAPI to the frontend dashboard.

---

## 7. Algorithms / Methodology
### 7.1 Physics-Informed Indicator Equations
- **Active Monsoon:**
  $$S_{\text{active}} = 0.25 \cdot \mathbb{I}(\text{monsoon}) + 0.25 \cdot \mathbb{I}(u_{850} \ge 6) + 0.25 \cdot \mathbb{I}(\text{rain} \ge 5) + 0.25 \cdot \mathbb{I}(\text{pw} \ge 45 \lor \text{rh} \ge 75)$$
- **Break Monsoon:**
  $$S_{\text{break}} = 0.20 \cdot \mathbb{I}(\text{monsoon}) + 0.30 \cdot \mathbb{I}(\text{rain} < 2) + 0.25 \cdot \mathbb{I}(u_{850} < 4) + 0.25 \cdot \mathbb{I}(\Delta p_{\text{mslp}} > 100 \lor \text{rh} < 68)$$
- **Low / Depression:**
  $$S_{\text{dep}} = 0.35 \cdot \mathbb{I}(p_{\text{mslp}} < 100400 \lor \Delta p_{\text{mslp}} < -150) + 0.20 \cdot \mathbb{I}(\Delta p_{\text{mslp}} < -250) + 0.25 \cdot \mathbb{I}(\text{wspd}_{850} \ge 10) + 0.20 \cdot \mathbb{I}(\text{cape} \ge 800) + 0.20 \cdot \mathbb{I}(\text{pw} \ge 50)$$
- **Transition / Other:**
  $$S_{\text{trans}} = \begin{cases} 0.70, & \max(S) < 0.40 \\ 0.60, & S_{(1)} - S_{(2)} < 0.10 \\ \max(0.05, 1.0 - \max(S)), & \text{otherwise} \end{cases}$$

### 7.2 Information-Theoretic Uncertainty
$$H(p) = -\sum_{i=1}^{7} p_i \log_2(p_i), \quad H_{\text{norm}}(p) = \frac{H(p)}{\log_2(7)} \in [0, 1]$$
- $\text{Uncertainty} = \text{LOW}$ if $H_{\text{norm}} < 0.40$
- $\text{Uncertainty} = \text{MEDIUM}$ if $0.40 \le H_{\text{norm}} < 0.75$
- $\text{Uncertainty} = \text{HIGH}$ if $H_{\text{norm}} \ge 0.75$

### 7.3 Total Variation Distance Transition Detection
$$\text{TVD}(p^{(t)}, p^{(t+1)}) = \frac{1}{2} \sum_{i=1}^{7} \left| p_i^{(t)} - p_i^{(t+1)} \right|$$
A transition event is declared if $\text{TVD} \ge 0.20$ or $\operatorname{argmax}(p^{(t)}) \neq \operatorname{argmax}(p^{(t+1)})$.

---

## 8. Files & Modules
- `config/regimes.yaml`: Canonical definition specifications.
- `ml/regimes/__init__.py`: Package export interface.
- `ml/regimes/definitions.py`: `WeatherRegime`, `LabelSource`, `LabelQuality`, `UncertaintyLevel`, `TransitionState`.
- `ml/regimes/indicators.py`: `RegimeIndicatorEngine`.
- `ml/regimes/weak_labeler.py`: `RegimeLabeler`.
- `ml/regimes/authoritative.py`: `AuthoritativeRegimeLabelProvider`.
- `ml/regimes/classifier.py`: Candidate classifiers.
- `ml/regimes/calibration.py`: `RegimeCalibrator`.
- `ml/regimes/uncertainty.py`: `UncertaintyEngine`.
- `ml/regimes/transition.py`: `RegimeTransitionDetector`.
- `ml/regimes/ensemble_regime.py`: `EnsembleRegimeEvaluator`.
- `ml/regimes/model_registry.py`: `RegimeModelRegistry`, `RegimeModelMetadata`.
- `ml/regimes/inference.py`: `RegimeInferenceService`.
- `ml/regimes/train.py`: Training, calibration, evaluation, artifact export script.
- `backend/src/ramp/api/v1/regime.py`: 8 REST endpoints.
- `frontend/src/pages/WeatherRegimes.tsx`: Frontend dashboard view.

---

## 9. APIs
| Endpoint | Method | Description |
|---|---|---|
| `/api/regime/status` | GET | Engine status, active model, honest real data flag, 7 regimes |
| `/api/regime/models` | GET | Model registry catalogue and hyperparameters |
| `/api/regime/current` | GET | Latest forecast probability vector, entropy, top regime |
| `/api/regime/grid` | GET | Gridded 0.25° spatial probability layers across India |
| `/api/regime/{sample_id}` | GET | Single-sample prediction, attribution, and confidence |
| `/api/regime/metrics` | GET | Classification accuracy, balanced accuracy, F1, confusion matrix |
| `/api/regime/calibration` | GET | Validation calibration report (uncalibrated vs calibrated Brier/log-loss) |
| `/api/regime/transitions` | GET | Sequential transition trajectory and trajectory state |

---

## 10. Frontend
- **Regime Probability Vector:** Color-coded probability bars for all 7 regimes with exact percentages summing to 100.0%.
- **Top Regime Card:** Dominant regime name, confidence %, Shannon entropy (bits), and normalized entropy.
- **Uncertainty Badge:** Color-coded `LOW`, `MEDIUM`, or `HIGH` uncertainty pill.
- **"Why this regime?" Section:** Top model-attribution features with disclaimer: *"Feature attribution reflects model importance and does not prove meteorological causality."*
- **Sequential Transition Timeline:** $T_0 \to T_{12} \to T_{24} \to T_{36}$ probability evolution with TVD shift flags.
- **Spatial Grid Preview:** Tabbed selector displaying layers (`top_regime`, `p_active`, `p_break`, `p_low_dep`, etc.) across canonical latitude/longitude points.
- **Validation Diagnostics:** Uncalibrated vs calibrated Brier scores and confusion matrix.
- **Persistent Banner:** Prominent amber notice declaring `REAL TRAINING DATA: NOT AVAILABLE (SYNTHETIC DEMO)`.

---

## 11. Testing
- 41 unit and integration tests in:
  - `backend/tests/unit/regimes/test_regime_definitions.py` (3 tests)
  - `backend/tests/unit/regimes/test_indicators.py` (7 tests)
  - `backend/tests/unit/regimes/test_weak_labeler.py` (3 tests)
  - `backend/tests/unit/regimes/test_calibration.py` (3 tests)
  - `backend/tests/unit/regimes/test_uncertainty.py` (4 tests)
  - `backend/tests/unit/regimes/test_transition.py` (3 tests)
  - `backend/tests/unit/regimes/test_ensemble_regime.py` (2 tests)
  - `backend/tests/unit/regimes/test_classifier_and_leakage.py` (4 tests)
  - `backend/tests/unit/regimes/test_inference_and_registry.py` (4 tests)
  - `backend/tests/integration/test_regime_api.py` (8 tests)

---

## 12. Actual Results
- **All 41 Phase 4 tests PASSED (100% pass rate).**
- **Cumulative test suite: 184 tests PASSED, 0 failures.**
- **Frontend production build (`tsc && vite build`) passed with 0 errors.**
- **Trained Model Candidate:** `regime_lgbm_v0.1.0` (LightGBM).
- **Validation Metrics (Synthetic Demonstration):**
  - Accuracy: 94.2%
  - Balanced Accuracy: 92.6%
  - Macro F1: 0.918
  - Weighted F1: 0.941
  - Calibrated Brier Score: 0.1568
- **Invariant Audit:** Every generated probability vector satisfies $\sum_{i=1}^7 p_i = 1.0 \pm 10^{-5}$.

---

## 13. Real vs Synthetic Status
- **REAL TRAINING DATA: NOT AVAILABLE**.
- All metrics are explicitly tagged `SYNTHETIC DEMONSTRATION ONLY`.
- The architecture is identical for real and synthetic modes. When real IMD/NCMRWF NetCDF files are placed in storage, the exact same training script (`python -m ml.regimes.train`) will execute without code changes.

---

## 14. Limitations
- Classification boundaries reflect weak-rule and synthetic simulation dynamics. Real atmospheric regimes exhibit mesoscale nuances not captured in low-resolution synthetic fields.
- Radar reflectivity and satellite IR channels are currently absent from indicator scoring.
- Demarcation of coastal and orographic boundaries uses spatial bounding corridors rather than fine-scale digital elevation rasters.

---

## 15. Security / Leakage Considerations
- `LeakageGuard` strictly forbids future observation variables (`observed_rainfall_mm`, `log_observed_rainfall`, `rain_flag`, `heavy_rainfall`, `very_heavy_rainfall`, `extremely_heavy_rainfall`) from entering predictor matrices.
- Probability calibration is fitted **strictly on the validation split**; fitting on test or train partitions raises `ValueError (Data Leakage Violation)`.
- Models are serialized safely via native formats / `joblib` within controlled local project paths.

---

## 16. Reproducibility
```bash
# 1. Train regime models, calibrate on validation split, and export artifacts:
$env:PYTHONPATH=".;backend/src"
python -m ml.regimes.train

# 2. Run Phase 4 unit and integration tests:
python -m pytest backend/tests/unit/regimes/ backend/tests/integration/test_regime_api.py -v

# 3. Run entire project test suite (184 tests):
python -m pytest backend/tests/ -q

# 4. Verify frontend TypeScript compilation and production build:
cd frontend
npm run build
```

---

## 17. Outputs
- `data/models/regime/regime_lgbm_v0.1.0/classifier.joblib`
- `data/models/regime/regime_lgbm_v0.1.0/calibrator.joblib`
- `data/models/regime/regime_lgbm_v0.1.0/model_metadata.json`
- `data/models/regime/regime_lgbm_v0.1.0/regime_metrics.json`
- `data/models/regime/regime_lgbm_v0.1.0/regime_confusion_matrix.json`
- `data/models/regime/regime_lgbm_v0.1.0/regime_calibration.json`
- `data/models/regime/regime_lgbm_v0.1.0/regime_transition_report.json`
- `data/models/regime/regime_lgbm_v0.1.0/regime_distribution.json`
- `data/models/regime/regime_lgbm_v0.1.0/REGIME_MODEL_CARD.md`
- `REGIME_MODEL_CARD.md` (root reference)

---

## 18. Next Phase Dependency
Phase 4 produces the **Regime Probability Vector** ($P(\text{regime})$) and regime indicators required for:
1. **Phase 5 (Baseline Post-Processing):** Evaluating raw NWP, mean bias, quantile mapping, and global ML baselines to establish benchmarks against which regime-conditioned corrections will be compared.
2. **Phase 6 (RAMP Mixture-of-Experts):** Supplying the soft gating weights ($p_1 \dots p_7$) to combine regime-specific expert post-processors into a single convex combination:
   $$\hat{R}_{\text{RAMP}}(x) = \sum_{k=1}^{7} p_k(x) \cdot \operatorname{Expert}_k(x)$$
