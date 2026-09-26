/**
 * Typed API Contracts for RAMP Frontend
 * SIH26080 | Synchronized with Backend Data Contracts
 */

export type DataMode = 'SYNTHETIC_DEMO' | 'REAL';

export type RegimeType =
  | 'ACTIVE_MONSOON'
  | 'BREAK_MONSOON'
  | 'MONSOON_LOW_DEPRESSION'
  | 'COASTAL_RAINFALL'
  | 'OROGRAPHIC_RAINFALL'
  | 'WESTERN_DISTURBANCE'
  | 'TRANSITION_OTHER';

export type BaselineModel =
  | 'raw_nwp'
  | 'mean_bias'
  | 'qmap'
  | 'global_ml'
  | 'ramp';

export interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
  environment: string;
  data_mode: DataMode;
}

export interface SystemInfoResponse {
  app_name: string;
  description: string;
  version: string;
  environment: string;
  organization: string;
  department: string;
  data_mode: DataMode;
  active_regimes: RegimeType[];
  imd_thresholds_mm_per_24h: {
    heavy: number;
    very_heavy: number;
    extremely_heavy: number;
  };
  supported_baselines: BaselineModel[];
  pipeline_stages: string[];
}

export interface RegimeProbabilityResponse {
  forecast_id: string;
  probabilities: Record<RegimeType, number>;
  dominant_regime: RegimeType;
  entropy: number;
  data_mode: DataMode;
  timestamp: string;
}

export interface ExtremeProbabilityResponse {
  forecast_id: string;
  prob_heavy_gte_64_5mm: number;
  prob_very_heavy_gte_115_6mm: number;
  prob_extremely_heavy_gte_204_5mm: number;
  data_mode: DataMode;
}

export interface VerificationScoreResponse {
  model_name: BaselineModel;
  date_range_start: string;
  date_range_end: string;
  rmse: number;
  csi_heavy: number;
  pod_heavy: number;
  far_heavy: number;
  ets_heavy: number;
  fss_50km: number;
  data_mode: DataMode;
}

export interface RegimeStatusData {
  status: string;
  active_model: string;
  data_mode: string;
  real_data_available: boolean;
  num_regimes: number;
  regimes: string[];
}

export interface RegimePredictionData {
  top_regime: string;
  probabilities: Record<string, number>;
  confidence: number;
  entropy: number;
  normalized_entropy: number;
  uncertainty_level: 'LOW' | 'MEDIUM' | 'HIGH';
  transition_state: string;
  model_version: string;
  feature_availability: Record<string, boolean>;
  top_attribution_features: Array<{ feature: string; importance: number }>;
}

export interface RegimeMetricsData {
  model_id: string;
  data_mode: string;
  performance_notice: string;
  metrics: {
    accuracy: number;
    balanced_accuracy: number;
    macro_f1: number;
    weighted_f1: number;
    test_samples: number;
  };
  confusion_matrix: Record<string, Record<string, number>>;
  class_distribution: Record<string, { count: number; percentage: number }>;
}

export interface RegimeCalibrationData {
  calibration_method: string;
  fitted_on: string;
  uncalibrated: { brier_score: number; log_loss: number };
  calibrated: { brier_score: number; log_loss: number };
}

export interface RegimeTransitionItem {
  from_step: string;
  to_step: string;
  from_regime: string;
  to_regime: string;
  tvd: number;
  regime_switched: boolean;
  is_transition: boolean;
  prob_prev: number[];
  prob_curr: number[];
}

export interface RegimeTransitionsData {
  transition_state: string;
  transitions_detected: number;
  max_tvd: number;
  history: RegimeTransitionItem[];
}

export interface RegimeGridData {
  total_points: number;
  latitudes: number[];
  longitudes: number[];
  top_regimes: string[];
  entropy: number[];
  normalized_entropy: number[];
  layers: Record<string, number[]>;
}

export interface BaselineStatusData {
  status: string;
  data_mode: string;
  real_data_available: boolean;
  models_available: string[];
  dataset_version: string;
}

