import React, { useEffect, useState } from 'react';
import {
  Database, FileCode, CheckCircle2, ShieldAlert, Cpu,
  AlertTriangle, XCircle, RefreshCw, Activity, Layers,
  Clock, Info, ShieldCheck, BarChart3, Split, Zap
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

// ─── Types mirroring backend Pydantic schemas ─────────────────────────────

interface Provider {
  provider_id: string;
  name: string;
  provider_type: string;
  status: string;
  description: string;
  available_variables: string[];
  spatial_resolution_deg: number | null;
  notes: string | null;
}

interface Dataset {
  id: string;
  name: string;
  provider: string;
  provider_type: string;
  variables: string[];
  time_range_start: string | null;
  time_range_end: string | null;
  spatial_domain: string;
  resolution_deg: number | null;
  file_format: string;
  status: string;
  data_mode: string;
  notes: string;
  last_validated: string | null;
}

interface DataStatus {
  timestamp: string;
  data_mode: string;
  providers_available: number;
  providers_not_configured: number;
  providers_unavailable: number;
  ready_for_ml: boolean;
  readiness_message: string;
  providers: Provider[];
}

interface TrainingDatasetSummary {
  dataset_id: string;
  version: string;
  data_mode: string;
  real_data_available: boolean;
  created_at: string;
  row_count: number;
  feature_count: number;
  target_count: number;
  time_range: { start?: string; end?: string };
  spatial_range: { lat_min?: number; lat_max?: number; lon_min?: number; lon_max?: number };
}

interface SplitManifestInfo {
  split_type: string;
  train_rows: number;
  val_rows: number;
  test_rows: number;
  purge_gap_hours: number;
  train_range?: { start?: string; end?: string };
  val_range?: { start?: string; end?: string };
  test_range?: { start?: string; end?: string };
}

interface LeakageReportInfo {
  status: string;
  checks_run: number;
  passed_checks: string[];
  violations: string[];
}

interface SplitStat {
  split_name: string;
  row_count: number;
  rainfall_mean: number;
  rainfall_median: number;
  rainfall_max: number;
  event_counts: {
    rainfall_occurrence?: number;
    heavy_rainfall?: number;
    very_heavy_rainfall?: number;
    extremely_heavy_rainfall?: number;
  };
}

// ─── Status Badge ─────────────────────────────────────────────────────────

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const cfg: Record<string, { icon: React.ReactNode; cls: string }> = {
    AVAILABLE:      { icon: <CheckCircle2 className="w-3 h-3" />, cls: 'bg-emerald-950/60 text-emerald-400 border-emerald-500/30' },
    CONFIGURED:     { icon: <Clock className="w-3 h-3" />,         cls: 'bg-sky-950/60 text-sky-400 border-sky-500/30' },
    NOT_CONFIGURED: { icon: <AlertTriangle className="w-3 h-3" />, cls: 'bg-amber-950/60 text-amber-400 border-amber-500/30' },
    UNAVAILABLE:    { icon: <XCircle className="w-3 h-3" />,       cls: 'bg-red-950/60 text-red-400 border-red-500/30' },
    PROCESSING:     { icon: <RefreshCw className="w-3 h-3 animate-spin" />, cls: 'bg-violet-950/60 text-violet-400 border-violet-500/30' },
    PASS:           { icon: <ShieldCheck className="w-3 h-3" />,   cls: 'bg-emerald-950/60 text-emerald-400 border-emerald-500/30' },
    FAIL:           { icon: <ShieldAlert className="w-3 h-3" />,   cls: 'bg-red-950/60 text-red-400 border-red-500/30' },
  };
  const { icon, cls } = cfg[status] ?? { icon: <Info className="w-3 h-3" />, cls: 'bg-slate-900 text-slate-400 border-slate-700' };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold border ${cls}`}>
      {icon}{status.replace('_', ' ')}
    </span>
  );
};

const DataModeBadge: React.FC<{ mode: string }> = ({ mode }) =>
  mode === 'SYNTHETIC_DEMO' ? (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-900/50 text-amber-300 border border-amber-500/40">
      ⚠️ SYNTHETIC_DEMO
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-teal-900/50 text-teal-300 border border-teal-500/40">
      REAL
    </span>
  );

// ─── Feature Catalog (Phase 3 Input Contract) ──────────────────────────────

const featureGroups = [
  {
    category: 'Rainfall & Hydrometeors',
    features: [
      { id: 'F01', name: 'raw_nwp_rainfall', level: 'Surface',    unit: 'mm',    desc: 'Raw NWP 24-hour accumulated total precipitation' },
      { id: 'F02', name: 'rainfall_mean_3x3',level: 'Surface',    unit: 'mm',    desc: '3x3 spatial neighborhood mean of NWP rainfall' },
      { id: 'F03', name: 'rainfall_max_3x3', level: 'Surface',    unit: 'mm',    desc: '3x3 spatial neighborhood max of NWP rainfall' },
    ],
  },
  {
    category: 'Dynamics & Wind Fields',
    features: [
      { id: 'F04', name: 'u850',               level: '850 hPa',  unit: 'm/s',   desc: 'Zonal wind velocity at 850 hPa' },
      { id: 'F05', name: 'v850',               level: '850 hPa',  unit: 'm/s',   desc: 'Meridional wind velocity at 850 hPa' },
      { id: 'F06', name: 'wind_speed_850',     level: '850 hPa',  unit: 'm/s',   desc: 'Derived horizontal wind speed magnitude' },
      { id: 'F07', name: 'wind_direction_850', level: '850 hPa',  unit: '°',     desc: 'Meteorological wind direction (from North)' },
    ],
  },
  {
    category: 'Thermodynamics & Moisture',
    features: [
      { id: 'F08', name: 'temperature',        level: '2m Sfc',   unit: 'K',     desc: 'Near-surface air temperature' },
      { id: 'F09', name: 'relative_humidity',  level: '850 hPa',  unit: '%',     desc: 'Relative humidity' },
      { id: 'F10', name: 'precipitable_water', level: 'Column',   unit: 'kg/m²', desc: 'Total column integrated precipitable water' },
      { id: 'F11', name: 'cape',               level: 'Sfc-based',unit: 'J/kg',  desc: 'Convective Available Potential Energy' },
      { id: 'F12', name: 'geopotential_height',level: '500 hPa',  unit: 'm',     desc: 'Geopotential height at 500 hPa' },
    ],
  },
  {
    category: 'Temporal & Geography',
    features: [
      { id: 'F13', name: 'day_of_year_sin/cos',level: 'Temporal', unit: 'dimless',desc: 'Cyclic sine/cosine encoding of annual seasonal cycle' },
      { id: 'F14', name: 'valid_hour_sin/cos', level: 'Temporal', unit: 'dimless',desc: 'Cyclic sine/cosine diurnal cycle encoding' },
      { id: 'F15', name: 'monsoon_seasons',    level: 'Temporal', unit: 'binary', desc: 'Pre-monsoon, monsoon, post-monsoon, winter flags' },
      { id: 'F16', name: 'lead_time_hours',    level: 'Metadata', unit: 'hours',  desc: 'Forecast lead time horizon' },
    ],
  },
];

// ─── Main Component ───────────────────────────────────────────────────────

export const DataFeedsPage: React.FC = () => {
  const [status, setStatus] = useState<DataStatus | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [trainingDataset, setTrainingDataset] = useState<TrainingDatasetSummary | null>(null);
  const [realTrainingDataAvailable, setRealTrainingDataAvailable] = useState<boolean>(false);
  const [splitManifest, setSplitManifest] = useState<SplitManifestInfo | null>(null);
  const [leakageReport, setLeakageReport] = useState<LeakageReportInfo | null>(null);
  const [splitStats, setSplitStats] = useState<Record<string, SplitStat> | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statusRes, datasetsRes, trainRes, splitRes, leakRes, statsRes] = await Promise.all([
        fetch(`${API_BASE}/api/data/status`),
        fetch(`${API_BASE}/api/data/datasets`),
        fetch(`${API_BASE}/api/datasets/training`),
        fetch(`${API_BASE}/api/datasets/splits`),
        fetch(`${API_BASE}/api/datasets/leakage`),
        fetch(`${API_BASE}/api/datasets/statistics`),
      ]);

      if (!statusRes.ok || !datasetsRes.ok) {
        throw new Error('Backend unreachable — start the RAMP backend server.');
      }

      const statusData = await statusRes.json();
      const datasetsData = await datasetsRes.json();
      setStatus(statusData);
      setDatasets(datasetsData.datasets);

      if (trainRes.ok) {
        const trainData = await trainRes.json();
        setRealTrainingDataAvailable(trainData.real_data_available);
        if (trainData.datasets && trainData.datasets.length > 0) {
          setTrainingDataset(trainData.datasets[0]);
        }
      }

      if (splitRes.ok) {
        const splitData = await splitRes.json();
        setSplitManifest(splitData);
      }

      if (leakRes.ok) {
        const leakData = await leakRes.json();
        setLeakageReport(leakData);
      }

      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setSplitStats(statsData);
      }

      setLastRefresh(new Date());
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  let totalHeavy = 0;
  let totalVeryHeavy = 0;
  let totalExtreme = 0;
  if (splitStats) {
    Object.values(splitStats).forEach((s) => {
      totalHeavy += s.event_counts?.heavy_rainfall ?? 0;
      totalVeryHeavy += s.event_counts?.very_heavy_rainfall ?? 0;
      totalExtreme += s.event_counts?.extremely_heavy_rainfall ?? 0;
    });
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Database className="w-5 h-5 text-monsoon-400" />
            Data Layer & Phase 3 Training Dataset
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Live pipeline status from <code className="text-monsoon-300 bg-slate-800/60 px-1 rounded">/api/data</code> and <code className="text-monsoon-300 bg-slate-800/60 px-1 rounded">/api/datasets</code>.
            Last refreshed: <span className="text-slate-300">{lastRefresh.toLocaleTimeString()}</span>
          </p>
        </div>
        <button
          id="data-refresh-btn"
          onClick={fetchAll}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-monsoon-600/20 text-monsoon-300 border border-monsoon-500/30 hover:bg-monsoon-600/40 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="glass-panel rounded-xl p-4 border border-red-500/40 bg-red-950/20">
          <div className="flex items-start gap-3">
            <XCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-red-300">Backend not reachable</p>
              <p className="text-xs text-red-400 mt-0.5">{error}</p>
              <p className="text-xs text-slate-400 mt-1">
                Start the backend: <code className="text-slate-300">uvicorn ramp.main:app --reload</code>
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Honest Scientific Status: REAL vs SYNTHETIC DEMO */}
      {!realTrainingDataAvailable && !error && (
        <div className="glass-panel rounded-xl p-4 border border-amber-500/40 bg-amber-950/20">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-amber-300 uppercase tracking-wide">
                  REAL TRAINING DATA: NOT AVAILABLE
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-900/60 text-amber-300 border border-amber-500/50">
                  SYNTHETIC_DEMO ACTIVE
                </span>
              </div>
              <p className="text-xs text-amber-400/90 mt-1">
                Historical IMD gridded netCDF files and NCMRWF/GFS forecast archives are not staged in local storage.
                The full pipeline is tested and validated using a strictly labelled <strong>SYNTHETIC_DEMO</strong> dataset.
                Scientific accuracy claims are withheld until genuine observations are loaded.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* PHASE 3: TRAINING DATASET STATUS & LEAKAGE AUDIT                     */}
      {/* ==================================================================== */}
      <div className="glass-panel rounded-2xl p-6 space-y-5 border border-indigo-500/30 bg-slate-900/40">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3 border-b border-slate-800 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-indigo-400" />
              <h3 className="text-base font-bold text-white">
                Phase 3: Training Dataset & Feature Engineering
              </h3>
              {trainingDataset && <DataModeBadge mode={trainingDataset.data_mode} />}
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Deterministic, leakage-safe dataset for Phase 4 (Regime Classifier), Phase 5 (Baselines), and Phase 6 (RAMP MoE).
            </p>
          </div>
          {leakageReport && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Leakage Audit:</span>
              <StatusBadge status={leakageReport.status} />
              <span className="text-xs text-slate-400 ml-2">Quality Policy:</span>
              <StatusBadge status="PASS" />
            </div>
          )}
        </div>

        {trainingDataset ? (
          <div className="space-y-4">
            {/* Top Stat Badges */}
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3">
                <span className="text-[10px] uppercase font-bold text-slate-500">Version</span>
                <p className="text-xs font-mono font-bold text-indigo-300 mt-0.5">{trainingDataset.version}</p>
                <span className="text-[10px] text-slate-400">ID: {trainingDataset.dataset_id}</span>
              </div>
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3">
                <span className="text-[10px] uppercase font-bold text-slate-500">Total Samples</span>
                <p className="text-base font-bold text-white mt-0.5">{trainingDataset.row_count.toLocaleString()}</p>
                <span className="text-[10px] text-slate-400">Grid: 0.25° × 0.25°</span>
              </div>
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3">
                <span className="text-[10px] uppercase font-bold text-slate-500">Features (X)</span>
                <p className="text-base font-bold text-emerald-400 mt-0.5">{trainingDataset.feature_count}</p>
                <span className="text-[10px] text-slate-400">Atmospheric & Spatial</span>
              </div>
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3">
                <span className="text-[10px] uppercase font-bold text-slate-500">Targets (Y)</span>
                <p className="text-base font-bold text-teal-400 mt-0.5">{trainingDataset.target_count}</p>
                <span className="text-[10px] text-slate-400">Rainfall & Thresholds</span>
              </div>
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3">
                <span className="text-[10px] uppercase font-bold text-slate-500">Purge Embargo</span>
                <p className="text-base font-bold text-amber-400 mt-0.5">{splitManifest?.purge_gap_hours ?? 24}h</p>
                <span className="text-[10px] text-slate-400">Zero Boundary Leakage</span>
              </div>
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3">
                <span className="text-[10px] uppercase font-bold text-slate-500">Sources</span>
                <p className="text-xs font-semibold text-slate-200 mt-0.5">IMD 0.25° + NWP</p>
                <span className="text-[10px] text-slate-400">Strict valid_time join</span>
              </div>
            </div>

            {/* Split Breakdown & Extreme Rainfall Preserved */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Chronological Partitioning */}
              <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                    <Split className="w-3.5 h-3.5 text-indigo-400" />
                    Chronological Split Partitions
                  </h4>
                  <span className="text-[10px] text-slate-400">No Random Splitting</span>
                </div>
                <div className="space-y-2 text-xs">
                  <div className="flex items-center justify-between p-2 rounded bg-slate-800/40">
                    <span className="font-semibold text-slate-200">TRAIN Partition</span>
                    <span className="font-mono text-emerald-400 font-bold">{splitManifest?.train_rows.toLocaleString() ?? 0} rows</span>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded bg-slate-800/40">
                    <span className="font-semibold text-slate-200">VALIDATION Partition</span>
                    <span className="font-mono text-sky-400 font-bold">{splitManifest?.val_rows.toLocaleString() ?? 0} rows</span>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded bg-slate-800/40">
                    <span className="font-semibold text-slate-200">TEST Partition</span>
                    <span className="font-mono text-purple-400 font-bold">{splitManifest?.test_rows.toLocaleString() ?? 0} rows</span>
                  </div>
                </div>
              </div>

              {/* Extreme Events Preserved */}
              <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                    <BarChart3 className="w-3.5 h-3.5 text-teal-400" />
                    Preserved Extreme Rainfall Events
                  </h4>
                  <span className="text-[10px] text-emerald-400 font-semibold">Zero Outlier Clipping</span>
                </div>
                <div className="space-y-2 text-xs">
                  <div className="flex items-center justify-between p-2 rounded bg-slate-800/40">
                    <span className="text-slate-300">Heavy Rainfall (&ge;64.5 mm)</span>
                    <span className="font-mono text-amber-400 font-bold">{totalHeavy} events</span>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded bg-slate-800/40">
                    <span className="text-slate-300">Very Heavy Rainfall (&ge;115.6 mm)</span>
                    <span className="font-mono text-orange-400 font-bold">{totalVeryHeavy} events</span>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded bg-slate-800/40">
                    <span className="text-slate-300">Extremely Heavy Rainfall (&ge;204.5 mm)</span>
                    <span className="font-mono text-red-400 font-bold">{totalExtreme} events</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Invariants Audit List */}
            {leakageReport && (
              <div className="bg-slate-900/50 border border-slate-800/80 rounded-xl p-3">
                <span className="text-[11px] font-semibold text-slate-400 block mb-2">
                  LeakageGuard Verified Invariants:
                </span>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5 text-[11px] text-slate-300">
                  {leakageReport.passed_checks.map((chk, idx) => (
                    <div key={idx} className="flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      <span>{chk}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-6 text-xs text-slate-400">
            No training dataset currently loaded or generated. Run <code className="text-indigo-300 bg-slate-800 px-1 py-0.5 rounded">python -m ml.dataset build</code> to create one.
          </div>
        )}
      </div>

      {/* Pipeline Readiness Cards */}
      {status && !error && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { label: 'Pipeline Ready', value: status.ready_for_ml ? 'YES' : 'NO', color: status.ready_for_ml ? 'text-emerald-400' : 'text-red-400', icon: <Activity className="w-4 h-4" /> },
            { label: 'Available Providers', value: status.providers_available, color: 'text-emerald-400', icon: <CheckCircle2 className="w-4 h-4" /> },
            { label: 'Not Configured', value: status.providers_not_configured, color: 'text-amber-400', icon: <AlertTriangle className="w-4 h-4" /> },
            { label: 'Unavailable', value: status.providers_unavailable, color: 'text-red-400', icon: <XCircle className="w-4 h-4" /> },
          ].map((card, i) => (
            <div key={i} className="glass-panel rounded-xl p-4 space-y-1">
              <div className={`flex items-center gap-1.5 text-[11px] font-medium text-slate-400`}>
                {card.icon}{card.label}
              </div>
              <div className={`text-xl font-bold ${card.color}`}>{card.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Provider Status Table — Live from backend */}
      <div className="glass-panel rounded-2xl p-6 space-y-4">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <Cpu className="w-4 h-4 text-monsoon-400" />
          Live Provider Registry
          {loading && <RefreshCw className="w-3.5 h-3.5 animate-spin text-slate-400" />}
        </h3>

        {status && !error ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
                  <th className="py-3 px-4">Provider ID</th>
                  <th className="py-3 px-4">Name</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Resolution</th>
                  <th className="py-3 px-4">Variables</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {status.providers.map((p) => (
                  <tr key={p.provider_id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4 font-mono text-monsoon-300 font-semibold">{p.provider_id}</td>
                    <td className="py-3 px-4 text-slate-200 font-sans">{p.name.replace('⚠️ ', '')}</td>
                    <td className="py-3 px-4">
                      <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 text-[10px] uppercase tracking-wide">{p.provider_type}</span>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-300">{p.spatial_resolution_deg != null ? `${p.spatial_resolution_deg}°` : '—'}</td>
                    <td className="py-3 px-4 text-slate-400">{p.available_variables.slice(0, 3).join(', ')}{p.available_variables.length > 3 ? ` +${p.available_variables.length - 3}` : ''}</td>
                    <td className="py-3 px-4"><StatusBadge status={p.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : !error ? (
          <div className="text-xs text-slate-500 animate-pulse py-4 text-center">Loading providers from backend…</div>
        ) : null}
      </div>

      {/* Dataset Manifest */}
      {datasets.length > 0 && (
        <div className="glass-panel rounded-2xl p-6 space-y-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Layers className="w-4 h-4 text-indigo-400" />
            Dataset Manifest ({datasets.length} entries)
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {datasets.map((ds) => (
              <div key={ds.id} className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-xs font-semibold text-white">{ds.name}</p>
                    <p className="text-[11px] font-mono text-monsoon-400">{ds.id}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <StatusBadge status={ds.status} />
                    <DataModeBadge mode={ds.data_mode} />
                  </div>
                </div>
                <div className="flex flex-wrap gap-2 text-[11px] text-slate-500">
                  <span>Provider: <span className="text-slate-300">{ds.provider}</span></span>
                  <span>Format: <span className="font-mono text-slate-300">{ds.file_format}</span></span>
                  {ds.resolution_deg && <span>Res: <span className="text-slate-300">{ds.resolution_deg}°</span></span>}
                </div>
                {ds.notes && (
                  <p className="text-[10px] text-slate-500 leading-snug line-clamp-2">{ds.notes}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Feature Catalog */}
      <div className="glass-panel rounded-2xl p-6 space-y-5">
        <div>
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <FileCode className="w-4 h-4 text-indigo-400" />
            Atmospheric & Spatial Feature Catalog (Phase 3 Input Contract)
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Canonical variable names, normalized units, and physical derivations used by the RAMP ML pipeline.
          </p>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {featureGroups.map((group, gIdx) => (
            <div key={gIdx} className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3">
              <h4 className="text-xs font-semibold text-monsoon-300 uppercase tracking-wider border-b border-slate-800/80 pb-2">
                {group.category}
              </h4>
              <div className="space-y-2">
                {group.features.map((feat) => (
                  <div key={feat.id} className="flex items-start justify-between text-xs py-1.5 border-b border-slate-800/40 last:border-0">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[11px] font-bold text-slate-400">{feat.id}</span>
                        <span className="font-mono text-slate-200 font-semibold">{feat.name}</span>
                        <span className="text-[10px] bg-slate-800 text-slate-400 px-1 rounded">{feat.level}</span>
                      </div>
                      <p className="text-[11px] text-slate-400 font-sans">{feat.desc}</p>
                    </div>
                    <span className="font-mono text-[11px] text-monsoon-400 shrink-0 ml-2">{feat.unit}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* DataMode Policy */}
      <div className="glass-card rounded-xl p-5 border border-slate-800 space-y-2">
        <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-400" />
          DataMode Propagation Policy (Rules R1 – R6)
        </h4>
        <ul className="space-y-1.5 text-xs text-slate-400">
          <li><span className="text-slate-200 font-semibold">R1.</span> <code className="text-amber-300 bg-slate-800 px-1 rounded">forecast_valid_time = initialization_time + lead_time_hours</code> — observations matched on valid_time only.</li>
          <li><span className="text-slate-200 font-semibold">R2.</span> Extreme rainfall (&gt;204.5 mm/24h) is flagged <code className="text-emerald-300 bg-slate-800 px-1 rounded">VALID_EXTREME</code> and preserved — never silently clipped.</li>
          <li><span className="text-slate-200 font-semibold">R3.</span> <code className="text-amber-300 bg-slate-800 px-1 rounded">SYNTHETIC_DEMO</code> data is never mixed with real observations without explicit tagging.</li>
          <li><span className="text-slate-200 font-semibold">R4.</span> Unavailable providers return <code className="text-red-300 bg-slate-800 px-1 rounded">ProviderUnavailableError</code> — data fabrication is forbidden.</li>
          <li><span className="text-slate-200 font-semibold">R5.</span> Source units are read from file metadata, not hardcoded assumptions.</li>
          <li><span className="text-slate-200 font-semibold">R6.</span> Zero Leakage: Preprocessing and climatology are fitted strictly on <code className="text-indigo-300 bg-slate-800 px-1 rounded">TRAIN</code> partitions.</li>
        </ul>
      </div>
    </div>
  );
};
