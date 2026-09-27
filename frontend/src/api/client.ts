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

// ==========================================
// Phase 11 — Operational Data Plane Functions
// ==========================================

export async function fetchOperationalSources(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/data/sources`);
  if (!res.ok) throw new Error(`Operational sources failed: ${res.status}`);
  return res.json();
}

export async function fetchOperationalCycles(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/data/cycles`);
  if (!res.ok) throw new Error(`Operational cycles failed: ${res.status}`);
  return res.json();
}

export async function fetchOperationalAvailability(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/data/availability`);
  if (!res.ok) throw new Error(`Operational availability failed: ${res.status}`);
  return res.json();
}

export async function fetchOperationalForecast(
  model = 'NCUM',
  date?: string,
  cycle = '00 UTC',
  leadTime = 24,
  variable = 'precip_nwp_raw'
): Promise<Record<string, any>> {
  const params = new URLSearchParams({
    model,
    cycle,
    lead_time: leadTime.toString(),
    variable,
  });
  if (date) params.append('date', date);
  const res = await fetch(`${API_BASE}/api/data/forecast?${params.toString()}`);
  if (!res.ok) throw new Error(`Operational forecast failed: ${res.status}`);
  return res.json();
}

export async function fetchOperationalObservations(date?: string): Promise<Record<string, any>> {
  const params = date ? `?date=${encodeURIComponent(date)}` : '';
  const res = await fetch(`${API_BASE}/api/data/observations${params}`);
  if (!res.ok) throw new Error(`Operational observations failed: ${res.status}`);
  return res.json();
}

export async function fetchOperationalMatch(
  model = 'NCUM',
  date?: string,
  leadTime = 24
): Promise<Record<string, any>> {
  const params = new URLSearchParams({
    model,
    lead_time: leadTime.toString(),
  });
  if (date) params.append('date', date);
  const res = await fetch(`${API_BASE}/api/data/match?${params.toString()}`);
  if (!res.ok) throw new Error(`Operational match failed: ${res.status}`);
  return res.json();
}

export async function fetchOperationalProvenance(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/data/provenance`);
  if (!res.ok) throw new Error(`Operational provenance failed: ${res.status}`);
  return res.json();
}

export async function fetchOperationalQuality(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/data/quality`);
  if (!res.ok) throw new Error(`Operational quality failed: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Phase 12 Real Paired Dataset API Fetch Functions
// ---------------------------------------------------------------------------

export async function fetchRealDatasetStatus(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/datasets/real/status`);
  if (!res.ok) throw new Error(`Real dataset status failed: ${res.status}`);
  return res.json();
}

export async function fetchRealDatasetSources(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/datasets/real/sources`);
  if (!res.ok) throw new Error(`Real dataset sources failed: ${res.status}`);
  return res.json();
}

export async function fetchRealDatasetCoverage(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/datasets/real/coverage`);
  if (!res.ok) throw new Error(`Real dataset coverage failed: ${res.status}`);
  return res.json();
}

export async function fetchRealDatasetStatistics(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/datasets/real/statistics`);
  if (!res.ok) throw new Error(`Real dataset statistics failed: ${res.status}`);
  return res.json();
}

export async function fetchRealDatasetEvents(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/datasets/real/events`);
  if (!res.ok) throw new Error(`Real dataset events failed: ${res.status}`);
  return res.json();
}

export async function fetchRealDatasetSplits(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/datasets/real/splits`);
  if (!res.ok) throw new Error(`Real dataset splits failed: ${res.status}`);
  return res.json();
}

export async function fetchRealDatasetQuality(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/datasets/real/quality`);
  if (!res.ok) throw new Error(`Real dataset quality failed: ${res.status}`);
  return res.json();
}

export async function fetchRealDatasetProvenance(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/datasets/real/provenance`);
  if (!res.ok) throw new Error(`Real dataset provenance failed: ${res.status}`);
  return res.json();
}