export interface BaselineBenchmarkItem {
  model: string;
  rmse: number;
  mae: number;
  mean_bias: number;
  pearson_r: number;
  rain_occurrence_csi: number | null;
  heavy_rain_csi_64_5: number | null;
  heavy_rain_pod_64_5: number | null;
  heavy_rain_far_64_5: number | null;
  heavy_rain_ets_64_5: number | null;
  very_heavy_csi_115_6: number | null;
  extremely_heavy_csi_204_5: number | null;
}

export interface BaselineBenchmarkData {
  evaluation_timestamp: string;
  data_mode: string;
  performance_notice: string;
  dataset_version: string;
  test_sample_count: number;
  benchmark_matrix: BaselineBenchmarkItem[];
  overall_metrics: Record<string, any>;
  threshold_metrics: Record<string, any>;
  lead_time_metrics: Record<string, any>;
  regime_metrics: Record<string, any>;
  spatial_metrics: Record<string, any>;
  bootstrap_significance: Record<string, any>;
}

// ==========================================
// RAMP Mixture-of-Experts Contracts
// ==========================================

export interface RAMPStatusData {
  status: string;
  data_mode: string;
  real_data_available: boolean;
  performance_notice: string;
  active_model_id: string;
  phase4_regime_model: string;
  phase5_baseline_model: string;
  expert_count: number;
  fallback_count: number;
  dataset_version: string;
}

export interface RAMPPredictionData {
  sample_id: string;
  forecast_valid_time: string;
  latitude: number;
  longitude: number;
  lead_time_hours: number;
  raw_nwp_prediction: number;
  global_ml_prediction: number;
  ramp_prediction: number;
  gate_probabilities: Record<string, number>;
  expert_predictions: Record<string, number>;
  weighted_contributions: Record<string, number>;
  top_regime: string;
  top_probability: number;
  entropy: number;
  uncertainty: string;
  transition_state: string;
  fallback_used: boolean;
  expert_sources: Record<string, string>;
  data_mode: string;
  model_version: string;
  observed_rainfall?: number | null;
}

export interface RAMPBenchmarkItem {
  model: string;
  rmse: number;
  mae: number;
  mean_bias: number;
  pearson_r: number;
  rain_occurrence_csi: number | null;
  heavy_rain_csi_64_5: number | null;
  heavy_rain_pod_64_5: number | null;
  heavy_rain_far_64_5: number | null;
  heavy_rain_ets_64_5: number | null;
  very_heavy_csi_115_6: number | null;
  extremely_heavy_csi_204_5: number | null;
}

export interface RAMPBenchmarkData {
  data_mode: string;
  performance_notice: string;
  test_sample_count: number;
  benchmark_matrix: RAMPBenchmarkItem[];
  bootstrap_significance: Record<string, any>;
  systems_evaluated: string[];
}

export interface RAMPExpertItem {
  regime: string;
  status: string;
  train_samples: number;
  train_rmse: number | null;
  top_features: Array<[string, number]>;
}

export interface RAMPGatingSample {
  sample_id: string;
  top_regime: string;
  top_probability: number;
  entropy: number;
  uncertainty: string;
  gate_weights: Record<string, number>;
}

export interface RAMPGatingData {
  data_mode: string;
  performance_notice: string;
  diagnostics: {
    sample_count: number;
    high_uncertainty_samples: number;
    mean_entropy: number;
    samples: RAMPGatingSample[];
  };
}

export interface RAMPAblationRow {
  ablation_tier: string;
  rmse: number;
  mae: number;
  mean_bias: number;
  heavy_rain_csi_64_5: number | null;
  heavy_rain_pod_64_5: number | null;
  heavy_rain_ets_64_5: number | null;
}

export interface RAMPDiagnosticsData {
  data_mode: string;
  expert_diversity: {
    num_evaluated_experts: number;
    correlation_matrix: Record<string, Record<string, number>>;
    specialization_summary: string;
  };
  ablation_comparison: RAMPAblationRow[];
}


// =============================================================================
// Phase 7 — Extreme Rainfall Probability Engine
// =============================================================================

