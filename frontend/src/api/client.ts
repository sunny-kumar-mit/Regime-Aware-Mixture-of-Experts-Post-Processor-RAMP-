/**
 * RAMP API Client
 * SIH26080 | Type-safe fetch wrappers
 */

import { HealthResponse, SystemInfoResponse } from '../types/api';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSystemInfo(): Promise<SystemInfoResponse> {
  const res = await fetch(`${API_BASE}/api/system/info`);
  if (!res.ok) {
    throw new Error(`Failed to fetch system info: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRegimeStatus(): Promise<import('../types/api').RegimeStatusData> {
  const res = await fetch(`${API_BASE}/api/regime/status`);
  if (!res.ok) throw new Error(`Regime status failed: ${res.status}`);
  return res.json();
}

export async function fetchCurrentRegime(): Promise<import('../types/api').RegimePredictionData> {
  const res = await fetch(`${API_BASE}/api/regime/current`);
  if (!res.ok) throw new Error(`Current regime failed: ${res.status}`);
  return res.json();
}

export async function fetchRegimeMetrics(): Promise<import('../types/api').RegimeMetricsData> {
  const res = await fetch(`${API_BASE}/api/regime/metrics`);
  if (!res.ok) throw new Error(`Regime metrics failed: ${res.status}`);
  return res.json();
}

export async function fetchRegimeCalibration(): Promise<import('../types/api').RegimeCalibrationData> {
  const res = await fetch(`${API_BASE}/api/regime/calibration`);
  if (!res.ok) throw new Error(`Regime calibration failed: ${res.status}`);
  return res.json();
}

export async function fetchRegimeTransitions(): Promise<import('../types/api').RegimeTransitionsData> {
  const res = await fetch(`${API_BASE}/api/regime/transitions`);
  if (!res.ok) throw new Error(`Regime transitions failed: ${res.status}`);
  return res.json();
}

export async function fetchRegimeGrid(): Promise<import('../types/api').RegimeGridData> {
  const res = await fetch(`${API_BASE}/api/regime/grid`);
  if (!res.ok) throw new Error(`Regime grid failed: ${res.status}`);
  return res.json();
}

export async function fetchBaselineStatus(): Promise<import('../types/api').BaselineStatusData> {
  const res = await fetch(`${API_BASE}/api/baselines/status`);
  if (!res.ok) throw new Error(`Baseline status failed: ${res.status}`);
  return res.json();
}

export async function fetchBaselineBenchmark(): Promise<import('../types/api').BaselineBenchmarkData> {
  const res = await fetch(`${API_BASE}/api/baselines/benchmark`);
  if (!res.ok) throw new Error(`Baseline benchmark failed: ${res.status}`);
  return res.json();
}

export async function fetchBaselineLeadTime(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/baselines/metrics/lead-time`);
  if (!res.ok) throw new Error(`Baseline lead-time metrics failed: ${res.status}`);
  return res.json();
}

export async function fetchBaselineRegimes(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/baselines/metrics/regime`);
  if (!res.ok) throw new Error(`Baseline regime diagnostics failed: ${res.status}`);
  return res.json();
}

export async function fetchBaselineSpatial(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/baselines/spatial`);
  if (!res.ok) throw new Error(`Baseline spatial metrics failed: ${res.status}`);
  return res.json();
}

// ==========================================
// RAMP Mixture-of-Experts API Functions
// ==========================================

export async function fetchRAMPStatus(): Promise<import('../types/api').RAMPStatusData> {
  const res = await fetch(`${API_BASE}/api/ramp/status`);
  if (!res.ok) throw new Error(`RAMP status failed: ${res.status}`);
  return res.json();
}

export async function fetchRAMPBenchmark(): Promise<import('../types/api').RAMPBenchmarkData> {
  const res = await fetch(`${API_BASE}/api/ramp/benchmark`);
  if (!res.ok) throw new Error(`RAMP benchmark failed: ${res.status}`);
  return res.json();
}

export async function fetchRAMPPrediction(sampleId: string): Promise<import('../types/api').RAMPPredictionData> {
  const res = await fetch(`${API_BASE}/api/ramp/prediction/${sampleId}`);
  if (!res.ok) throw new Error(`RAMP prediction failed: ${res.status}`);
  return res.json();
}

export async function fetchRAMPExperts(): Promise<{ data_mode: string; experts: Record<string, import('../types/api').RAMPExpertItem> }> {
  const res = await fetch(`${API_BASE}/api/ramp/experts`);
  if (!res.ok) throw new Error(`RAMP experts failed: ${res.status}`);
  return res.json();
}