export async function fetchRealDataDiagnostic(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/diagnostic`);
  if (!res.ok) throw new Error(`Real data diagnostic failed: ${res.status}`);
  return res.json();
}

export async function fetchRealDataDownloads(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/api/real-data/downloads`);
  if (!res.ok) throw new Error(`Real data downloads failed: ${res.status}`);
  return res.json();
}

export async function fetchRealDataDownload(downloadId: string): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/download/${encodeURIComponent(downloadId)}`);
  if (!res.ok) throw new Error(`Real data download status failed: ${res.status}`);
  return res.json();
}

export async function postRealDataDownload(payload: {
  provider: string;
  dataset: string;
  date: string;
  cycle?: string;
  lead_hours?: number;
  variables?: string[];
  levels?: string[];
  source_id?: string;
  execute_now?: boolean;
}): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/download`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Download request failed' }));
    throw new Error(err.detail || `Download request failed: ${res.status}`);
  }
  return res.json();
}

export async function postRealDataImportDownload(downloadId: string): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/import`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ download_id: downloadId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Import downloaded data failed' }));
    throw new Error(err.detail || `Import downloaded data failed: ${res.status}`);
  }
  return res.json();
}

export async function postRealDataConvert(payload: {
  filepath: string;
  output_format?: string;
  valid_date?: string;
}): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/convert`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Format conversion failed: ${res.status}`);
  return res.json();
}

export async function fetchRealDataConversions(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/api/real-data/conversions`);
  if (!res.ok) throw new Error(`Fetch conversions failed: ${res.status}`);
  return res.json();
}

export async function postRealDataPair(payload: {
  forecast_id?: string;
  forecast_filepath?: string;
  forecast_valid_time: string;
  observation_id?: string;
  observation_filepath?: string;
  observation_valid_time: string;
  cycle?: string;
  lead_hours?: number;
}): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/pair`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Pairing failed' }));
    throw new Error(err.detail || `Pairing failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchRealDataPairs(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/pairs`);
  if (!res.ok) throw new Error(`Fetch pairs failed: ${res.status}`);
  return res.json();
}

export async function fetchRealDataProvenance(experimentId: string): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/provenance/${encodeURIComponent(experimentId)}`);
  if (!res.ok) throw new Error(`Fetch provenance failed: ${res.status}`);
  return res.json();
}