export interface ExtremeEngineStatus {
  engine_version: string;
  ramp_source_version: string;
  data_mode: string;
  data_mode_banner: string;
  n_thresholds: number;
  thresholds: number[];
  models_status: Record<string, boolean>;
  all_fitted: boolean;
  monotonicity_enforced: boolean;
  calibration_applied: boolean;
  last_trained_at: string | null;
  operational: boolean;
  warnings: string[];
}

export interface ExtremeModelMeta {
  threshold_mm: number;
  threshold_label: string;
  model_type: string;
  version: string;
  calibration_method: string;
  is_fitted: boolean;
  train_n_samples: number;
  train_n_events: number;
  train_event_rate: number;
  val_brier_score: number;
  val_roc_auc: number;
  val_pr_auc: number;
  val_ece: number;
  sample_size_warning: boolean;
  feature_count: number;
  feature_names: string[];
}

export interface ProbabilityThresholdResult {
  threshold_mm: number;
  threshold_label: string;
  imd_warning_color: string;
  raw_probability: number;
  calibrated_probability: number;
  calibration_method: string;
  top_features: Record<string, number>;
  train_event_rate: number;
  train_n_events: number;
  train_n_total: number;
  sample_size_warning: boolean;
  probability_lower: number;
  probability_upper: number;
}

export interface ExtremePredictionRecord {
  sample_id: string;
  forecast_valid_time: string;
  latitude: number;
  longitude: number;
  lead_time_hours: number;
  ramp_prediction_mm: number;
  raw_nwp_prediction_mm: number;
  top_regime: string;
  regime_confidence: number;
  p_trace: number;
  p_heavy: number;
  p_very_heavy: number;
  p_extreme: number;
  threshold_results: ProbabilityThresholdResult[];
  monotonicity_satisfied: boolean;
  monotonicity_corrections_applied: number;
  composite_risk_index: number;
  risk_category: string;
  imd_warning_recommendation: string;
  model_version: string;
  data_mode: string;
  computed_at: string;
}

export interface ExtremeMetric {
  threshold_mm: number;
  threshold_label: string;
  roc_auc: number;
  pr_auc: number;
  brier_score: number;
  brier_skill_score: number;
  expected_calibration_error: number;
  train_n_events: number;
  train_event_rate: number;
  sample_size_warning: boolean;
  data_mode: string;
}

export interface CalibrationBin {
  threshold_mm: number;
  bin_confidence: number[];
  bin_accuracy: number[];
  bin_counts: number[];
  ece: number;
}

export interface BrierScoreRow {
  threshold_mm: number;
  threshold_label: string;
  brier_score: number;
  brier_reference: number;
  brier_skill_score: number;
  skill_vs_raw_nwp: number;
  skill_vs_ramp_deterministic: number;
}

export interface PRCurveDataPoint {
  threshold_mm: number;
  precision: number[];
  recall: number[];
  pr_auc: number;
  baseline_precision: number;
  skill_vs_random: number;
}

export interface ExtremeFeatureImportance {
  threshold_mm: number;
  threshold_label: string;
  top_features: Record<string, number>;
  n_total_features: number;
}

export interface MonotonicityReport {
  monotonicity_invariant: string;
  reconciliation_algorithm: string;
  n_samples_checked: number;
  violation_rate_before_reconciliation: number;
  violation_rate_after_reconciliation: number;
  total_corrections_applied: number;
  invariant_satisfied: boolean;
  guarantee: string;
}

// ---------------------------------------------------------------------------
// Phase 8 Operational Verification & Real-Data Integration Types
// ---------------------------------------------------------------------------

export interface OperationalStatusResponse {
  status: string;
  data_mode: 'REAL' | 'SYNTHETIC_DEMO';
  is_real_data_available: boolean;
  readiness_level: number;
  readiness_level_name: string;
  banner_message: string;
  active_provider: string;
  model_versions: {
    ramp_moe: string;
    extreme_probability: string;
    regime_intelligence: string;
    baselines: Record<string, string>;
  };
  freeze_status: Record<string, string>;
}

