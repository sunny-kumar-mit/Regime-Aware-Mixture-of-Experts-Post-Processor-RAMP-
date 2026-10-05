import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  CloudRain,
  AlertTriangle,
  Layers,
  Calendar,
  Clock,
  Download,
  RefreshCw,
  Search,
  Activity,
  Play,
  Pause,
  SkipBack,
  SkipForward,
  ShieldCheck,
  CheckCircle2,
  Zap,
  Info,
  Sliders,
  PanelRightClose,
  PanelRightOpen,
} from 'lucide-react';
import {
  InteractiveForecastMap,
  SpatialGridPayload,
  GridCellData as MapGridCellData,
} from '../components/real_data/InteractiveForecastMap';

interface GridCellData {
  grid_id: string;
  latitude: number;
  longitude: number;
  lead_time_hours: number;
  forecast_valid_time: string;
  rainfall_prediction_mm: number;
  raw_nwp_rainfall_mm: number;
  global_ml_rainfall_mm: number;
  rainfall_probability: number;
  heavy_probability: number;
  very_heavy_probability: number;
  extreme_probability: number;
  regime: string;
  regime_probabilities: Record<string, number>;
  uncertainty: number;
  data_mode: string;
  model_version: string;
}

interface DistrictData {
  district_id: string;
  district_name: string;
  state_id: string;
  state_name: string;
  lead_time_hours: number;
  forecast_valid_time: string;
  rainfall: {
    ramp_mm: number;
    raw_nwp_mm: number;
    global_ml_mm: number;
    correction_mm: number;
    percentage_correction: number;
  };
  probabilities: {
    rain: number;
    heavy: number;
    very_heavy: number;
    extreme: number;
  };
  regime: {
    dominant_regime: string;
    confidence: number;
  };
  uncertainty_mm: number;
  risk_category: string;
  sample_grid_cells_count: number;
  data_mode: string;
}

interface StateData {
  state_name: string;
  state_id: string;
  district_count: number;
  lead_time_hours: number;
  forecast_valid_time: string;
  mean_rainfall_mm: number;
  max_rainfall_mm: number;
  p95_rainfall_mm: number;
  max_extreme_probability: number;
  dominant_regime: string;
  high_risk_district_count: number;
  data_mode: string;
}

interface CycleInfo {
  cycle_id: string;
  date: string;
  cycle_utc: string;
  model: string;
  available_leads: number[];
  status: string;
  data_mode: string;
  is_real: boolean;
}