export async function postRealDataDiscover(payload: {
  provider: string;
  dataset?: string;
  date?: string;
}): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/discover`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Discover source failed: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Phase 15 Operations Control Center API Fetch Functions
// ---------------------------------------------------------------------------

export async function fetchOperationsStatus(): Promise<Record<string, any>> {
  const res = await fetch(API_BASE + '/api/operations/status');
  if (!res.ok) throw new Error('Operations status failed: ' + res.status);
  return res.json();
}

export async function fetchOperationsState(): Promise<Record<string, any>> {
  const res = await fetch(API_BASE + '/api/operations/state');
  if (!res.ok) throw new Error('Operations state failed: ' + res.status);
  return res.json();
}

export async function postOperationsStateTransition(
  to_state: string,
  reason: string
): Promise<Record<string, any>> {
  const res = await fetch(API_BASE + '/api/operations/state/transition', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ to_state, reason }),
  });
  if (!res.ok) throw new Error('State transition failed: ' + res.status);
  return res.json();
}

export async function fetchOperationsScheduler(): Promise<Record<string, any>> {
  const res = await fetch(API_BASE + '/api/operations/scheduler');
  if (!res.ok) throw new Error('Scheduler status failed: ' + res.status);
  return res.json();
}

export async function postSchedulerStart(): Promise<Record<string, any>> {
  const res = await fetch(API_BASE + '/api/operations/scheduler/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error('Scheduler start failed: ' + res.status);
  return res.json();
}

export async function postSchedulerStop(): Promise<Record<string, any>> {
  const res = await fetch(API_BASE + '/api/operations/scheduler/stop', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error('Scheduler stop failed: ' + res.status);
  return res.json();
}

export async function fetchOperationsJobs(limit = 50): Promise<Record<string, any>> {
  const res = await fetch(API_BASE + '/api/operations/jobs?limit=' + limit);
  if (!res.ok) throw new Error('Jobs list failed: ' + res.status);
  return res.json();
}

export async function postSubmitJob(
  cycle_id: string,
  lead_hours: number
): Promise<Record<string, any>> {
  const res = await fetch(API_BASE + '/api/operations/jobs/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cycle_id, lead_hours }),
  });
  if (!res.ok) throw new Error('Submit job failed: ' + res.status);
  return res.json();
}

export async function fetchOperationsAlerts(include_resolved = false): Promise<Record<string, any>> {
  const res = await fetch(
    API_BASE + '/api/operations/alerts?include_resolved=' + include_resolved
  );
  if (!res.ok) throw new Error('Alerts fetch failed: ' + res.status);
  return res.json();
}

export async function postAcknowledgeAlert(
  alertId: string,
  operator = 'OPERATOR'
): Promise<Record<string, any>> {
  const res = await fetch(
    API_BASE + '/api/operations/alerts/' + alertId + '/acknowledge?operator=' + operator,
    { method: 'POST', headers: { 'Content-Type': 'application/json' } }
  );
  if (!res.ok) throw new Error('Acknowledge failed: ' + res.status);
  return res.json();
}

export async function postResolveAlert(alertId: string): Promise<Record<string, any>> {
  const res = await fetch(API_BASE + '/api/operations/alerts/' + alertId + '/resolve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error('Resolve failed: ' + res.status);
  return res.json();
}

export async function fetchOperationsDrift(): Promise<Record<string, any>> {
  const res = await fetch(API_BASE + '/api/operations/drift');
  if (!res.ok) throw new Error('Drift report failed: ' + res.status);
  return res.json();
}

export async function fetchOperationsReadiness(): Promise<Record<string, any>> {
  const res = await fetch(API_BASE + '/api/operations/readiness');
  if (!res.ok) throw new Error('Readiness check failed: ' + res.status);
  return res.json();
}

export async function fetchOperationsHealth(): Promise<Record<string, any>> {
  const res = await fetch(API_BASE + '/api/operations/health');
  if (!res.ok) throw new Error('Operations health failed: ' + res.status);
  return res.json();
}

// ---------------------------------------------------------------------------
// Phase 16: Real-Data Activation, Ingestion & Real Verification
// ---------------------------------------------------------------------------

export async function fetchActivationStatus(
  cycle = '00Z',
  sourceId = 'NCMRWF_NCUM'
): Promise<Record<string, any>> {
  const res = await fetch(
    API_BASE + '/api/activation/status?cycle=' + encodeURIComponent(cycle) + '&source_id=' + encodeURIComponent(sourceId)
  );
  if (!res.ok) throw new Error('Activation status failed: ' + res.status);
  return res.json();
}

export async function fetchActivationSources(): Promise<any[]> {
  const res = await fetch(API_BASE + '/api/activation/sources');
  if (!res.ok) throw new Error('Activation sources failed: ' + res.status);
  return res.json();
}

export async function fetchActivationValidation(
  cycle = '00Z',
  sourceId = 'NCMRWF_NCUM'
): Promise<Record<string, any>> {
  const res = await fetch(
    API_BASE + '/api/activation/validation?cycle=' + encodeURIComponent(cycle) + '&source_id=' + encodeURIComponent(sourceId)
  );
  if (!res.ok) throw new Error('Activation validation failed: ' + res.status);
  return res.json();
}

export async function fetchActivationAudit(): Promise<any[]> {
  const res = await fetch(API_BASE + '/api/activation/audit');
  if (!res.ok) throw new Error('Activation audit failed: ' + res.status);
  return res.json();
}

export async function postActivationRequest(
  operatorId: string,
  sourceId = 'NCMRWF_NCUM',
  cycle = '00Z',
  reason = 'Operational run launch'
): Promise<Record<string, any>> {
  const res = await fetch(API_BASE + '/api/activation/request', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ operator_id: operatorId, source_id: sourceId, cycle, reason }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail?.message || ('Activation request failed: ' + res.status));
  }
  return res.json();
}

export async function postActivationApprove(
  operatorId: string,
  signature: string,
  activationId?: string
): Promise<Record<string, any>> {
  const res = await fetch(API_BASE + '/api/activation/approve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ operator_id: operatorId, signature, activation_id: activationId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail?.message || ('Activation approval failed: ' + res.status));
  }
  return res.json();
}

export async function postActivationReject(
  operatorId: string,
  reason: string,
  activationId?: string
): Promise<Record<string, any>> {
  const res = await fetch(API_BASE + '/api/activation/reject', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ operator_id: operatorId, reason, activation_id: activationId }),
  });
  if (!res.ok) throw new Error('Activation rejection failed: ' + res.status);
  return res.json();
}

export async function fetchIngestionStatus(): Promise<Record<string, any>> {
  const res = await fetch(API_BASE + '/api/ingestion/status');
  if (!res.ok) throw new Error('Ingestion status failed: ' + res.status);
  return res.json();
}

export async function fetchIngestionSources(): Promise<any[]> {
  const res = await fetch(API_BASE + '/api/ingestion/sources');
  if (!res.ok) throw new Error('Ingestion sources failed: ' + res.status);
  return res.json();
}

export async function fetchIngestionFiles(limit = 50, authority?: string): Promise<Record<string, any>> {
  const url = authority
    ? (API_BASE + '/api/ingestion/files?limit=' + limit + '&authority=' + encodeURIComponent(authority))
    : (API_BASE + '/api/ingestion/files?limit=' + limit);
  const res = await fetch(url);
  if (!res.ok) throw new Error('Ingestion files failed: ' + res.status);
  return res.json();
}

export async function fetchIngestionQC(): Promise<Record<string, any>> {
  const res = await fetch(API_BASE + '/api/ingestion/qc');
  if (!res.ok) throw new Error('Ingestion QC failed: ' + res.status);
  return res.json();
}

export async function fetchRealVerification(
  cycle = '00Z',
  leadTime = 24,
  thresholdMm = 0.1
): Promise<Record<string, any>> {
  const res = await fetch(
    API_BASE + '/api/verification/real?cycle=' + encodeURIComponent(cycle) + '&lead_time=' + leadTime + '&threshold_mm=' + thresholdMm
  );
  if (!res.ok) throw new Error('Real verification failed: ' + res.status);
  return res.json();
}

// ==========================================
// Phase 17 Production & Operational APIs
// ==========================================

export async function fetchProductionStatus(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/production/status`);
  if (!res.ok) throw new Error(`Production status failed: ${res.status}`);
  return res.json();
}