export async function fetchRAMPGating(): Promise<import('../types/api').RAMPGatingData> {
  const res = await fetch(`${API_BASE}/api/ramp/gating`);
  if (!res.ok) throw new Error(`RAMP gating failed: ${res.status}`);
  return res.json();
}

export async function fetchRAMPLeadTime(): Promise<{ data_mode: string; lead_time_metrics: Record<string, any> }> {
  const res = await fetch(`${API_BASE}/api/ramp/metrics/lead-time`);
  if (!res.ok) throw new Error(`RAMP lead-time metrics failed: ${res.status}`);
  return res.json();
}

export async function fetchRAMPThresholds(): Promise<{ data_mode: string; threshold_metrics: Record<string, any> }> {
  const res = await fetch(`${API_BASE}/api/ramp/metrics/threshold`);
  if (!res.ok) throw new Error(`RAMP threshold metrics failed: ${res.status}`);
  return res.json();
}

export async function fetchRAMPRegimes(): Promise<{ data_mode: string; regime_metrics: Record<string, any> }> {
  const res = await fetch(`${API_BASE}/api/ramp/metrics/regime`);
  if (!res.ok) throw new Error(`RAMP regime metrics failed: ${res.status}`);
  return res.json();
}

export async function fetchRAMPSpatial(): Promise<{ data_mode: string; spatial_metrics: Record<string, any> }> {
  const res = await fetch(`${API_BASE}/api/ramp/metrics/spatial`);
  if (!res.ok) throw new Error(`RAMP spatial metrics failed: ${res.status}`);
  return res.json();
}

export async function fetchRAMPDiagnostics(): Promise<import('../types/api').RAMPDiagnosticsData> {
  const res = await fetch(`${API_BASE}/api/ramp/diagnostics`);
  if (!res.ok) throw new Error(`RAMP diagnostics failed: ${res.status}`);
  return res.json();
}

// =============================================================================
// Phase 7 — Extreme Rainfall Probability Engine API Functions
// =============================================================================

export async function fetchExtremeStatus(): Promise<import('../types/api').ExtremeEngineStatus> {
  const res = await fetch(`${API_BASE}/api/extreme/status`);
  if (!res.ok) throw new Error(`Extreme status failed: ${res.status}`);
  return res.json();
}

export async function fetchExtremeModels(): Promise<{ data_mode: string; data_mode_banner: string; engine_version: string; n_models: number; models: import('../types/api').ExtremeModelMeta[] }> {
  const res = await fetch(`${API_BASE}/api/extreme/models`);
  if (!res.ok) throw new Error(`Extreme models failed: ${res.status}`);
  return res.json();
}

export async function fetchExtremeDemo(rampPrediction: number = 85, regime: string = 'ACTIVE_MONSOON', leadTimeHours: number = 48): Promise<import('../types/api').ExtremePredictionRecord & { data_mode_banner: string; scenario: Record<string, unknown> }> {
  const params = new URLSearchParams({
    ramp_prediction: String(rampPrediction),
    regime,
    lead_time_hours: String(leadTimeHours),
  });
  const res = await fetch(`${API_BASE}/api/extreme/predict/demo?${params}`);
  if (!res.ok) throw new Error(`Extreme demo prediction failed: ${res.status}`);
  return res.json();
}

export async function fetchExtremeMetrics(): Promise<{ data_mode: string; data_mode_banner: string; metrics: import('../types/api').ExtremeMetric[]; notes: string[] }> {
  const res = await fetch(`${API_BASE}/api/extreme/metrics`);
  if (!res.ok) throw new Error(`Extreme metrics failed: ${res.status}`);
  return res.json();
}

export async function fetchExtremeCalibration(): Promise<{ data_mode: string; data_mode_banner: string; calibration_method: string; calibration_split: string; thresholds: import('../types/api').CalibrationBin[] }> {
  const res = await fetch(`${API_BASE}/api/extreme/calibration`);
  if (!res.ok) throw new Error(`Extreme calibration failed: ${res.status}`);
  return res.json();
}

export async function fetchExtremeBrierScores(): Promise<{ data_mode: string; bss_ladder: import('../types/api').BrierScoreRow[]; reference_forecast: string; interpretation: string }> {
  const res = await fetch(`${API_BASE}/api/extreme/brier-scores`);
  if (!res.ok) throw new Error(`Extreme Brier scores failed: ${res.status}`);
  return res.json();
}