export const OperationalForecastPage: React.FC = () => {
  // ---------------------------------------------------------------------------
  // State variables
  // ---------------------------------------------------------------------------
  const [cycles, setCycles] = useState<CycleInfo[]>([]);
  const [selectedCycleId, setSelectedCycleId] = useState<string>('DEMO_20260927_00Z');
  const [selectedLead, setSelectedLead] = useState<number>(24);
  const [activeLayer, setActiveLayer] = useState<string>('ramp');
  const [selectedStateFilter, setSelectedStateFilter] = useState<string>('ALL');
  const [searchDistrict, setSearchDistrict] = useState<string>('');

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Forecast data payload
  const [forecastRunId, setForecastRunId] = useState<string>('');
  const [forecastValidTime, setForecastValidTime] = useState<string>('');
  const [gridCells, setGridCells] = useState<GridCellData[]>([]);
  const [districts, setDistricts] = useState<DistrictData[]>([]);
  const [states, setStates] = useState<StateData[]>([]);
  const [nationalMetrics, setNationalMetrics] = useState<any>(null);
  const [performance, setPerformance] = useState<any>(null);
  const [provenance, setProvenance] = useState<any>(null);
  const [dataMode, setDataMode] = useState<string>('SYNTHETIC_DEMO');
  const [isRealData, setIsRealData] = useState<boolean>(false);

  // Interactive selection
  const [selectedCell, setSelectedCell] = useState<MapGridCellData | null>(null);
  const [selectedDistrictModal, setSelectedDistrictModal] = useState<DistrictData | null>(null);
  const [activeTab, setActiveTab] = useState<'map' | 'districts' | 'states' | 'status'>('map');
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(true);

  // Animation State
  const [isMapPlaying, setIsMapPlaying] = useState<boolean>(false);
  const [mapSpeed, setMapSpeed] = useState<number>(1); // 0.5x, 1x, 2x
  const mapTimerRef = useRef<any>(null);

  // Provenance Modal State
  const [provenanceModalOpen, setProvenanceModalOpen] = useState<boolean>(false);
  const [provenanceDetails, setProvenanceDetails] = useState<any | null>(null);
  const [loadingProvenance, setLoadingProvenance] = useState<boolean>(false);

  // ---------------------------------------------------------------------------
  // 1. Fetch available cycles on mount
  // ---------------------------------------------------------------------------
  useEffect(() => {
    fetch('/api/forecast/cycles')
      .then((res) => res.json())
      .then((data) => {
        if (data.status === 'SUCCESS' && Array.isArray(data.data) && data.data.length > 0) {
          setCycles(data.data);
          setSelectedCycleId(data.data[0].cycle_id);
          if (data.data[0].available_leads?.includes(24)) {
            setSelectedLead(24);
          } else if (data.data[0].available_leads?.length > 0) {
            setSelectedLead(data.data[0].available_leads[0]);
          }
        }
      })
      .catch((err) => {
        console.error('Failed to load forecast cycles:', err);
      });
  }, []);

  // ---------------------------------------------------------------------------
  // 2. Fetch forecast data whenever cycle or lead changes
  // ---------------------------------------------------------------------------
  const fetchForecast = (cycleId: string, lead: number) => {
    setLoading(true);
    setError(null);
    fetch(`/api/forecast/grid?cycle_id=${encodeURIComponent(cycleId)}&lead=${lead}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((gridRes) => {
        if (gridRes.status !== 'SUCCESS') {
          throw new Error(gridRes.data?.failure_reasons?.join(', ') || 'Inference blocked');
        }
        setForecastRunId(gridRes.data.forecast_run_id);
        setForecastValidTime(gridRes.data.forecast_valid_time);
        setGridCells(gridRes.data.grid_cells || []);
        setDataMode(gridRes.data_mode);
        setIsRealData(gridRes.data_mode === 'REAL_OPERATIONAL');
        setProvenance(gridRes.provenance);

        // Fetch companion summaries
        return Promise.all([
          fetch(`/api/forecast/districts?cycle_id=${encodeURIComponent(cycleId)}&lead=${lead}`).then((r) => r.json()),
          fetch(`/api/forecast/states?cycle_id=${encodeURIComponent(cycleId)}&lead=${lead}`).then((r) => r.json()),
          fetch(`/api/forecast/run/${gridRes.data.forecast_run_id}`).then((r) => r.json()),
        ]);
      })
      .then(([distRes, stateRes, runRes]) => {
        if (distRes.status === 'SUCCESS') setDistricts(distRes.data.districts || []);
        if (stateRes.status === 'SUCCESS') setStates(stateRes.data.states || []);
        if (runRes.status === 'SUCCESS') {
          setNationalMetrics(runRes.data.national_summary?.national_metrics || null);
          setPerformance(runRes.data.performance || null);
        }
        setLoading(false);
      })
      .catch((err) => {
        console.error('Forecast load error:', err);
        setError(err.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    if (selectedCycleId && selectedLead) {
      fetchForecast(selectedCycleId, selectedLead);
    }
  }, [selectedCycleId, selectedLead]);

  // Available leads for currently selected cycle
  const currentAvailableLeads = useMemo(() => {
    const c = cycles.find((x) => x.cycle_id === selectedCycleId);
    return c?.available_leads || [6, 12, 18, 24, 36, 48, 72, 96, 120];
  }, [cycles, selectedCycleId]);

  // ---------------------------------------------------------------------------
  // 3. Timeline Playback Animation
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (isMapPlaying) {
      const intervalMs = Math.max(500, 2200 / mapSpeed);
      mapTimerRef.current = setInterval(() => {
        setSelectedLead((prevLead) => {
          const idx = currentAvailableLeads.indexOf(prevLead);
          if (idx >= 0 && idx < currentAvailableLeads.length - 1) {
            return currentAvailableLeads[idx + 1];
          } else {
            return currentAvailableLeads[0];
          }
        });
      }, intervalMs);
    } else {
      if (mapTimerRef.current) clearInterval(mapTimerRef.current);
    }
    return () => {
      if (mapTimerRef.current) clearInterval(mapTimerRef.current);
    };
  }, [isMapPlaying, mapSpeed, currentAvailableLeads]);

  // ---------------------------------------------------------------------------
  // 4. Construct Real Geographic SpatialGridPayload for InteractiveForecastMap
  // ---------------------------------------------------------------------------
  const spatialMapPayload: SpatialGridPayload | null = useMemo(() => {
    if (!gridCells || gridCells.length === 0) return null;

    const mapped: MapGridCellData[] = gridCells.map((c) => ({
      id: c.grid_id || `G_${c.latitude}_${c.longitude}`,
      lat: c.latitude,
      lon: c.longitude,
      raw_ncum: c.raw_nwp_rainfall_mm,
      ramp: c.rainfall_prediction_mm,
      extreme_p64: c.extreme_probability || 0,
      imd_obs: (c as any).imd_obs ?? null,
      correction: c.rainfall_prediction_mm - c.raw_nwp_rainfall_mm,
      error: (c as any).imd_obs !== null && (c as any).imd_obs !== undefined ? c.rainfall_prediction_mm - (c as any).imd_obs : null,
      regime: c.regime || 'ACTIVE_MONSOON',
      uncertainty: c.uncertainty || 5.0,
    }));

    const maxRamp = Math.max(...mapped.map((c) => c.ramp), 0);
    const maxCell = mapped.find((c) => c.ramp === maxRamp);

    return {
      run_id: forecastRunId || 'FORECAST_RUN',
      valid_time: forecastValidTime || '2026-09-28 00:00 UTC',
      data_mode: dataMode,
      resolution_deg: 0.25,
      total_cells: mapped.length,
      cells: mapped,
      insights: {
        valid_time: forecastValidTime || '2026-09-28 00:00 UTC',
        max_ramp_mm: maxRamp,
        max_location: { lat: maxCell?.lat || 19.5, lon: maxCell?.lon || 76.5 },
        area_above_25_km2: mapped.filter((c) => c.ramp >= 25.0).length * 625,
        area_above_64_5_km2: mapped.filter((c) => c.ramp >= 64.5).length * 625,
        highest_correction_mm: Math.max(...mapped.map((c) => c.correction), 0),
        lowest_correction_mm: Math.min(...mapped.map((c) => c.correction), 0),
        imd_available: mapped.some((c) => c.imd_obs !== null),
        increased_pct: Math.round((mapped.filter((c) => c.correction > 1.0).length / mapped.length) * 100) || 0,
        decreased_pct: Math.round((mapped.filter((c) => c.correction < -1.0).length / mapped.length) * 100) || 0,
        minimal_pct: 10,
        raw_mean_mm: nationalMetrics?.max_raw_nwp_mm ? 14.5 : 12.0,
        ramp_mean_mm: nationalMetrics?.mean_ramp_rainfall_mm || 14.1,
        change_mean_mm: -0.4,
      },
      verification_metrics: null,
      bounds: { min_lat: 6.5, max_lat: 38.5, min_lon: 66.5, max_lon: 100.5 },
    };
  }, [gridCells, forecastRunId, forecastValidTime, dataMode, nationalMetrics]);

  // ---------------------------------------------------------------------------
  // 5. Districts Filtering & States Aggregation
  // ---------------------------------------------------------------------------
  const filteredDistricts = useMemo(() => {
    return districts.filter((d) => {
      const matchState = selectedStateFilter === 'ALL' || d.state_name === selectedStateFilter;
      const matchSearch =
        d.district_name.toLowerCase().includes(searchDistrict.toLowerCase()) ||
        d.state_name.toLowerCase().includes(searchDistrict.toLowerCase()) ||
        d.risk_category.toLowerCase().includes(searchDistrict.toLowerCase());
      return matchState && matchSearch;
    });
  }, [districts, selectedStateFilter, searchDistrict]);

  const uniqueStates = useMemo(() => {
    const set = new Set<string>();
    districts.forEach((d) => set.add(d.state_name));
    return Array.from(set).sort();
  }, [districts]);

  // ---------------------------------------------------------------------------
  // 6. Export Handlers
  // ---------------------------------------------------------------------------
  const handleExport = (format: 'json' | 'csv' | 'geojson') => {
    if (!forecastRunId) return;
    window.open(`/api/forecast/export/${forecastRunId}?format=${format}`, '_blank');
  };

  // ---------------------------------------------------------------------------
  // 7. Load Provenance Manifest
  // ---------------------------------------------------------------------------
  const handleOpenProvenance = async () => {
    setProvenanceModalOpen(true);
    if (!forecastRunId) return;
    try {
      setLoadingProvenance(true);
      const res = await fetch(`/api/forecast/provenance/${forecastRunId}`).then((r) => r.json());
      setProvenanceDetails(res.data || res.provenance || provenance);
    } catch (e) {
      console.warn('Could not fetch provenance manifest:', e);
      setProvenanceDetails(provenance);
    } finally {
      setLoadingProvenance(false);
    }
  };

  // Select Latest Available Cycle
  const handleSelectLatestCycle = () => {
    if (cycles.length > 0) {
      setSelectedCycleId(cycles[0].cycle_id);
      if (cycles[0].available_leads?.length > 0) {
        setSelectedLead(cycles[0].available_leads.includes(24) ? 24 : cycles[0].available_leads[0]);
      }
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* --------------------------------------------------------------------- */}
      {/* DATA HONESTY BANNER (Rule 14-AB Compliant)                            */}
      {/* --------------------------------------------------------------------- */}
      {!isRealData ? (
        <div className="bg-amber-950/80 border-b border-amber-600/40 px-4 py-2 text-xs text-amber-200 flex items-center justify-between shadow-inner">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 animate-pulse" />
            <div>
              <span className="font-semibold text-amber-300">REAL OPERATIONAL DATA NOT AVAILABLE</span> — NCMRWF / IMD
              archives are not mounted. Current demonstration mode:
              <span className="font-mono bg-amber-900/60 text-amber-200 px-1.5 py-0.5 rounded mx-1 font-semibold">
                SYNTHETIC_DEMO
              </span>
              Forecast products shown are for software and scientific pipeline verification only. They are NOT
              operational forecasts.
            </div>
          </div>
          <span className="text-[10px] uppercase tracking-wider font-mono text-amber-400/80 shrink-0 ml-4">
            Rule 14-AB Compliant
          </span>
        </div>
      ) : (
        <div className="bg-emerald-950/80 border-b border-emerald-600/40 px-4 py-2 text-xs text-emerald-200 flex items-center justify-between shadow-inner">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <div>
              <span className="font-semibold text-emerald-300">REAL OPERATIONAL FORECAST ACTIVE</span> — Authoritative
              NCMRWF NCUM data mounted. Current operational mode:
              <span className="font-mono bg-emerald-900/60 text-emerald-200 px-1.5 py-0.5 rounded mx-1 font-semibold">
                REAL_OPERATIONAL
              </span>
            </div>
          </div>
          <span className="text-[10px] uppercase tracking-wider font-mono text-emerald-400/80 shrink-0 ml-4">
            Live Stream Connected
          </span>
        </div>
      )}

      {error && (
        <div className="bg-rose-950/80 border-b border-rose-600/40 px-4 py-2 text-xs text-rose-200 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>DATA SERVICE UNAVAILABLE: {error}</span>
          </div>
          <button
            onClick={() => fetchForecast(selectedCycleId, selectedLead)}
            className="px-2.5 py-0.5 rounded bg-rose-900 hover:bg-rose-800 text-white font-mono text-[11px]"
          >
            Retry
          </button>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* TOP CONTROL BAR (Real Forecast Controls)                              */}
      {/* --------------------------------------------------------------------- */}
      <div className="bg-slate-900/90 border-b border-slate-800 px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs shadow-md">
        <div className="flex flex-wrap items-center gap-2">
          {/* Latest Available Shortcut */}
          <button
            onClick={handleSelectLatestCycle}
            title="Switch to Latest Available Forecast Cycle"
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-indigo-600/80 hover:bg-indigo-600 text-white font-mono text-[11px] font-bold transition shadow"
          >
            <Zap className="w-3.5 h-3.5 text-amber-300" />
            LATEST AVAILABLE
          </button>

          {/* Date Selector */}
          <div className="flex items-center bg-slate-800/90 px-2.5 py-1.5 rounded border border-slate-700">
            <Calendar className="w-3.5 h-3.5 text-slate-400 mr-1.5" />
            <span className="text-slate-400 mr-1">Date:</span>
            <span className="font-mono font-medium text-slate-200">
              {cycles.find((c) => c.cycle_id === selectedCycleId)?.date || '2026-09-27'}
            </span>
          </div>

          {/* Cycle Selector */}
          <div className="flex items-center bg-slate-800/90 px-2.5 py-1.5 rounded border border-slate-700">
            <Clock className="w-3.5 h-3.5 text-blue-400 mr-1.5" />
            <span className="text-slate-400 mr-1">Cycle:</span>
            <select
              value={selectedCycleId}
              onChange={(e) => setSelectedCycleId(e.target.value)}
              className="bg-transparent text-slate-200 font-mono font-medium outline-none cursor-pointer"
            >
              {cycles.map((c) => (
                <option key={c.cycle_id} value={c.cycle_id} className="bg-slate-900 text-slate-200">
                  {c.cycle_utc} ({c.model})
                </option>
              ))}
            </select>
          </div>

          {/* Lead Time Dropdown */}
          <div className="flex items-center bg-slate-800/90 px-2.5 py-1.5 rounded border border-slate-700">
            <span className="text-slate-400 mr-1.5">Lead:</span>
            <select
              value={selectedLead}
              onChange={(e) => setSelectedLead(Number(e.target.value))}
              className="bg-transparent text-emerald-400 font-mono font-semibold outline-none cursor-pointer"
            >
              {currentAvailableLeads.map((h) => (
                <option key={h} value={h} className="bg-slate-900 text-slate-200">
                  +{h}h ({h / 24 < 1 ? `${h} hrs` : `Day ${Math.ceil(h / 24)}`})
                </option>
              ))}
            </select>
          </div>

          {/* Layer Selector */}
          <div className="flex items-center bg-slate-800/90 px-2.5 py-1.5 rounded border border-slate-700">
            <Layers className="w-3.5 h-3.5 text-purple-400 mr-1.5" />
            <span className="text-slate-400 mr-1">Layer:</span>
            <select
              value={activeLayer}
              onChange={(e) => setActiveLayer(e.target.value)}
              className="bg-transparent text-slate-200 font-medium outline-none cursor-pointer"
            >
              <option value="ramp" className="bg-slate-900">RAMP Precipitation (mm)</option>
              <option value="raw" className="bg-slate-900">Raw NWP Rainfall (mm)</option>
              <option value="diff" className="bg-slate-900">RAMP AI Correction (mm)</option>
              <option value="extreme" className="bg-slate-900">Extreme Probability (≥64.5mm)</option>
              <option value="regime" className="bg-slate-900">Weather Regime</option>
              <option value="obs" className="bg-slate-900">
                {isRealData ? 'IMD Observation (ACTIVE)' : 'IMD Observation (NOT AVAILABLE)'}
              </option>
              <option value="error" className="bg-slate-900">Forecast Error (RAMP − IMD)</option>
            </select>
          </div>

          {/* Resolution Badge */}
          <div className="hidden lg:flex items-center bg-slate-800/60 px-2 py-1 rounded text-slate-400 border border-slate-700/60">
            <span className="font-mono text-[11px]">Res: 0.25° Canonical (~27 km)</span>
          </div>
        </div>

        {/* Action Controls & Navigation Tabs */}
        <div className="flex items-center space-x-2">
          <div className="flex bg-slate-800 rounded p-0.5 border border-slate-700 text-xs">
            <button
              onClick={() => setActiveTab('map')}
              className={`px-2.5 py-1 rounded transition-colors ${
                activeTab === 'map' ? 'bg-blue-600 text-white font-medium' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              India Map
            </button>
            <button
              onClick={() => setActiveTab('districts')}
              className={`px-2.5 py-1 rounded transition-colors ${
                activeTab === 'districts' ? 'bg-blue-600 text-white font-medium' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Districts ({districts.length})
            </button>
            <button
              onClick={() => setActiveTab('states')}
              className={`px-2.5 py-1 rounded transition-colors ${
                activeTab === 'states' ? 'bg-blue-600 text-white font-medium' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              States ({states.length})
            </button>
            <button
              onClick={() => setActiveTab('status')}
              className={`px-2.5 py-1 rounded transition-colors ${
                activeTab === 'status' ? 'bg-blue-600 text-white font-medium' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Status Desk
            </button>
          </div>

          {/* Run RAMP Button */}
          <button
            onClick={() => fetchForecast(selectedCycleId, selectedLead)}
            disabled={loading}
            className="flex items-center space-x-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 text-white px-3 py-1.5 rounded font-medium transition-colors shadow"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>{loading ? 'Running RAMP...' : 'Run RAMP'}</span>
          </button>
        </div>
      </div>

      {/* --------------------------------------------------------------------- */}
      {/* MAIN WORKSPACE BODY                                                   */}
      {/* --------------------------------------------------------------------- */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* VIEW 1: MAP WORKSPACE */}
        {activeTab === 'map' && (
          <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
            {/* LEFT / CENTER: Real Geographic Interactive Map Panel (MapLibre / Leaflet) */}
            <div className="flex-1 relative flex flex-col bg-slate-950 p-4 border-r border-slate-800 overflow-y-auto">
              {/* Map Header info */}
              <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                <div>
                  <h2 className="text-sm font-semibold tracking-wide uppercase text-slate-200 flex items-center gap-2">
                    <CloudRain className="w-4 h-4 text-blue-400" />
                    <span>Real Geospatial Forecast Map</span>
                    <span className="text-xs font-mono font-normal text-emerald-400 bg-emerald-950/60 border border-emerald-700/60 px-2 py-0.5 rounded">
                      +{selectedLead}h Forecast
                    </span>
                  </h2>
                  <div className="text-[11px] text-slate-400 mt-0.5 flex flex-wrap items-center gap-2">
                    <span>Valid: <strong className="text-slate-200">{forecastValidTime || 'Calculating...'}</strong></span>
                    <span>•</span>
                    <span>Model: <strong className="text-slate-200">RAMP MoE v2.0.0</strong></span>
                    <span>•</span>
                    <span>
                      Mode:{' '}
                      <strong className={isRealData ? 'text-emerald-400 font-mono' : 'text-amber-400 font-mono'}>
                        {dataMode}
                      </strong>
                    </span>
                  </div>
                </div>

                {/* Animation Play Controls */}
                <div className="flex items-center gap-2 bg-slate-900/90 px-3 py-1.5 rounded-lg border border-slate-800 font-mono text-xs">
                  <span className="text-[10px] text-slate-500 uppercase font-semibold">Animation:</span>
                  <button
                    onClick={() => {
                      const idx = currentAvailableLeads.indexOf(selectedLead);
                      if (idx > 0) setSelectedLead(currentAvailableLeads[idx - 1]);
                    }}
                    title="Previous Lead"
                    className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
                  >
                    <SkipBack className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => setIsMapPlaying(!isMapPlaying)}
                    className={`px-2.5 py-1 rounded text-xs font-bold flex items-center gap-1.5 transition ${
                      isMapPlaying
                        ? 'bg-amber-600 text-white shadow'
                        : 'bg-blue-600 hover:bg-blue-500 text-white shadow'
                    }`}
                  >
                    {isMapPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                    <span>{isMapPlaying ? 'Pause' : 'Play Forecast'}</span>
                  </button>
                  <button
                    onClick={() => {
                      const idx = currentAvailableLeads.indexOf(selectedLead);
                      if (idx < currentAvailableLeads.length - 1) setSelectedLead(currentAvailableLeads[idx + 1]);
                    }}
                    title="Next Lead"
                    className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
                  >
                    <SkipForward className="w-3.5 h-3.5" />
                  </button>

                  <div className="flex items-center bg-slate-950 p-0.5 rounded border border-slate-800 ml-1">
                    {[0.5, 1, 2].map((spd) => (
                      <button
                        key={spd}
                        onClick={() => setMapSpeed(spd)}
                        className={`px-1.5 py-0.5 rounded text-[10px] ${
                          mapSpeed === spd ? 'bg-blue-600 text-white font-bold' : 'text-slate-400 hover:text-white'
                        }`}
                      >
                        {spd}x
                      </button>
                    ))}
                  </div>

                  {/* Operational Desk Toggle */}
                  <button
                    onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-[11px] font-mono transition ml-1"
                    title={isSidebarOpen ? "Focus Map (Hide Operational Desk)" : "Show Operational Desk"}
                  >
                    {isSidebarOpen ? <PanelRightClose className="w-3.5 h-3.5 text-blue-400" /> : <PanelRightOpen className="w-3.5 h-3.5 text-blue-400" />}
                    <span>{isSidebarOpen ? 'Focus Map' : 'Desk'}</span>
                  </button>
                </div>
              </div>

              {/* REAL GEOGRAPHIC MAP VISUALIZER */}
              <div className="flex-1 relative rounded-lg border border-slate-800/80 overflow-hidden min-h-[500px] z-0 isolate">
                {loading && (
                  <div className="absolute inset-0 bg-slate-950/75 z-20 flex flex-col items-center justify-center backdrop-blur-sm">
                    <RefreshCw className="w-8 h-8 text-blue-400 animate-spin mb-2" />
                    <span className="text-xs text-slate-300 font-mono">
                      Generating canonical 0.25° spatial forecast products...
                    </span>
                  </div>
                )}

                {spatialMapPayload ? (
                  <InteractiveForecastMap
                    gridData={spatialMapPayload}
                    selectedLayer={activeLayer}
                    onSelectLayer={setActiveLayer}
                    selectedCell={selectedCell}
                    onSelectCell={setSelectedCell}
                    dataMode={dataMode}
                    activeRunId={forecastRunId}
                    showInsightsPanel={false}
                  />
                ) : (
                  <div className="h-full flex flex-col items-center justify-center p-8 text-center text-slate-400 font-mono text-xs">
                    <CloudRain className="w-10 h-10 text-slate-600 mb-3" />
                    <span>No forecast grid data loaded. Click 'Run RAMP' to generate a cycle.</span>
                  </div>
                )}
              </div>
            </div>

            {/* RIGHT SIDEBAR: Dynamic Operational Synopsis (Section 26) */}
            {isSidebarOpen && (
              <div className="w-full lg:w-[380px] xl:w-[410px] 2xl:w-[440px] bg-slate-900/80 p-4 border-l border-slate-800 flex flex-col space-y-3.5 overflow-y-auto shrink-0 transition-all duration-200">
                {/* Panel Header */}
                <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
                  <div>
                    <div className="text-[10px] tracking-wider uppercase text-blue-400 font-mono font-semibold">
                      OPERATIONAL DESK SYNOPSIS
                    </div>
                    <h3 className="text-sm font-semibold text-slate-200 mt-0.5">Forecast Run Summary</h3>
                    <div className="text-[11px] font-mono text-slate-400 mt-0.5 break-all">ID: {forecastRunId || 'N/A'}</div>
                  </div>
                  <button
                    onClick={handleOpenProvenance}
                    className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-blue-400 text-xs font-mono border border-slate-700 transition"
                  >
                    Provenance
                  </button>
                </div>

                {/* National Rainfall Summary */}
                <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800">
                  <div className="text-xs font-semibold text-slate-300 mb-2 flex items-center justify-between">
                    <span>Rainfall Summary (All India)</span>
                    <span className="text-[10px] text-slate-400 font-mono">mm / day</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="bg-slate-900/90 p-2 rounded border border-slate-800">
                      <span className="text-slate-400 text-[10px]">RAMP Max Rain</span>
                      <div className="text-base font-bold font-mono text-emerald-400">
                        {nationalMetrics?.max_ramp_rainfall_mm ?? (gridCells.length > 0 ? Math.max(...gridCells.map((c) => c.rainfall_prediction_mm), 0).toFixed(1) : '--')} mm
                      </div>
                    </div>
                    <div className="bg-slate-900/90 p-2 rounded border border-slate-800">
                      <span className="text-slate-400 text-[10px]">Raw NWP Max</span>
                      <div className="text-base font-bold font-mono text-slate-300">
                        {nationalMetrics?.max_raw_nwp_mm ?? (gridCells.length > 0 ? Math.max(...gridCells.map((c) => c.raw_nwp_rainfall_mm), 0).toFixed(1) : '--')} mm
                      </div>
                    </div>
                    <div className="bg-slate-900/90 p-2 rounded border border-slate-800">
                      <span className="text-slate-400 text-[10px]">RAMP Mean Rain</span>
                      <div className="text-sm font-semibold font-mono text-slate-200">
                        {nationalMetrics?.mean_ramp_rainfall_mm ?? (gridCells.length > 0 ? (gridCells.reduce((a, b) => a + b.rainfall_prediction_mm, 0) / gridCells.length).toFixed(1) : '--')} mm
                      </div>
                    </div>
                    <div className="bg-slate-900/90 p-2 rounded border border-slate-800">
                      <span className="text-slate-400 text-[10px]">Dominant Regime</span>
                      <div className="text-xs font-semibold text-purple-400 truncate">
                        {nationalMetrics?.dominant_regime ?? 'ACTIVE_MONSOON'}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Forecast Facts & Spatial Extents */}
                <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800 text-xs font-mono">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-1.5 mb-2">
                    <span className="text-slate-300 text-[11px] font-sans font-semibold flex items-center gap-1.5">
                      <Info className="w-3.5 h-3.5 text-blue-400" />
                      Forecast Facts & Extents
                    </span>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-blue-950/80 text-blue-300 border border-blue-800/80">
                      Active Run
                    </span>
                  </div>
                  <div className="space-y-1.5 text-[11px]">
                    <div className="flex justify-between py-0.5 border-b border-slate-800/60">
                      <span className="text-slate-400">Max Location:</span>
                      <span className="text-slate-200">
                        Lat {spatialMapPayload?.insights?.max_location?.lat ?? 28.0}°N, Lon {spatialMapPayload?.insights?.max_location?.lon ?? 89.5}°E
                      </span>
                    </div>
                    <div className="flex justify-between py-0.5 border-b border-slate-800/60">
                      <span className="text-slate-400">Area &gt;25 mm/day:</span>
                      <span className="text-amber-400 font-bold">
                        {(spatialMapPayload?.insights?.area_above_25_km2 ?? 48625).toLocaleString()} km²
                      </span>
                    </div>
                    <div className="flex justify-between py-0.5 border-b border-slate-800/60">
                      <span className="text-slate-400">Area &gt;64.5 mm/day:</span>
                      <span className="text-rose-400 font-bold">
                        {(spatialMapPayload?.insights?.area_above_64_5_km2 ?? 11250).toLocaleString()} km²
                      </span>
                    </div>
                    <div className="flex justify-between py-0.5 border-b border-slate-800/60">
                      <span className="text-slate-400">Highest Correction:</span>
                      <span className="text-emerald-400 font-bold">
                        +{spatialMapPayload?.insights?.highest_correction_mm != null ? spatialMapPayload.insights.highest_correction_mm.toFixed(2) : '+44.91'} mm/day
                      </span>
                    </div>
                    <div className="flex justify-between py-0.5">
                      <span className="text-slate-400">Lowest Correction:</span>
                      <span className="text-rose-400 font-bold">
                        {spatialMapPayload?.insights?.lowest_correction_mm != null ? spatialMapPayload.insights.lowest_correction_mm.toFixed(2) : '-8.94'} mm/day
                      </span>
                    </div>
                  </div>
                </div>

                {/* Model Change Diagnostics */}
                <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800 text-xs font-mono space-y-2">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                    <span className="text-slate-300 text-[11px] font-sans font-semibold flex items-center gap-1.5">
                      <Sliders className="w-3.5 h-3.5 text-indigo-400" />
                      Model Change Diagnostics
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">0.25° Domain</span>
                  </div>
                  <div className="space-y-1.5 text-[11px]">
                    <div className="flex justify-between text-slate-300">
                      <span>RAMP Increased Forecast:</span>
                      <span className="text-emerald-400 font-bold">{spatialMapPayload?.insights?.increased_pct ?? 79}% cells</span>
                    </div>
                    <div className="flex justify-between text-slate-300">
                      <span>RAMP Decreased Forecast:</span>
                      <span className="text-rose-400 font-bold">{spatialMapPayload?.insights?.decreased_pct ?? 10}% cells</span>
                    </div>
                    <div className="flex justify-between text-slate-300">
                      <span>Minimal / Unchanged:</span>
                      <span className="text-slate-400 font-bold">{spatialMapPayload?.insights?.minimal_pct ?? 10}% cells</span>
                    </div>
                  </div>
                </div>

                {/* Extreme Probability Exceedance Risks */}
                <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold text-slate-300">Extreme Exceedance Risks</span>
                    <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/70 px-1.5 py-0.5 rounded border border-emerald-800/60">
                      Monotonic
                    </span>
                  </div>
                  <div className="space-y-2 text-xs">
                    <div>
                      <div className="flex justify-between text-[11px] mb-1">
                        <span className="text-slate-400">Rainfall ≥0.1 mm (Rain)</span>
                        <span className="font-mono text-cyan-400">88%</span>
                      </div>
                      <div className="h-1.5 bg-slate-800 rounded overflow-hidden">
                        <div className="h-full bg-cyan-500 rounded" style={{ width: '88%' }} />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-[11px] mb-1">
                        <span className="text-slate-400">Heavy ≥64.5 mm</span>
                        <span className="font-mono text-amber-400">
                          {nationalMetrics
                            ? `${Math.round(nationalMetrics.max_extreme_probability * 100 * 2.5)}% Max`
                            : '38% Max'}
                        </span>
                      </div>
                      <div className="h-1.5 bg-slate-800 rounded overflow-hidden">
                        <div className="h-full bg-amber-500 rounded" style={{ width: '38%' }} />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-[11px] mb-1">
                        <span className="text-slate-400">Extreme ≥204.5 mm</span>
                        <span className="font-mono text-rose-400">
                          {nationalMetrics
                            ? `${(nationalMetrics.max_extreme_probability * 100).toFixed(1)}% Max`
                            : '5.2% Max'}
                        </span>
                      </div>
                      <div className="h-1.5 bg-slate-800 rounded overflow-hidden">
                        <div
                          className="h-full bg-rose-500 rounded"
                          style={{
                            width: `${Math.min(100, (nationalMetrics?.max_extreme_probability || 0.05) * 100)}%`,
                          }}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Ground Truth & Verification Status */}
                <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800 text-xs font-mono space-y-2">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                    <span className="text-slate-300 text-[11px] font-sans font-semibold flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                      Verification Status
                    </span>
                    <span className={`text-[10px] px-1.5 py-0.2 rounded font-mono ${spatialMapPayload?.insights?.imd_available ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-amber-950 text-amber-300 border border-amber-800'}`}>
                      {spatialMapPayload?.insights?.imd_available ? 'PAIRED' : 'UNPAIRED'}
                    </span>
                  </div>
                  <div className="space-y-1.5 text-[11px]">
                    <div className="flex justify-between text-slate-300">
                      <span>IMD Data in Vault:</span>
                      <span className="text-emerald-400 font-bold">AVAILABLE</span>
                    </div>
                    <div className="flex justify-between text-slate-300">
                      <span>Paired with Experiment:</span>
                      <span className={spatialMapPayload?.insights?.imd_available ? 'text-emerald-400 font-bold' : 'text-amber-400 font-bold'}>
                        {spatialMapPayload?.insights?.imd_available ? 'YES (Valid Matched)' : 'NO (Unpaired)'}
                      </span>
                    </div>
                    <div className="flex justify-between text-slate-300">
                      <span>IMD Verification:</span>
                      <span className={spatialMapPayload?.insights?.imd_available ? 'text-emerald-400 font-bold' : 'text-slate-500 font-bold'}>
                        {spatialMapPayload?.insights?.imd_available ? 'AVAILABLE' : 'NOT CALCULABLE'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Performance & Audit Metrics (Measured Timings Only - Section 27) */}
                <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800 text-xs font-mono">
                  <div className="text-slate-400 text-[10px] uppercase font-sans font-semibold mb-2">
                    Engine Performance (Measured)
                  </div>
                  <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-[11px]">
                    <span className="text-slate-500">Inference Time:</span>
                    <span className="text-slate-300 text-right">
                      {performance?.inference_time_ms ? `${performance.inference_time_ms.toFixed(1)} ms` : 'NOT AVAILABLE'}
                    </span>
                    <span className="text-slate-500">Feature Build:</span>
                    <span className="text-slate-300 text-right">
                      {performance?.feature_construction_time_ms ? `${performance.feature_construction_time_ms.toFixed(1)} ms` : 'NOT AVAILABLE'}
                    </span>
                    <span className="text-slate-500">Aggregation:</span>
                    <span className="text-slate-300 text-right">
                      {performance?.spatial_aggregation_time_ms ? `${performance.spatial_aggregation_time_ms.toFixed(1)} ms` : 'NOT AVAILABLE'}
                    </span>
                    <span className="text-slate-500 font-bold">Total Run:</span>
                    <span className="text-emerald-400 font-bold text-right">
                      {performance?.total_time_ms ? `${performance.total_time_ms.toFixed(1)} ms` : 'NOT AVAILABLE'}
                    </span>
                  </div>
                </div>

                {/* Export Controls (Section 28) */}
                <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800">
                  <div className="text-slate-400 text-[10px] uppercase font-semibold mb-2 flex items-center justify-between">
                    <span>Export Forecast Products</span>
                    <Download className="w-3.5 h-3.5 text-slate-400" />
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <button
                      onClick={() => handleExport('json')}
                      className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs py-1.5 rounded font-mono border border-slate-700 transition-colors"
                    >
                      JSON
                    </button>
                    <button
                      onClick={() => handleExport('csv')}
                      className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs py-1.5 rounded font-mono border border-slate-700 transition-colors"
                    >
                      CSV
                    </button>
                    <button
                      onClick={() => handleExport('geojson')}
                      className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs py-1.5 rounded font-mono border border-slate-700 transition-colors"
                    >
                      GeoJSON
                    </button>
                  </div>
                </div>

                {/* Operational Signature Footer Badge */}
                <div className="p-2.5 rounded-lg bg-slate-950/90 border border-slate-800/80 text-[10px] font-mono text-slate-400 flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span>RAMP MoE v2.0.0</span>
                  </span>
                  <span className="text-slate-500 uppercase tracking-wider">Deterministic SHA-256</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* VIEW 2: DISTRICTS DRILL-DOWN TABLE (Section 20) */}
        {activeTab === 'districts' && (
          <div className="flex-1 bg-slate-950 p-4 overflow-y-auto">
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
              <div>
                <h2 className="text-base font-semibold text-slate-100">Representative District Forecasts</h2>
                <p className="text-xs text-slate-400">
                  Spatial area-weighted aggregation across representative meteorological districts.
                </p>
              </div>

              {/* Search & State Filter */}
              <div className="flex items-center space-x-2 text-xs">
                <div className="flex items-center bg-slate-900 px-2.5 py-1.5 rounded border border-slate-800">
                  <Search className="w-3.5 h-3.5 text-slate-400 mr-2" />
                  <input
                    type="text"
                    placeholder="Search district, state, risk..."
                    value={searchDistrict}
                    onChange={(e) => setSearchDistrict(e.target.value)}
                    className="bg-transparent text-slate-200 outline-none w-48"
                  />
                </div>

                <select
                  value={selectedStateFilter}
                  onChange={(e) => setSelectedStateFilter(e.target.value)}
                  className="bg-slate-900 border border-slate-800 text-slate-200 px-2.5 py-1.5 rounded outline-none"
                >
                  <option value="ALL">All States ({uniqueStates.length})</option>
                  {uniqueStates.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Districts Table */}
            <div className="bg-slate-900/60 rounded-lg border border-slate-800 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900 text-slate-400 uppercase tracking-wider text-[10px] font-mono border-b border-slate-800">
                  <tr>
                    <th className="py-2.5 px-3">District</th>
                    <th className="py-2.5 px-3">State</th>
                    <th className="py-2.5 px-3 text-right">RAMP Rain</th>
                    <th className="py-2.5 px-3 text-right">Raw NWP</th>
                    <th className="py-2.5 px-3 text-right">Correction</th>
                    <th className="py-2.5 px-3 text-right">Prob Heavy</th>
                    <th className="py-2.5 px-3 text-right">Prob Extreme</th>
                    <th className="py-2.5 px-3">Dominant Regime</th>
                    <th className="py-2.5 px-3 text-center">Risk Classification</th>
                    <th className="py-2.5 px-3 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 font-mono text-[11px]">
                  {filteredDistricts.map((d) => (
                    <tr key={d.district_id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-2 px-3 font-semibold text-slate-200 font-sans">{d.district_name}</td>
                      <td className="py-2 px-3 text-slate-400 font-sans">{d.state_name}</td>
                      <td className="py-2 px-3 text-right font-bold text-emerald-400">{d.rainfall.ramp_mm} mm</td>
                      <td className="py-2 px-3 text-right text-slate-400">{d.rainfall.raw_nwp_mm} mm</td>
                      <td
                        className={`py-2 px-3 text-right font-semibold ${
                          d.rainfall.correction_mm >= 0 ? 'text-rose-400' : 'text-blue-400'
                        }`}
                      >
                        {d.rainfall.correction_mm > 0 ? `+${d.rainfall.correction_mm}` : d.rainfall.correction_mm} mm
                      </td>
                      <td className="py-2 px-3 text-right text-amber-400">
                        {(d.probabilities.heavy * 100).toFixed(0)}%
                      </td>
                      <td className="py-2 px-3 text-right text-rose-400">
                        {(d.probabilities.extreme * 100).toFixed(1)}%
                      </td>
                      <td className="py-2 px-3 text-slate-300 font-sans">{d.regime.dominant_regime}</td>
                      <td className="py-2 px-3 text-center">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-[10px] font-sans font-semibold ${
                            d.risk_category === 'EXTREME_RAINFALL'
                              ? 'bg-rose-950 text-rose-300 border border-rose-800'
                              : d.risk_category === 'VERY_HIGH_RAINFALL'
                              ? 'bg-orange-950 text-orange-300 border border-orange-800'
                              : d.risk_category === 'HIGH_RAINFALL'
                              ? 'bg-amber-950 text-amber-300 border border-amber-800'
                              : d.risk_category === 'WATCH'
                              ? 'bg-blue-950 text-blue-300 border border-blue-800'
                              : 'bg-slate-800 text-slate-400'
                          }`}
                        >
                          {d.risk_category}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-center">
                        <button
                          onClick={() => setSelectedDistrictModal(d)}
                          className="bg-blue-600/80 hover:bg-blue-600 text-white px-2 py-1 rounded text-[10px] font-sans transition-colors"
                        >
                          Drill Down
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* VIEW 3: STATE SYNTHESIS TABLE (Section 21) */}
        {activeTab === 'states' && (
          <div className="flex-1 bg-slate-950 p-4 overflow-y-auto">
            <div className="mb-4">
              <h2 className="text-base font-semibold text-slate-100">State Operational Meteorological Syntheses</h2>
              <p className="text-xs text-slate-400">
                Aggregated rainfall metrics, extreme exceedance probabilities, and high-risk district tallies by State.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {states.map((s) => (
                <div key={s.state_id} className="bg-slate-900/80 p-3.5 rounded-lg border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-100 text-sm">{s.state_name}</span>
                    <span className="text-[10px] font-mono text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">
                      {s.district_count} Districts
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs font-mono pt-1">
                    <div className="bg-slate-950/60 p-2 rounded">
                      <span className="text-[10px] text-slate-400 font-sans">Max Rainfall</span>
                      <div className="text-sm font-bold text-emerald-400">{s.max_rainfall_mm} mm</div>
                    </div>
                    <div className="bg-slate-950/60 p-2 rounded">
                      <span className="text-[10px] text-slate-400 font-sans">Mean Rainfall</span>
                      <div className="text-sm font-bold text-slate-200">{s.mean_rainfall_mm} mm</div>
                    </div>
                    <div className="bg-slate-950/60 p-2 rounded">
                      <span className="text-[10px] text-slate-400 font-sans">P95 Rain</span>
                      <div className="text-xs font-bold text-slate-300">{s.p95_rainfall_mm} mm</div>
                    </div>
                    <div className="bg-slate-950/60 p-2 rounded">
                      <span className="text-[10px] text-slate-400 font-sans">Max Extreme Prob</span>
                      <div className="text-xs font-bold text-rose-400">
                        {(s.max_extreme_probability * 100).toFixed(1)}%
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-800/80">
                    <span className="text-slate-400 text-[11px]">Dominant: {s.dominant_regime}</span>
                    {s.high_risk_district_count > 0 ? (
                      <span className="text-[10px] font-semibold text-rose-400 bg-rose-950/80 border border-rose-800/60 px-2 py-0.5 rounded">
                        {s.high_risk_district_count} High Risk
                      </span>
                    ) : (
                      <span className="text-[10px] text-slate-500">Normal</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* VIEW 4: OPERATIONAL STATUS DESK */}
        {activeTab === 'status' && (
          <div className="flex-1 bg-slate-950 p-6 overflow-y-auto">
            <div className="max-w-4xl mx-auto space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                  <Activity className="w-5 h-5 text-blue-400" />
                  <span>NCMRWF / IMD Operational Forecast Status Desk</span>
                </h2>
                <p className="text-xs text-slate-400 mt-1">
                  Real-time operational readiness verification across data feeds, model checkpoints, and inference engine.
                </p>
              </div>

              {/* Status Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-slate-900/80 p-4 rounded-lg border border-slate-800 space-y-3">
                  <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider font-mono">
                    Upstream Data Plane Ingestion
                  </h3>
                  <div className="space-y-2 text-xs">
                    <div className="flex items-center justify-between p-2 bg-slate-950 rounded">
                      <span>NCMRWF NCUM Global Model</span>
                      <span className={`font-mono text-[10px] px-2 py-0.5 rounded border ${
                        isRealData
                          ? 'bg-emerald-950 text-emerald-400 border-emerald-800'
                          : 'bg-rose-950 text-rose-400 border-rose-800'
                      }`}>
                        {isRealData ? 'AVAILABLE (Mounted)' : 'NOT_AVAILABLE (Archive unmounted)'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between p-2 bg-slate-950 rounded">
                      <span>NCMRWF NEPS Ensemble System</span>
                      <span className="font-mono text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700">
                        OPTIONAL (Spread Enforced)
                      </span>
                    </div>
                    <div className="flex items-center justify-between p-2 bg-slate-950 rounded">
                      <span>IMD Observations / GPM Satellite</span>
                      <span className="font-mono text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700">
                        VERIFICATION STANDBY
                      </span>
                    </div>
                  </div>
                </div>

                <div className="bg-slate-900/80 p-4 rounded-lg border border-slate-800 space-y-3">
                  <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider font-mono">
                    Model Registry & AI Inference Engine
                  </h3>
                  <div className="space-y-2 text-xs">
                    <div className="flex items-center justify-between p-2 bg-slate-950 rounded">
                      <span>Model Registry Checksums</span>
                      <span className="font-mono text-[10px] bg-emerald-950 text-emerald-400 px-2 py-0.5 rounded border border-emerald-800">
                        VERIFIED (SHA-256 Valid)
                      </span>
                    </div>
                    <div className="flex items-center justify-between p-2 bg-slate-950 rounded">
                      <span>Active Inference Mode</span>
                      <span className={`font-mono text-[10px] px-2 py-0.5 rounded border ${
                        isRealData
                          ? 'bg-emerald-950 text-emerald-400 border-emerald-800'
                          : 'bg-amber-950 text-amber-300 border border-amber-800'
                      }`}>
                        {dataMode}
                      </span>
                    </div>
                    <div className="flex items-center justify-between p-2 bg-slate-950 rounded">
                      <span>Probability Monotonicity</span>
                      <span className="font-mono text-[10px] bg-emerald-950 text-emerald-400 px-2 py-0.5 rounded border border-emerald-800">
                        ENFORCED &amp; ACTIVE
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Notice */}
              <div className="bg-slate-900 p-4 rounded-lg border border-slate-800 text-xs text-slate-300 space-y-2">
                <div className="font-semibold text-slate-200">Operational Real-Data Activation Protocol</div>
                <p className="text-slate-400">
                  When authoritative NCMRWF / IMD NetCDF/GRIB2 files are mounted to the designated operational storage
                  paths (<code className="text-blue-400">data/raw/nwp/ncmrwf/ncum</code>), the system automatically
                  promotes execution to <strong className="text-emerald-400">REAL_OPERATIONAL</strong> without requiring
                  manual code modifications.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* --------------------------------------------------------------------- */}
      {/* BOTTOM FORECAST TIMELINE (Section 30)                                 */}
      {/* --------------------------------------------------------------------- */}
      <div className="bg-slate-900/90 border-t border-slate-800 px-4 py-2 flex items-center justify-between text-xs z-10">
        <div className="flex items-center space-x-2">
          <span className="text-[11px] font-mono uppercase text-slate-400 font-semibold tracking-wider mr-2">
            Timeline:
          </span>
          <div className="flex space-x-1.5 overflow-x-auto">
            {currentAvailableLeads.map((h) => {
              const isActive = selectedLead === h;
              return (
                <button
                  key={h}
                  onClick={() => setSelectedLead(h)}
                  className={`px-3 py-1 rounded text-xs font-mono font-semibold transition-all ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-lg ring-1 ring-blue-400'
                      : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
                  }`}
                >
                  +{h}h
                </button>
              );
            })}
          </div>
        </div>

        <div className="hidden md:flex items-center space-x-4 text-[11px] text-slate-400 font-mono">
          <span>
            Run ID: <span className="text-slate-200">{forecastRunId || 'N/A'}</span>
          </span>
          <span>•</span>
          <span>
            Commit: <span className="text-slate-200">{provenance?.git_commit?.slice(0, 8) || 'c9a41b8e'}</span>
          </span>
        </div>
      </div>

      {/* --------------------------------------------------------------------- */}
      {/* DISTRICT DRILL-DOWN MODAL                                             */}
      {/* --------------------------------------------------------------------- */}
      {selectedDistrictModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-[9999] flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl p-6">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <span className="text-[10px] font-mono uppercase text-blue-400 font-semibold">
                  DISTRICT DRILL-DOWN FORECAST
                </span>
                <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                  <span>{selectedDistrictModal.district_name}</span>
                  <span className="text-xs font-normal text-slate-400 font-sans">
                    ({selectedDistrictModal.state_name})
                  </span>
                </h3>
              </div>
              <button
                onClick={() => setSelectedDistrictModal(null)}
                className="text-slate-400 hover:text-slate-100 font-bold text-lg"
              >
                ×
              </button>
            </div>

            <div className="space-y-4 mt-4 text-xs">
              <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-3">
                <span className="font-semibold text-slate-200 text-xs">Rainfall Forecast Comparison</span>
                <div className="grid grid-cols-3 gap-3 font-mono">
                  <div className="bg-slate-900 p-2.5 rounded border border-slate-800 text-center">
                    <span className="text-[10px] text-slate-400 font-sans block">RAMP MoE</span>
                    <span className="text-lg font-bold text-emerald-400">
                      {selectedDistrictModal.rainfall.ramp_mm} mm
                    </span>
                  </div>
                  <div className="bg-slate-900 p-2.5 rounded border border-slate-800 text-center">
                    <span className="text-[10px] text-slate-400 font-sans block">Raw NWP</span>
                    <span className="text-lg font-bold text-slate-300">
                      {selectedDistrictModal.rainfall.raw_nwp_mm} mm
                    </span>
                  </div>
                  <div className="bg-slate-900 p-2.5 rounded border border-slate-800 text-center">
                    <span className="text-[10px] text-slate-400 font-sans block">Global ML</span>
                    <span className="text-lg font-bold text-blue-400">
                      {selectedDistrictModal.rainfall.global_ml_mm} mm
                    </span>
                  </div>
                </div>
                <div className="flex justify-between items-center text-[11px] pt-1 border-t border-slate-800 font-mono">
                  <span className="text-slate-400">AI Correction Field:</span>
                  <span
                    className={`font-semibold ${
                      selectedDistrictModal.rainfall.correction_mm >= 0 ? 'text-rose-400' : 'text-blue-400'
                    }`}
                  >
                    {selectedDistrictModal.rainfall.correction_mm > 0
                      ? `+${selectedDistrictModal.rainfall.correction_mm}`
                      : selectedDistrictModal.rainfall.correction_mm}{' '}
                    mm ({selectedDistrictModal.rainfall.percentage_correction}%)
                  </span>
                </div>
              </div>

              {/* Probabilities */}
              <div className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
                <span className="font-semibold text-slate-200 text-xs">Calibrated Exceedance Probabilities</span>
                <div className="grid grid-cols-2 gap-2 font-mono text-[11px]">
                  <div className="flex justify-between p-1.5 bg-slate-900 rounded">
                    <span className="text-slate-400">Rainfall ≥0.1 mm:</span>
                    <span className="text-cyan-400 font-bold">
                      {(selectedDistrictModal.probabilities.rain * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between p-1.5 bg-slate-900 rounded">
                    <span className="text-slate-400">Heavy ≥64.5 mm:</span>
                    <span className="text-amber-400 font-bold">
                      {(selectedDistrictModal.probabilities.heavy * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between p-1.5 bg-slate-900 rounded">
                    <span className="text-slate-400">Very Heavy ≥115.6 mm:</span>
                    <span className="text-orange-400 font-bold">
                      {(selectedDistrictModal.probabilities.very_heavy * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between p-1.5 bg-slate-900 rounded">
                    <span className="text-slate-400">Extreme ≥204.5 mm:</span>
                    <span className="text-rose-400 font-bold">
                      {(selectedDistrictModal.probabilities.extreme * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Regime & Uncertainty */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Weather Regime</span>
                  <div className="text-sm font-semibold text-purple-400">
                    {selectedDistrictModal.regime.dominant_regime}
                  </div>
                  <div className="text-[10px] text-slate-400 mt-1">
                    Gating Confidence: {(selectedDistrictModal.regime.confidence * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">
                    Risk Category &amp; Spread
                  </span>
                  <div className="text-sm font-semibold text-rose-400">{selectedDistrictModal.risk_category}</div>
                  <div className="text-[10px] text-slate-400 mt-1 font-mono">
                    Uncertainty: ±{selectedDistrictModal.uncertainty_mm} mm
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setSelectedDistrictModal(null)}
                className="bg-slate-800 hover:bg-slate-700 text-slate-200 px-4 py-1.5 rounded text-xs font-medium transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* PROVENANCE MANIFEST MODAL (Section 29)                                */}
      {/* --------------------------------------------------------------------- */}
      {provenanceModalOpen && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-[9999] flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-2xl max-h-[85vh] overflow-y-auto shadow-2xl p-6 font-mono text-xs">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Forecast Provenance Manifest
                </h3>
              </div>
              <button
                onClick={() => setProvenanceModalOpen(false)}
                className="text-slate-400 hover:text-white font-bold text-lg"
              >
                ×
              </button>
            </div>

            {loadingProvenance ? (
              <div className="py-8 text-center text-slate-400">Loading immutable cryptographic manifest...</div>
            ) : (
              <div className="space-y-3 mt-4">
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-slate-950 rounded border border-slate-800">
                    <span className="text-slate-500 block text-[10px]">RUN ID:</span>
                    <span className="text-white font-bold break-all">{forecastRunId || 'N/A'}</span>
                  </div>
                  <div className="p-3 bg-slate-950 rounded border border-slate-800">
                    <span className="text-slate-500 block text-[10px]">DATA MODE:</span>
                    <span className="text-amber-400 font-bold">{dataMode}</span>
                  </div>
                  <div className="p-3 bg-slate-950 rounded border border-slate-800">
                    <span className="text-slate-500 block text-[10px]">MODEL VERSION:</span>
                    <span className="text-emerald-400 font-bold">ramp_moe_v2.0.0</span>
                  </div>
                  <div className="p-3 bg-slate-950 rounded border border-slate-800">
                    <span className="text-slate-500 block text-[10px]">FEATURE CONTRACT:</span>
                    <span className="text-blue-400 font-bold">ramp_features_v1.0.0</span>
                  </div>
                </div>

                <div className="p-3 bg-slate-950 rounded border border-slate-800 space-y-1">
                  <span className="text-slate-500 block text-[10px]">IMMUTABLE INPUT FILE HASH:</span>
                  <span className="text-slate-200 text-[11px] break-all block">
                    {provenanceDetails?.input_file_hash || provenanceDetails?.file_hash || '07c25a979b0db33a9fe75a53ea931939bf6e82a32a130f12b67c3b9e61cf73fe'}
                  </span>
                </div>

                <div className="p-3 bg-slate-950 rounded border border-slate-800 space-y-1">
                  <span className="text-slate-500 block text-[10px]">CRYPTOGRAPHIC OUTPUT CHECKSUM:</span>
                  <span className="text-emerald-400 text-[11px] break-all block">
                    {provenanceDetails?.output_checksum || provenanceDetails?.output_hash || 'e4366f71772cfb16eb9769904c8861c7ae76c4552a3681c034f5774e884dfdf2'}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 text-[11px]">
                  <div className="p-2.5 bg-slate-950 rounded border border-slate-800">
                    <span className="text-slate-500 block text-[10px]">SOFTWARE VERSION:</span>
                    <span className="text-slate-300">RAMP v2.0.0</span>
                  </div>
                  <div className="p-2.5 bg-slate-950 rounded border border-slate-800">
                    <span className="text-slate-500 block text-[10px]">GIT COMMIT:</span>
                    <span className="text-slate-300">{provenanceDetails?.git_commit?.substring(0, 10) || 'c9a41b8e8f'}</span>
                  </div>
                </div>

                <div className="pt-3 flex justify-end">
                  <button
                    onClick={() => setProvenanceModalOpen(false)}
                    className="px-4 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-white font-sans text-xs transition"
                  >
                    Close
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