export async function fetchProductionHealth(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/production/health`);
  if (!res.ok) throw new Error(`Production health failed: ${res.status}`);
  return res.json();
}

export async function fetchProductionCycles(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/production/cycles`);
  if (!res.ok) throw new Error(`Production cycles failed: ${res.status}`);
  return res.json();
}

export async function fetchProductionCycleDetail(cycleId: string): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/production/cycles/${encodeURIComponent(cycleId)}`);
  if (!res.ok) throw new Error(`Production cycle detail failed: ${res.status}`);
  return res.json();
}

export async function fetchProductionJobs(cycleId?: string): Promise<Record<string, any>> {
  const url = cycleId
    ? `${API_BASE}/api/production/jobs?cycle_id=${encodeURIComponent(cycleId)}`
    : `${API_BASE}/api/production/jobs`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Production jobs failed: ${res.status}`);
  return res.json();
}

export async function fetchProductionDataHealth(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/production/data-health`);
  if (!res.ok) throw new Error(`Data health failed: ${res.status}`);
  return res.json();
}

export async function fetchProductionFreshness(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/production/freshness`);
  if (!res.ok) throw new Error(`Freshness failed: ${res.status}`);
  return res.json();
}

export async function fetchProductionStorage(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/production/storage`);
  if (!res.ok) throw new Error(`Storage status failed: ${res.status}`);
  return res.json();
}

export async function fetchProductionPublications(limit = 50): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/production/publications?limit=${limit}`);
  if (!res.ok) throw new Error(`Publications failed: ${res.status}`);
  return res.json();
}