export interface OperationalDataResponse {
  active_provider: string;
  data_mode: string;
  is_real_data_available: boolean;
  adapters_supported: Array<{
    format: string;
    engine: string;
    status: string;
  }>;
  discovery_summary: {
    total_files_scanned: number;
    netcdf_files: number;
    grib_files: number;
    parquet_files: number;
    csv_files: number;
    discovered_variables: string[];
    time_range: { start?: string; end?: string };
  };
}

export interface QualityCheckItem {
  check_id: number;
  name: string;
  passed: boolean;
  severity: string;
  affected_count: number;
  details: string;
}

export interface OperationalQualityResponse {
  dataset_id: string;
  data_mode: string;
  overall_status: string;
  total_records: number;
  valid_records: number;
  invalid_records: number;
  duplicate_records: number;
  missing_target_records: number;
  physical_invalid_rain_count: number;
  extreme_but_valid_rain_count: number;
  checks: QualityCheckItem[];
  rejection_reasons: Record<string, number>;
}

export interface OperationalDatasetResponse {
  manifest: {
    dataset_id: string;
    dataset_version: string;
    mode: string;
    source: string;
    variables: string[];
    start_date: string;
    end_date: string;
    spatial_extent: { lat_min: number; lat_max: number; lon_min: number; lon_max: number };
    resolution: string;
    lead_times: number[];
    quality_status: string;
    total_records: number;
    valid_records: number;
    notes?: string;
  };
  contract: Record<string, any>;
}

export interface OperationalCoverageResponse {
  time_coverage: { start?: string; end?: string; unique_cycles?: number };
  spatial_coverage: {
    lat_min?: number;
    lat_max?: number;
    lon_min?: number;
    lon_max?: number;
    unique_grid_cells?: number;
  };
  variable_coverage: Record<string, number>;
  lead_time_coverage: number[];
}

export interface BenchmarkMatrixRow {
  system: string;
  rmse: number;
  mae: number;
  mean_bias: number;
  pearson_r: number;
  rain_csi: number;
  heavy_csi: number;
  very_heavy_csi: number;
  extreme_csi: number;
  heavy_pod: number;
  heavy_far: number;
  heavy_ets: number;
  brier_heavy: number;
  pr_auc: number;
  ece: number;
}

export interface OperationalVerificationResponse {
  dataset_id: string;
  data_mode: string;
  verified_at: string;
  sample_count: number;
  continuous_metrics: Record<string, { rmse: number; mae: number; mean_bias: number; pearson_r: number }>;
  bootstrap: {
    ramp_vs_raw_nwp: {
      status: string;
      mean_mae_diff?: number;
      ci_95?: [number, number];
      p_value?: number;
      resamples_run?: number;
      is_significant?: boolean;
    };
    ramp_vs_global_ml: {
      status: string;
      mean_mae_diff?: number;
      ci_95?: [number, number];
      p_value?: number;
      resamples_run?: number;
      is_significant?: boolean;
    };
  };
  benchmark_matrix: BenchmarkMatrixRow[];
}

export interface OperationalThresholdResponse {
  thresholds: Record<string, Record<string, {
    threshold_mm: number;
    hits: number;
    false_alarms: number;
    misses: number;
    correct_negatives: number;
    pod: number;
    far: number;
    csi: number;
    ets: number;
    fbias: number;
  }>>;
  extreme_events: Array<{
    threshold_mm: number;
    category: string;
    event_count: number;
    base_rate: number;
    brier_score: number;
    pr_auc: number;
    roc_auc: number;
    pod: number;
    far: number;
    csi: number;
    ets: number;
  }>;
}

export interface OperationalRegimeResponse {
  regimes: Record<string, {
    regime: string;
    sample_count: number;
    status: string;
    rmse?: number;
    mae?: number;
    mean_bias?: number;
    heavy_csi?: number;
    heavy_pod?: number;
    heavy_far?: number;
    message?: string;
  }>;
}