export async function fetchExtremePRCurves(): Promise<{ data_mode: string; data_mode_banner: string; note: string; curves: import('../types/api').PRCurveDataPoint[] }> {
  const res = await fetch(`${API_BASE}/api/extreme/pr-curves`);
  if (!res.ok) throw new Error(`Extreme PR curves failed: ${res.status}`);
  return res.json();
}

export async function fetchExtremeFeatureImportance(topN: number = 10): Promise<{ data_mode: string; importance_metric: string; note: string; thresholds: import('../types/api').ExtremeFeatureImportance[] }> {
  const res = await fetch(`${API_BASE}/api/extreme/feature-importance?top_n=${topN}`);
  if (!res.ok) throw new Error(`Extreme feature importance failed: ${res.status}`);
  return res.json();
}

export async function fetchExtremeMonotonicity(nSamples: number = 1000): Promise<import('../types/api').MonotonicityReport & { data_mode: string; data_mode_banner: string }> {
  const res = await fetch(`${API_BASE}/api/extreme/monotonicity?n_samples=${nSamples}`);
  if (!res.ok) throw new Error(`Monotonicity report failed: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Phase 8 Operational Verification Fetch Functions
// ---------------------------------------------------------------------------

export async function fetchOperationalStatus(): Promise<import('../types/api').OperationalStatusResponse> {
  const res = await fetch(`${API_BASE}/api/operational/status`);
  if (!res.ok) throw new Error(`Operational status failed: ${res.status}`);
  return res.json();
}

export async function fetchOperationalData(): Promise<import('../types/api').OperationalDataResponse> {
  const res = await fetch(`${API_BASE}/api/operational/data`);
  if (!res.ok) throw new Error(`Operational data failed: ${res.status}`);
  return res.json();
}

export async function fetchOperationalDataQuality(): Promise<import('../types/api').OperationalQualityResponse> {
  const res = await fetch(`${API_BASE}/api/operational/data-quality`);
  if (!res.ok) throw new Error(`Operational data quality failed: ${res.status}`);
  return res.json();
}

export async function fetchOperationalDataset(): Promise<import('../types/api').OperationalDatasetResponse> {
  const res = await fetch(`${API_BASE}/api/operational/dataset`);
  if (!res.ok) throw new Error(`Operational dataset failed: ${res.status}`);
  return res.json();
}

export async function fetchOperationalCoverage(): Promise<import('../types/api').OperationalCoverageResponse> {
  const res = await fetch(`${API_BASE}/api/operational/coverage`);
  if (!res.ok) throw new Error(`Operational coverage failed: ${res.status}`);
  return res.json();
}

export async function fetchOperationalVerification(): Promise<import('../types/api').OperationalVerificationResponse> {
  const res = await fetch(`${API_BASE}/api/operational/verification`);
  if (!res.ok) throw new Error(`Operational verification failed: ${res.status}`);
  return res.json();
}

export async function fetchOperationalThresholds(): Promise<import('../types/api').OperationalThresholdResponse> {
  const res = await fetch(`${API_BASE}/api/operational/verification/threshold`);
  if (!res.ok) throw new Error(`Operational thresholds failed: ${res.status}`);
  return res.json();
}

export async function fetchOperationalRegimes(): Promise<import('../types/api').OperationalRegimeResponse> {
  const res = await fetch(`${API_BASE}/api/operational/verification/regime`);
  if (!res.ok) throw new Error(`Operational regimes failed: ${res.status}`);
  return res.json();
}

export async function fetchOperationalLeadTimes(): Promise<import('../types/api').OperationalLeadTimeResponse> {
  const res = await fetch(`${API_BASE}/api/operational/verification/lead-time`);
  if (!res.ok) throw new Error(`Operational lead times failed: ${res.status}`);
  return res.json();
}

export async function fetchOperationalSpatial(): Promise<import('../types/api').OperationalSpatialResponse> {
  const res = await fetch(`${API_BASE}/api/operational/verification/spatial`);
  if (!res.ok) throw new Error(`Operational spatial failed: ${res.status}`);
  return res.json();
}

export async function fetchOperationalCalibration(): Promise<import('../types/api').OperationalCalibrationResponse> {
  const res = await fetch(`${API_BASE}/api/operational/calibration`);
  if (!res.ok) throw new Error(`Operational calibration failed: ${res.status}`);
  return res.json();
}

export async function fetchOperationalLeakage(): Promise<import('../types/api').OperationalLeakageResponse> {
  const res = await fetch(`${API_BASE}/api/operational/leakage`);
  if (!res.ok) throw new Error(`Operational leakage failed: ${res.status}`);
  return res.json();
}

export async function fetchOperationalModels(): Promise<import('../types/api').OperationalModelsResponse> {
  const res = await fetch(`${API_BASE}/api/operational/models`);
  if (!res.ok) throw new Error(`Operational models failed: ${res.status}`);
  return res.json();
}

export async function fetchOperationalReadiness(): Promise<import('../types/api').OperationalReadinessResponse> {
  const res = await fetch(`${API_BASE}/api/operational/readiness`);
  if (!res.ok) throw new Error(`Operational readiness failed: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Phase 9 Spatial Forecast Products & District Aggregation API Client
// ---------------------------------------------------------------------------

export async function fetchSpatialStatus(): Promise<import('../types/api').SpatialStatusResponse> {
  const res = await fetch(`${API_BASE}/api/spatial/status`);
  if (!res.ok) throw new Error(`Spatial status failed: ${res.status}`);
  return res.json();
}

export async function fetchSpatialGrid(leadHours: number = 24): Promise<{
  data_mode: string;
  lead_time_hours: number;
  total_cells: number;
  cells: any[];
}> {
  const res = await fetch(`${API_BASE}/api/spatial/grid?lead_hours=${leadHours}&limit=200`);
  if (!res.ok) throw new Error(`Spatial grid failed: ${res.status}`);
  return res.json();
}

export async function fetchSpatialDistricts(leadHours: number = 24, riskFilter?: string): Promise<import('../types/api').SpatialDistrictsResponse> {
  const url = riskFilter 
    ? `${API_BASE}/api/spatial/districts?lead_hours=${leadHours}&risk_filter=${encodeURIComponent(riskFilter)}`
    : `${API_BASE}/api/spatial/districts?lead_hours=${leadHours}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Spatial districts failed: ${res.status}`);
  return res.json();
}

export async function fetchDistrictDetail(districtId: string, leadHours: number = 24): Promise<{
  data_mode: string;
  product: import('../types/api').DistrictForecastProductItem;
  boundary_geometry: any;
  provenance: any;
}> {
  const res = await fetch(`${API_BASE}/api/spatial/district/${encodeURIComponent(districtId)}?lead_hours=${leadHours}`);
  if (!res.ok) throw new Error(`District detail failed: ${res.status}`);
  return res.json();
}

export async function fetchSpatialStates(leadHours: number = 24): Promise<import('../types/api').SpatialStatesResponse> {
  const res = await fetch(`${API_BASE}/api/spatial/states?lead_hours=${leadHours}`);
  if (!res.ok) throw new Error(`Spatial states failed: ${res.status}`);
  return res.json();
}

export async function fetchNationalSummary(leadHours: number = 24): Promise<import('../types/api').NationalSummaryResponse> {
  const res = await fetch(`${API_BASE}/api/spatial/summary?lead_hours=${leadHours}`);
  if (!res.ok) throw new Error(`National summary failed: ${res.status}`);
  return res.json();
}

export async function fetchSpatialProbabilities(leadHours: number = 24): Promise<{
  data_mode: string;
  lead_time_hours: number;
  probabilities: any[];
}> {
  const res = await fetch(`${API_BASE}/api/spatial/probability?lead_hours=${leadHours}`);
  if (!res.ok) throw new Error(`Spatial probabilities failed: ${res.status}`);
  return res.json();
}

export async function fetchSpatialHotspots(leadHours: number = 24): Promise<import('../types/api').HotspotsResponse> {
  const res = await fetch(`${API_BASE}/api/spatial/hotspots?lead_hours=${leadHours}`);
  if (!res.ok) throw new Error(`Spatial hotspots failed: ${res.status}`);
  return res.json();
}

export async function fetchSpatialRegimes(leadHours: number = 24): Promise<{
  data_mode: string;
  lead_time_hours: number;
  regimes: any[];
}> {
  const res = await fetch(`${API_BASE}/api/spatial/regimes?lead_hours=${leadHours}`);
  if (!res.ok) throw new Error(`Spatial regimes failed: ${res.status}`);
  return res.json();
}

export async function fetchSpatialUncertainty(leadHours: number = 24): Promise<{
  data_mode: string;
  lead_time_hours: number;
  district_uncertainties: any[];
}> {
  const res = await fetch(`${API_BASE}/api/spatial/uncertainty?lead_hours=${leadHours}`);
  if (!res.ok) throw new Error(`Spatial uncertainty failed: ${res.status}`);
  return res.json();
}

export async function fetchSpatialDifference(leadHours: number = 24): Promise<import('../types/api').SpatialDifferenceResponse> {
  const res = await fetch(`${API_BASE}/api/spatial/difference?lead_hours=${leadHours}`);
  if (!res.ok) throw new Error(`Spatial difference failed: ${res.status}`);
  return res.json();
}

export async function fetchSpatialFSS(): Promise<import('../types/api').SpatialFSSResponse> {
  const res = await fetch(`${API_BASE}/api/spatial/fss`);
  if (!res.ok) throw new Error(`Spatial FSS failed: ${res.status}`);
  return res.json();
}

export async function fetchSpatialGeoJSON(layer: string = 'districts', leadHours: number = 24): Promise<any> {
  const res = await fetch(`${API_BASE}/api/spatial/geojson?layer=${encodeURIComponent(layer)}&lead_hours=${leadHours}`);
  if (!res.ok) throw new Error(`Spatial GeoJSON failed: ${res.status}`);
  return res.json();
}

export async function fetchSpatialExport(leadHours: number = 24): Promise<import('../types/api').SpatialExportResponse> {
  const res = await fetch(`${API_BASE}/api/spatial/export?lead_hours=${leadHours}`);
  if (!res.ok) throw new Error(`Spatial export failed: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Phase 10 Scientific Verification API Client
// ---------------------------------------------------------------------------

export async function fetchScientificStatus(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/scientific/status`);
  if (!res.ok) throw new Error(`Scientific status failed: ${res.status}`);
  return res.json();
}

export async function fetchScientificVerification(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/scientific/verification`);
  if (!res.ok) throw new Error(`Scientific verification failed: ${res.status}`);
  return res.json();
}

export async function fetchScientificThresholds(thresholdMm?: number): Promise<Record<string, any>> {
  const url = thresholdMm != null
    ? `${API_BASE}/api/scientific/thresholds?threshold_mm=${thresholdMm}`
    : `${API_BASE}/api/scientific/thresholds`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Scientific thresholds failed: ${res.status}`);
  return res.json();
}