export async function fetchProductionLatestPublication(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/production/publications/latest`);
  if (!res.ok) throw new Error(`Latest publication failed: ${res.status}`);
  return res.json();
}

export async function fetchProductionVerification(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/production/verification`);
  if (!res.ok) throw new Error(`Production verification failed: ${res.status}`);
  return res.json();
}

export async function fetchProductionVerificationHistory(
  leadTime?: number,
  thresholdMm?: number,
  region?: string
): Promise<Record<string, any>> {
  const params = new URLSearchParams();
  if (leadTime !== undefined) params.append('lead_time', leadTime.toString());
  if (thresholdMm !== undefined) params.append('threshold_mm', thresholdMm.toString());
  if (region) params.append('region', region);
  const q = params.toString() ? `?${params.toString()}` : '';
  const res = await fetch(`${API_BASE}/api/production/verification/history${q}`);
  if (!res.ok) throw new Error(`Verification history failed: ${res.status}`);
  return res.json();
}

export async function fetchProductionMetrics(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/production/metrics`);
  if (!res.ok) throw new Error(`Production metrics failed: ${res.status}`);
  return res.json();
}

export async function fetchProductionAlerts(severity?: string, category?: string): Promise<Record<string, any>> {
  const params = new URLSearchParams();
  if (severity) params.append('severity', severity);
  if (category) params.append('category', category);
  const q = params.toString() ? `?${params.toString()}` : '';
  const res = await fetch(`${API_BASE}/api/production/alerts${q}`);
  if (!res.ok) throw new Error(`Production alerts failed: ${res.status}`);
  return res.json();
}

export async function postRetryCycle(cycleId: string, leadHours?: number): Promise<Record<string, any>> {
  const params = leadHours !== undefined ? `?lead_hours=${leadHours}` : '';
  const res = await fetch(`${API_BASE}/api/production/cycle/${encodeURIComponent(cycleId)}/retry${params}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error(`Retry cycle failed: ${res.status}`);
  return res.json();
}

export async function postRetractPublication(id: string, reason: string): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/production/publication/${encodeURIComponent(id)}/retract?reason=${encodeURIComponent(reason)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error(`Retract publication failed: ${res.status}`);
  return res.json();
}

export async function postEmergencyStop(reason: string, actor = 'OPERATOR_DESK', role = 'OPERATOR'): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/production/emergency-stop`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason, actor, role }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Emergency stop failed' }));
    throw new Error(err.detail || `Emergency stop failed: ${res.status}`);
  }
  return res.json();
}

export async function postEmergencyRecover(justification: string, actor = 'SUPERVISOR_CONSOLE', role = 'SUPERVISOR'): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/production/emergency-recover`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ justification, actor, role }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Emergency recovery failed' }));
    throw new Error(err.detail || `Emergency recovery failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchProductionGates(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/production/gates`);
  if (!res.ok) throw new Error(`Production gates failed: ${res.status}`);
  return res.json();
}

export async function fetchProductionEvents(limit = 50): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/production/events?limit=${limit}`);
  if (!res.ok) throw new Error(`Production events failed: ${res.status}`);
  return res.json();
}

export async function fetchProductionModels(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/production/models`);
  if (!res.ok) throw new Error(`Production models failed: ${res.status}`);
  return res.json();
}