export interface OperationalLeadTimeResponse {
  lead_times: Record<string, {
    lead_day: string;
    lead_hours: number;
    sample_count: number;
    rmse: number;
    mae: number;
    heavy_csi: number;
    heavy_pod: number;
    brier_heavy: number;
  }>;
}

export interface SpatialGridCellPoint {
  latitude: number;
  longitude: number;
  sample_count: number;
  rmse: number;
  mae: number;
  mean_bias: number;
  heavy_csi: number;
  heavy_pod: number;
  heavy_far: number;
}

export interface OperationalSpatialResponse {
  grid_cells: SpatialGridCellPoint[];
  total_cells: number;
}

export interface OperationalCalibrationResponse {
  calibration: Record<string, {
    threshold_mm: number;
    base_rate: number;
    n_events: number;
    raw_nwp_brier: number;
    ramp_prob_brier: number;
    bss_vs_climatology: number;
    ece: number;
    mce: number;
    roc_auc: number;
    pr_auc: number;
  }>;
}

export interface OperationalLeakageResponse {
  status: string;
  checks_run: number;
  passed_checks: string[];
  violations: string[];
  checked_at: string;
  forbidden_invariants: string[];
}

export interface OperationalModelsResponse {
  registry_version: string;
  last_updated: string;
  ramp_version: string;
  extreme_prob_version: string;
  regime_version: string;
  dataset_version: string;
  feature_schema: string;
  calibration_version: string;
  total_registered_models: number;
  models: Array<{
    phase: number;
    system_name: string;
    version_id: string;
    status: string;
    data_mode: string;
    trained_at: string;
    artifact_path?: string;
    metrics_summary: Record<string, number>;
    notes?: string;
  }>;
}

export interface ReadinessTierItem {
  level: number;
  name: string;
  description: string;
  status: 'ACHIEVED' | 'CURRENT_ACTIVE' | 'IN_PROGRESS' | 'NOT_STARTED';
  criteria_met: string[];
  pending_criteria: string[];
}

export interface OperationalReadinessResponse {
  current_level: number;
  current_level_name: string;
  data_mode: string;
  is_real_data_available: boolean;
  summary: string;
  disclaimer: string;
  tiers: ReadinessTierItem[];
}

// ---------------------------------------------------------------------------
// Phase 9 Spatial Forecast Products & District Aggregation Contracts
// ---------------------------------------------------------------------------

export type RiskCategory =
  | 'NORMAL'
  | 'WATCH'
  | 'HIGH_RAINFALL'
  | 'VERY_HIGH_RAINFALL'
  | 'EXTREME_RAINFALL';

export interface DistrictForecastProductItem {
  product_id: string;
  district_id: string;
  district_name: string;
  state_id: string;
  state_name: string;
  forecast_valid_time: string;
  initialization_time: string;
  lead_time_hours: number;
  aggregation_method: string;
  rainfall_mm: number;
  min_rainfall_mm: number;
  max_rainfall_mm: number;
  median_rainfall_mm: number;
  p90_rainfall_mm: number;
  p95_rainfall_mm: number;
  p99_rainfall_mm: number;
  rain_probability: number;
  heavy_probability: number;
  very_heavy_probability: number;
  extreme_probability: number;
  hotspot_latitude: number;
  hotspot_longitude: number;
  hotspot_rainfall_mm: number;
  valid_grid_cells: number;
  total_grid_cells: number;
  coverage_fraction: number;
  regime_distribution: Record<string, number>;
  uncertainty: {
    uncertainty_available: boolean;
    spatial_std_mm?: number;
    coverage_fraction?: number;
    coverage_penalty?: number;
    composite_uncertainty_score?: number;
    uncertainty_tier?: string;
    reason?: string;
  };
  model_version: string;
  dataset_version: string;
  data_mode: string;
  boundary_version: string;
  raw_nwp_rainfall_mm: number;
  global_ml_rainfall_mm: number;
  difference_nwp_mm: number;
  difference_global_ml_mm: number;
  risk_category: RiskCategory;
  risk_description: string;
  color_hex: string;
  hotspot_intensity: number;
  max_heavy_probability: number;
  max_extreme_probability: number;
  high_risk_cells_count: number;
  area_km2: number;
  classification_rule: string;
}