export async function fetchScientificRegimes(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/scientific/regimes`);
  if (!res.ok) throw new Error(`Scientific regimes failed: ${res.status}`);
  return res.json();
}

export async function fetchScientificLeadTime(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/scientific/lead-time`);
  if (!res.ok) throw new Error(`Scientific lead-time failed: ${res.status}`);
  return res.json();
}

export async function fetchScientificSpatial(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/scientific/spatial`);
  if (!res.ok) throw new Error(`Scientific spatial failed: ${res.status}`);
  return res.json();
}

export async function fetchScientificCalibration(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/scientific/calibration`);
  if (!res.ok) throw new Error(`Scientific calibration failed: ${res.status}`);
  return res.json();
}

export async function fetchScientificBootstrap(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/scientific/bootstrap`);
  if (!res.ok) throw new Error(`Scientific bootstrap failed: ${res.status}`);
  return res.json();
}

export async function fetchScientificFailures(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/scientific/failures`);
  if (!res.ok) throw new Error(`Scientific failures failed: ${res.status}`);
  return res.json();
}

export async function fetchScientificCases(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/scientific/cases`);
  if (!res.ok) throw new Error(`Scientific cases failed: ${res.status}`);
  return res.json();
}

export async function fetchScientificCase(caseId: string): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/scientific/case/${encodeURIComponent(caseId)}`);
  if (!res.ok) throw new Error(`Scientific case failed: ${res.status}`);
  return res.json();
}

export async function fetchScientificExplainability(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/scientific/explainability`);
  if (!res.ok) throw new Error(`Scientific explainability failed: ${res.status}`);
  return res.json();
}

export async function fetchScientificFeatures(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/scientific/features`);
  if (!res.ok) throw new Error(`Scientific features failed: ${res.status}`);
  return res.json();
}

export async function fetchScientificExperts(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/scientific/experts`);
  if (!res.ok) throw new Error(`Scientific experts failed: ${res.status}`);
  return res.json();
}

export async function fetchScientificJuryDemo(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/scientific/jury-demo`);
  if (!res.ok) throw new Error(`Scientific jury-demo failed: ${res.status}`);
  return res.json();
}