export async function fetchProductionDataReadiness(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/production/data-readiness`);
  if (!res.ok) throw new Error(`Data readiness failed: ${res.status}`);
  return res.json();
}

// Modular Health Probes
export async function fetchHealthOverall(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/health/overall`);
  if (!res.ok) throw new Error(`Health overall failed: ${res.status}`);
  return res.json();
}

// =============================================================================
// Phase 18 — Institutional Acceptance & Validation API Functions
// =============================================================================

export async function fetchAcceptanceStatus(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/acceptance/status`);
  if (!res.ok) throw new Error(`Acceptance status failed: ${res.status}`);
  return res.json();
}

export async function fetchAcceptanceSources(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/acceptance/sources`);
  if (!res.ok) throw new Error(`Acceptance sources failed: ${res.status}`);
  return res.json();
}

export async function fetchAcceptanceCycles(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/acceptance/cycles`);
  if (!res.ok) throw new Error(`Acceptance cycles failed: ${res.status}`);
  return res.json();
}

export async function fetchAcceptanceGates(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/acceptance/gates`);
  if (!res.ok) throw new Error(`Acceptance gates failed: ${res.status}`);
  return res.json();
}

export async function fetchAcceptanceInference(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/acceptance/inference`);
  if (!res.ok) throw new Error(`Acceptance inference failed: ${res.status}`);
  return res.json();
}

export async function fetchAcceptanceVerification(leadHours = 24): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/acceptance/verification?lead_hours=${leadHours}`);
  if (!res.ok) throw new Error(`Acceptance verification failed: ${res.status}`);
  return res.json();
}

export async function fetchAcceptanceBaselines(leadHours = 24): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/acceptance/baselines?lead_hours=${leadHours}`);
  if (!res.ok) throw new Error(`Acceptance baselines failed: ${res.status}`);
  return res.json();
}

export async function fetchAcceptanceSpatial(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/acceptance/spatial`);
  if (!res.ok) throw new Error(`Acceptance spatial failed: ${res.status}`);
  return res.json();
}

export async function fetchAcceptanceFss(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/acceptance/fss`);
  if (!res.ok) throw new Error(`Acceptance FSS failed: ${res.status}`);
  return res.json();
}

export async function fetchAcceptanceCalibration(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/acceptance/calibration`);
  if (!res.ok) throw new Error(`Acceptance calibration failed: ${res.status}`);
  return res.json();
}

export async function fetchAcceptanceCases(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/acceptance/cases`);
  if (!res.ok) throw new Error(`Acceptance cases failed: ${res.status}`);
  return res.json();
}

export async function fetchAcceptanceAudit(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/acceptance/audit`);
  if (!res.ok) throw new Error(`Acceptance audit failed: ${res.status}`);
  return res.json();
}

export async function postStagingRun(payload: {
  cycle_id: string;
  lead_hours?: number;
  ncum_file?: string;
  neps_file?: string;
  imd_file?: string;
  operator_id?: string;
}): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/acceptance/staging-run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Staging run failed: ${res.status}`);
  return res.json();
}

export async function postRequestActivation(operatorId: string, reason: string): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/acceptance/request-activation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ operator_id: operatorId, reason }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request activation failed' }));
    throw new Error(err.detail || `Request activation failed: ${res.status}`);
  }
  return res.json();
}

export async function postApproveActivation(supervisorId: string, authorizationPin: string): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/acceptance/approve-activation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ supervisor_id: supervisorId, authorization_pin: authorizationPin }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Approve activation failed' }));
    throw new Error(err.detail || `Approve activation failed: ${res.status}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Phase 19 Real Data Activation Lab API Client
// ---------------------------------------------------------------------------

export async function fetchRealDataMountStatus(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/mount-status`);
  if (!res.ok) throw new Error(`Real data mount status failed: ${res.status}`);
  return res.json();
}

export async function fetchRealDataDiagnose(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/diagnose`, { method: 'POST' });
  if (!res.ok) throw new Error(`Real data diagnose failed: ${res.status}`);
  return res.json();
}