export interface SpatialStatusResponse {
  status: string;
  data_mode: string;
  banner: string;
  product_version: string;
  model_version: string;
  extreme_prob_version: string;
  regime_version: string;
  boundary_metadata: {
    boundary_dataset_id: string;
    boundary_dataset_version: string;
    source: string;
    geographic_crs: string;
    projected_crs: string;
    total_districts: number;
    total_states: number;
  };
  default_lead_time_hours: number;
  supported_lead_days: string[];
  default_aggregation_method: string;
  geographic_crs: string;
  projected_crs: string;
  timestamp: string;
}

export interface SpatialDistrictsResponse {
  data_mode: string;
  banner: string;
  lead_time_hours: number;
  total_districts: number;
  aggregation_method: string;
  model_version: string;
  boundary_version: string;
  districts: DistrictForecastProductItem[];
}

export interface StateForecastProductItem {
  state_id: string;
  state_name: string;
  forecast_valid_time: string;
  lead_time_hours: number;
  district_count: number;
  total_area_km2: number;
  area_weighted_rainfall_mm: number;
  max_district_rainfall_mm: number;
  max_rainfall_district: string;
  mean_rainfall_mm: number;
  high_risk_districts: number;
  very_high_risk_districts: number;
  extreme_risk_districts: number;
  mean_heavy_probability: number;
  mean_extreme_probability: number;
  districts: DistrictForecastProductItem[];
  data_mode: string;
  model_version: string;
}

export interface SpatialStatesResponse {
  data_mode: string;
  lead_time_hours: number;
  total_states: number;
  states: StateForecastProductItem[];
}

export interface NationalSummaryResponse {
  forecast_valid_time: string;
  lead_time_hours: number;
  data_mode: string;
  model_version: string;
  boundary_version: string;
  total_districts_evaluated: number;
  total_states_evaluated: number;
  valid_grid_cells: number;
  overall_coverage_pct: number;
  districts_with_heavy_probability: number;
  districts_with_very_heavy_probability: number;
  districts_with_extreme_probability: number;
  max_predicted_district_rainfall_mm: number;
  max_rainfall_district_name: string;
  max_rainfall_state_name: string;
  highest_risk_spatial_region: string;
  risk_category_counts: Record<string, number>;
  generated_at: string;
}

export interface HotspotItem {
  district_id: string;
  district_name: string;
  state_name: string;
  hotspot_latitude: number;
  hotspot_longitude: number;
  hotspot_rainfall_mm: number;
  district_mean_mm: number;
  hotspot_intensity: number;
  max_heavy_prob: number;
  max_extreme_prob: number;
  risk_category: string;
}

export interface HotspotsResponse {
  data_mode: string;
  lead_time_hours: number;
  total_hotspots: number;
  hotspots: HotspotItem[];
}

export interface SpatialDifferenceItem {
  district_id: string;
  district_name: string;
  state_name: string;
  ramp_rainfall_mm: number;
  raw_nwp_rainfall_mm: number;
  global_ml_rainfall_mm: number;
  difference_nwp_mm: number;
  difference_global_ml_mm: number;
  correction_type: string;
}

export interface SpatialDifferenceResponse {
  data_mode: string;
  lead_time_hours: number;
  units: string;
  differences: SpatialDifferenceItem[];
}

export interface SpatialFSSResponse {
  status: string;
  message?: string;
  thresholds?: number[];
  scales?: string[];
  fss_curves: Record<string, Record<string, {
    fss: number;
    mse: number;
    mse_ref: number;
    forecast_fraction: number;
    observed_fraction: number;
    sample_count: number;
    status: string;
  }>>;
}

export interface SpatialExportResponse {
  status: string;
  data_mode: string;
  lead_time_hours: number;
  files: {
    geojson: string;
    csv: string;
    parquet: string;
  };
  generated_at: string;
  total_districts: number;
}