export async function fetchRealDataStatus(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/status`);
  if (!res.ok) throw new Error(`Real data status failed: ${res.status}`);
  return res.json();
}

export async function fetchRealDataSources(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/api/real-data/sources`);
  if (!res.ok) throw new Error(`Real data sources failed: ${res.status}`);
  return res.json();
}

export async function fetchRealDataFiles(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/api/real-data/files`);
  if (!res.ok) throw new Error(`Real data files failed: ${res.status}`);
  return res.json();
}

export async function fetchRealDataManifest(id: string): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/manifest/${encodeURIComponent(id)}`);
  if (!res.ok) throw new Error(`Real data manifest failed: ${res.status}`);
  return res.json();
}

export async function postRealDataImport(formData: FormData): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/import`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Import failed' }));
    throw new Error(err.detail || `Import failed: ${res.status}`);
  }
  return res.json();
}

export async function postRealDataScan(directories?: string[]): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ directories }),
  });
  if (!res.ok) throw new Error(`Directory scan failed: ${res.status}`);
  return res.json();
}

export async function postRealDataValidate(importId: string): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/validate/${encodeURIComponent(importId)}`, { method: 'POST' });
  if (!res.ok) throw new Error(`Validate file failed: ${res.status}`);
  return res.json();
}

export async function postRealDataReject(importId: string, reason: string): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/reject/${encodeURIComponent(importId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) throw new Error(`Reject file failed: ${res.status}`);
  return res.json();
}

export async function postRealDataPromote(importId: string): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/promote/${encodeURIComponent(importId)}`, { method: 'POST' });
  if (!res.ok) throw new Error(`Promote file failed: ${res.status}`);
  return res.json();
}

export async function fetchRealDataRuns(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/api/real-data/runs`);
  if (!res.ok) throw new Error(`Fetch runs failed: ${res.status}`);
  return res.json();
}

export async function fetchRealDataRunDetails(runId: string): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/runs/${encodeURIComponent(runId)}`);
  if (!res.ok) throw new Error(`Fetch run details failed: ${res.status}`);
  return res.json();
}

export async function postRealDataRun(payload: {
  ncum_filepath?: string;
  ncum_file_id?: string;
  neps_filepath?: string;
  neps_file_id?: string;
  imd_filepath?: string;
  imd_file_id?: string;
  source_id?: string;
  cycle?: string;
  lead_hours?: number;
  operator_id?: string;
}): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Experiment execution failed' }));
    throw new Error(err.detail || `Experiment execution failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchRealDataGrid(runId: string, leadHours = 24, force = false): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/runs/${encodeURIComponent(runId)}/grid?lead_hours=${leadHours}&force=${force}`);
  if (!res.ok) throw new Error(`Fetch spatial grid failed: ${res.status}`);
  return res.json();
}

export async function fetchPairingCandidates(runId?: string): Promise<{
  target_run?: any;
  recommended_id?: string;
  total_candidates: number;
  candidates: any[];
  anti_leakage_policy: string;
}> {
  const q = runId ? `?run_id=${encodeURIComponent(runId)}` : '';
  const res = await fetch(`${API_BASE}/api/real-data/pairing-candidates${q}`);
  if (!res.ok) throw new Error(`Fetch pairing candidates failed: ${res.status}`);
  return res.json();
}

export async function pairRunWithImd(
  runId: string,
  imdFileId?: string,
  autoMatch = true
): Promise<{
  success: boolean;
  run_id: string;
  status: string;
  pairing_id: string;
  pairing_hash: string;
  forecast_valid_time: string;
  observation_valid_time: string;
  observation_filename: string;
  observation_sha256: string;
  zero_future_leakage_verified: boolean;
  verification_status: string;
  verification_metrics: Record<string, any>;
  grid: Record<string, any>;
  message: string;
}> {
  const res = await fetch(`${API_BASE}/api/real-data/runs/${encodeURIComponent(runId)}/pair-imd`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ imd_file_id: imdFileId, auto_match: autoMatch }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'IMD pairing failed' }));
    throw new Error(err.detail || `IMD pairing failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchRealDataVault(provider?: string, dataset?: string): Promise<any[]> {
  const params = new URLSearchParams();
  if (provider) params.set('provider', provider);
  if (dataset) params.set('dataset', dataset);
  const q = params.toString() ? `?${params.toString()}` : '';
  const res = await fetch(`${API_BASE}/api/real-data/vault${q}`);
  if (!res.ok) throw new Error(`Fetch data vault failed: ${res.status}`);
  return res.json();
}

export async function deleteRealDataVault(id: string, force = false): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/vault/delete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, force }),
  });
  if (!res.ok) throw new Error(`Delete vault item failed: ${res.status}`);
  return res.json();
}

export async function deleteRealDataDownload(downloadId: string, force = false): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/downloads/${encodeURIComponent(downloadId)}?force=${force}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Delete download failed: ${res.status}`);
  return res.json();
}

export async function deleteRealDataFile(fileId: string, force = false): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/files/${encodeURIComponent(fileId)}?force=${force}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Delete file failed: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Map Engine Configuration & Raw Data Explorer APIs (Phase 19 Upgrade)
// ---------------------------------------------------------------------------

export async function fetchMapConfig(): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/map/config`);
  if (!res.ok) throw new Error(`Fetch map config failed: ${res.status}`);
  return res.json();
}

export async function fetchFileSummary(fileId: string): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/files/${encodeURIComponent(fileId)}/summary`);
  if (!res.ok) throw new Error(`Fetch file summary failed: ${res.status}`);
  return res.json();
}

export async function fetchFileRecords(
  fileId: string,
  page = 1,
  pageSize = 100,
  lat?: number,
  lon?: number,
  search?: string
): Promise<Record<string, any>> {
  const params = new URLSearchParams({
    page: page.toString(),
    pageSize: pageSize.toString(),
  });
  if (lat !== undefined && lat !== null) params.set('lat', lat.toString());
  if (lon !== undefined && lon !== null) params.set('lon', lon.toString());
  if (search) params.set('search', search);

  const res = await fetch(`${API_BASE}/api/real-data/files/${encodeURIComponent(fileId)}/records?${params.toString()}`);
  if (!res.ok) throw new Error(`Fetch file records failed: ${res.status}`);
  return res.json();
}

export async function fetchFileVariables(fileId: string): Promise<any[]> {
  const res = await fetch(`${API_BASE}/api/real-data/files/${encodeURIComponent(fileId)}/variables`);
  if (!res.ok) throw new Error(`Fetch file variables failed: ${res.status}`);
  return res.json();
}

export async function fetchFileTimes(fileId: string): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/files/${encodeURIComponent(fileId)}/times`);
  if (!res.ok) throw new Error(`Fetch file times failed: ${res.status}`);
  return res.json();
}

export async function fetchFileMapData(fileId: string, variable?: string): Promise<Record<string, any>> {
  const params = variable ? `?variable=${encodeURIComponent(variable)}` : '';
  const res = await fetch(`${API_BASE}/api/real-data/files/${encodeURIComponent(fileId)}/map${params}`);
  if (!res.ok) throw new Error(`Fetch file map data failed: ${res.status}`);
  return res.json();
}

export function getFileDownloadUrl(fileId: string, type: 'raw' | 'canonical' = 'raw'): string {
  return `${API_BASE}/api/real-data/files/${encodeURIComponent(fileId)}/download?type=${type}`;
}

export async function fetchFileProvenance(fileId: string): Promise<Record<string, any>> {
  const res = await fetch(`${API_BASE}/api/real-data/files/${encodeURIComponent(fileId)}/provenance`);
  if (!res.ok) throw new Error(`Fetch file provenance failed: ${res.status}`);
  return res.json();
}



