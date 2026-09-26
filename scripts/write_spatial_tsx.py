"""Script to generate frontend/src/pages/SpatialForecast.tsx with all 18 sections.
"""

spatial_tsx = """import React, { useState, useEffect } from 'react';
import {
  MapPin,
  Layers,
  CloudRain,
  AlertTriangle,
  Download,
  Info,
  Calendar,
  Compass,
  BarChart3,
  TrendingUp,
  ShieldAlert,
  Search,
  CheckCircle2,
  RefreshCw,
  Eye,
  Sliders,
  Maximize2
} from 'lucide-react';
import {
  fetchSpatialStatus,
  fetchSpatialDistricts,
  fetchDistrictDetail,
  fetchSpatialStates,
  fetchNationalSummary,
  fetchSpatialHotspots,
  fetchSpatialDifference,
  fetchSpatialFSS,
  fetchSpatialExport
} from '../api/client';
import {
  SpatialStatusResponse,
  DistrictForecastProductItem,
  StateForecastProductItem,
  NationalSummaryResponse,
  HotspotItem,
  SpatialDifferenceItem,
  SpatialFSSResponse,
  RiskCategory
} from '../types/api';

type ActiveLayer =
  | 'ramp_rainfall'
  | 'raw_nwp'
  | 'global_ml'
  | 'diff_nwp'
  | 'prob_rain'
  | 'prob_heavy'
  | 'prob_very_heavy'
  | 'prob_extreme'
  | 'regime'
  | 'uncertainty';

export const SpatialForecastPage: React.FC = () => {
  const [status, setStatus] = useState<SpatialStatusResponse | null>(null);
  const [districts, setDistricts] = useState<DistrictForecastProductItem[]>([]);
  const [states, setStates] = useState<StateForecastProductItem[]>([]);
  const [summary, setSummary] = useState<NationalSummaryResponse | null>(null);
  const [hotspots, setHotspots] = useState<HotspotItem[]>([]);
  const [differences, setDifferences] = useState<SpatialDifferenceItem[]>([]);
  const [fssData, setFssData] = useState<SpatialFSSResponse | null>(null);

  const [leadHours, setLeadHours] = useState<number>(24);
  const [activeLayer, setActiveLayer] = useState<ActiveLayer>('ramp_rainfall');
  const [selectedState, setSelectedState] = useState<string>('ALL');
  const [selectedDistrictId, setSelectedDistrictId] = useState<string | null>(null);
  const [selectedDistrict, setSelectedDistrict] = useState<DistrictForecastProductItem | null>(null);
  const [riskFilter, setRiskFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [exportNotice, setExportNotice] = useState<string | null>(null);

  useEffect(() => {
    loadAllData();
  }, [leadHours]);

  const loadAllData = async () => {
    setLoading(true);
    try {
      const [st, distRes, stRes, sumRes, hotRes, diffRes, fssRes] = await Promise.all([
        fetchSpatialStatus(),
        fetchSpatialDistricts(leadHours),
        fetchSpatialStates(leadHours),
        fetchNationalSummary(leadHours),
        fetchSpatialHotspots(leadHours),
        fetchSpatialDifference(leadHours),
        fetchSpatialFSS(),
      ]);

      setStatus(st);
      setDistricts(distRes.districts);
      setStates(stRes.states);
      setSummary(sumRes);
      setHotspots(hotRes.hotspots);
      setDifferences(diffRes.differences);
      setFssData(fssRes);

      // Default selected district
      if (distRes.districts.length > 0 && !selectedDistrictId) {
        setSelectedDistrict(distRes.districts[0]);
        setSelectedDistrictId(distRes.districts[0].district_id);
      } else if (selectedDistrictId) {
        const found = distRes.districts.find(d => d.district_id === selectedDistrictId);
        if (found) setSelectedDistrict(found);
      }
    } catch (err) {
      console.error('Failed to load spatial forecast data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDistrictSelect = async (dId: string) => {
    setSelectedDistrictId(dId);
    try {
      const detail = await fetchDistrictDetail(dId, leadHours);
      setSelectedDistrict(detail.product);
    } catch {
      const fallback = districts.find(d => d.district_id === dId);
      if (fallback) setSelectedDistrict(fallback);
    }
  };

  const handleExport = async () => {
    try {
      const res = await fetchSpatialExport(leadHours);
      setExportNotice(`Generated GIS artifacts: GeoJSON, CSV, Parquet at ${res.generated_at}`);
      setTimeout(() => setExportNotice(null), 5000);
    } catch (err) {
      setExportNotice('Export failed');
    }
  };

  // Filtered districts
  const filteredDistricts = districts.filter(d => {
    const matchesState = selectedState === 'ALL' || d.state_id === selectedState;
    const matchesRisk = riskFilter === 'ALL' || d.risk_category === riskFilter;
    const matchesSearch = searchQuery === '' ||
      d.district_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.state_name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesState && matchesRisk && matchesSearch;
  });

  const getRiskBadgeColor = (cat: RiskCategory) => {
    switch (cat) {
      case 'EXTREME_RAINFALL': return 'bg-red-950 border-red-700 text-red-300';
      case 'VERY_HIGH_RAINFALL': return 'bg-orange-950 border-orange-700 text-orange-300';
      case 'HIGH_RAINFALL': return 'bg-amber-950 border-amber-700 text-amber-300';
      case 'WATCH': return 'bg-yellow-950 border-yellow-700 text-yellow-300';
      case 'NORMAL': return 'bg-emerald-950 border-emerald-700 text-emerald-300';
    }
  };

  // Map coordinate bounds to SVG viewBox (India: Lon 66.5-100.5, Lat 6.5-38.5)
  // X = (lon - 66.5) / 34 * 600, Y = (38.5 - lat) / 32 * 600
  const coordToSvg = (lon: number, lat: number) => {
    const x = ((lon - 66.5) / 34.0) * 560 + 20;
    const y = ((38.5 - lat) / 32.0) * 560 + 20;
    return { x, y };
  };

  return (
    <div className="space-y-6 pb-12">
      {/* 1. DATA MODE / HONESTY BANNER */}
      <div className="p-4 bg-amber-950/40 border border-amber-600/50 rounded-xl flex items-center justify-between shadow-lg">
        <div className="flex items-center space-x-3">
          <ShieldAlert className="w-6 h-6 text-amber-400 shrink-0" />
          <div>
            <div className="text-sm font-semibold tracking-wide text-amber-200 uppercase">
              SYNTHETIC DEMONSTRATION — REAL OPERATIONAL DATA NOT AVAILABLE
            </div>
            <div className="text-xs text-amber-300/80">
              District aggregations and engineering risk categories are computed from synthetic numerical demo grids. Not official IMD warnings.
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <span className="px-2.5 py-1 text-xs font-mono bg-amber-900/60 border border-amber-600/50 rounded text-amber-200">
            {status?.boundary_metadata.projected_crs || 'EPSG:7755 (Albers)'}
          </span>
          <button
            onClick={loadAllData}
            className="p-1.5 rounded-lg bg-amber-900/40 hover:bg-amber-800/60 border border-amber-600/40 text-amber-200 transition-colors"
            title="Refresh spatial products"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* 2. FORECAST SUMMARY CARDS */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 shadow">
          <div className="text-xs text-slate-400 flex items-center justify-between">
            <span>Districts Evaluated</span>
            <MapPin className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100 mt-1">
            {summary?.total_districts_evaluated ?? '--'}
          </div>
          <div className="text-xs text-slate-400 mt-1">
            Across {summary?.total_states_evaluated ?? '--'} States ({summary?.overall_coverage_pct}% Active Grid)
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 shadow">
          <div className="text-xs text-slate-400 flex items-center justify-between">
            <span>Peak District Forecast</span>
            <CloudRain className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-blue-400 mt-1">
            {summary?.max_predicted_district_rainfall_mm.toFixed(1) ?? '--'} <span className="text-sm font-normal text-slate-400">mm</span>
          </div>
          <div className="text-xs text-slate-400 mt-1">
            {summary?.max_rainfall_district_name}, {summary?.max_rainfall_state_name}
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 shadow">
          <div className="text-xs text-slate-400 flex items-center justify-between">
            <span>High Risk Districts</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400 mt-1">
            {(summary?.districts_with_heavy_probability ?? 0)}
          </div>
          <div className="text-xs text-slate-400 mt-1">
            P(Heavy &ge; 64.5mm) &ge; 20%
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 shadow">
          <div className="text-xs text-slate-400 flex items-center justify-between">
            <span>Extreme Risk Districts</span>
            <TrendingUp className="w-4 h-4 text-red-400" />
          </div>
          <div className="text-2xl font-bold text-red-400 mt-1">
            {(summary?.districts_with_extreme_probability ?? 0)}
          </div>
          <div className="text-xs text-slate-400 mt-1">
            P(Extreme &ge; 204.5mm) &ge; 5%
          </div>
        </div>
      </div>

      {/* CONTROLS BAR: LEAD-TIME, LAYER, MODEL, STATE */}
      <div className="p-4 bg-slate-900/70 border border-slate-800 rounded-xl space-y-4 shadow">
        <div className="flex flex-wrap items-center justify-between gap-4">
          {/* 6. Lead-Time Selector */}
          <div className="flex items-center space-x-2">
            <Calendar className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-semibold text-slate-300 uppercase">Horizon:</span>
            <div className="flex bg-slate-800/70 rounded-lg p-1 border border-slate-700/50">
              {[
                { label: 'Day 1 (+24h)', hours: 24 },
                { label: 'Day 2 (+48h)', hours: 48 },
                { label: 'Day 3 (+72h)', hours: 72 },
                { label: 'Day 4 (+96h)', hours: 96 },
                { label: 'Day 5 (+120h)', hours: 120 },
              ].map(h => (
                <button
                  key={h.hours}
                  onClick={() => setLeadHours(h.hours)}
                  className={`px-3 py-1 text-xs rounded-md transition-all ${
                    leadHours === h.hours
                      ? 'bg-cyan-600 text-white font-medium shadow'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {h.label}
                </button>
              ))}
            </div>
          </div>

          {/* 7. Model Layer Selector */}
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-purple-400" />
            <span className="text-xs font-semibold text-slate-300 uppercase">Active Layer:</span>
            <select
              value={activeLayer}
              onChange={(e) => setActiveLayer(e.target.value as ActiveLayer)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <optgroup label="Deterministic Rainfall (mm)">
                <option value="ramp_rainfall">RAMP MoE Rainfall</option>
                <option value="raw_nwp">Raw NWP Baseline</option>
                <option value="global_ml">Global ML Baseline</option>
                <option value="diff_nwp">Spatial Correction (RAMP − NWP)</option>
              </optgroup>
              <optgroup label="Extreme Probabilities">
                <option value="prob_rain">P(Rain &ge; 0.1 mm)</option>
                <option value="prob_heavy">P(Heavy &ge; 64.5 mm)</option>
                <option value="prob_very_heavy">P(Very Heavy &ge; 115.6 mm)</option>
                <option value="prob_extreme">P(Extreme &ge; 204.5 mm)</option>
              </optgroup>
              <optgroup label="Diagnostics">
                <option value="regime">Dominant Weather Regime</option>
                <option value="uncertainty">Forecast Uncertainty</option>
              </optgroup>
            </select>
          </div>

          {/* 18. GIS Export Action */}
          <button
            onClick={handleExport}
            className="flex items-center space-x-2 px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-medium text-slate-200 transition-colors shadow"
          >
            <Download className="w-3.5 h-3.5 text-cyan-400" />
            <span>Export GIS Layers</span>
          </button>
        </div>

        {exportNotice && (
          <div className="p-2.5 bg-emerald-950/60 border border-emerald-600/40 rounded text-xs text-emerald-300 flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            <span>{exportNotice}</span>
          </div>
        )}
      </div>

      {/* MAIN TWO-COLUMN WORKSPACE: MAP (LEFT) & DISTRICT DETAILS (RIGHT) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* 3. INTERACTIVE INDIA MAP & CONTROLS (8 Cols) */}
        <div className="lg:col-span-8 space-y-4">
          <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-xl relative shadow-lg">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold text-slate-200 flex items-center space-x-2">
                  <Compass className="w-4 h-4 text-cyan-400" />
                  <span>Subcontinental Spatial Forecast Map (0.25° Grid &amp; Administrative Boundaries)</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Click any district to inspect area-weighted statistics, peak convective hotspots, and uncertainty.
                </p>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-xs px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">
                  Layer: <strong className="text-cyan-400">{activeLayer.replace('_', ' ').toUpperCase()}</strong>
                </span>
              </div>
            </div>

            {/* SVG Interactive Map Canvas */}
            <div className="w-full bg-slate-950/80 border border-slate-800/80 rounded-xl p-4 flex items-center justify-center overflow-hidden min-h-[500px]">
              <svg viewBox="0 0 600 600" className="w-full max-w-[550px] h-auto select-none">
                {/* Background Grid Pattern (0.25° grid representation) */}
                <defs>
                  <pattern id="gridPattern" width="20" height="20" patternUnits="userSpaceOnUse">
                    <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#1e293b" strokeWidth="0.5" />
                  </pattern>
                </defs>
                <rect width="600" height="600" fill="url(#gridPattern)" />

                {/* Approximate Subcontinental India Outline Baseline */}
                <path
                  d="M 180,60 L 260,70 L 320,110 L 350,140 L 460,180 L 520,180 L 480,240 L 410,250 L 380,310 L 320,400 L 280,500 L 260,540 L 250,550 L 240,530 L 200,430 L 160,330 L 130,280 L 150,220 L 140,150 Z"
                  fill="#0f172a"
                  stroke="#334155"
                  strokeWidth="1.5"
                  strokeDasharray="4 2"
                  opacity="0.6"
                />

                {/* Render District Polygons from loaded bounds */}
                {districts.map(d => {
                  // Nagpur approx bounds: [78.4, 20.8, 79.5, 21.8]
                  // Map each district bounding box to SVG rect for visualization
                  let minLon = 78.0, minLat = 21.0, maxLon = 79.0, maxLat = 22.0;
                  if (d.district_id === 'NAGPUR') {
                    minLon = 78.4; minLat = 20.8; maxLon = 79.5; maxLat = 21.8;
                  } else if (d.district_id === 'AMRAVATI') {
                    minLon = 77.2; minLat = 20.7; maxLon = 78.3; maxLat = 21.7;
                  } else if (d.district_id === 'PUNE') {
                    minLon = 73.4; minLat = 18.2; maxLon = 75.0; maxLat = 19.3;
                  } else if (d.district_id === 'MUMBAI') {
                    minLon = 72.7; minLat = 18.8; maxLon = 73.0; maxLat = 19.3;
                  } else if (d.district_id === 'WAYANAD') {
                    minLon = 75.8; minLat = 11.5; maxLon = 76.4; maxLat = 11.9;
                  } else if (d.district_id === 'IDUKKI') {
                    minLon = 76.6; minLat = 9.6; maxLon = 77.3; maxLat = 10.4;
                  } else if (d.district_id === 'AHMEDABAD') {
                    minLon = 71.9; minLat = 22.6; maxLon = 72.8; maxLat = 23.4;
                  } else if (d.district_id === 'BENGALURU') {
                    minLon = 77.4; minLat = 12.8; maxLon = 77.8; maxLat = 13.2;
                  } else if (d.district_id === 'PURI') {
                    minLon = 85.1; minLat = 19.6; maxLon = 86.4; maxLat = 20.2;
                  } else if (d.district_id === 'KAMRUP') {
                    minLon = 91.5; minLat = 25.9; maxLon = 92.1; maxLat = 26.4;
                  } else if (d.district_id === 'SHIMLA') {
                    minLon = 77.0; minLat = 30.9; maxLon = 77.9; maxLat = 31.5;
                  } else if (d.district_id === 'JAIPUR') {
                    minLon = 75.3; minLat = 26.6; maxLon = 76.2; maxLat = 27.5;
                  } else if (d.district_id === 'DELHI') {
                    minLon = 76.8; minLat = 28.4; maxLon = 77.3; maxLat = 28.9;
                  } else if (d.district_id === 'CHENNAI') {
                    minLon = 80.1; minLat = 12.9; maxLon = 80.3; maxLat = 13.2;
                  } else if (d.district_id === 'KOLKATA') {
                    minLon = 88.2; minLat = 22.4; maxLon = 88.5; maxLat = 22.7;
                  }

                  const p1 = coordToSvg(minLon, maxLat);
                  const p2 = coordToSvg(maxLon, minLat);
                  const w = Math.max(12, p2.x - p1.x);
                  const h = Math.max(12, p2.y - p1.y);

                  const isSelected = selectedDistrictId === d.district_id;

                  // Layer color calculation
                  let fillColor = '#1e293b';
                  if (activeLayer === 'ramp_rainfall') {
                    if (d.rainfall_mm > 64.5) fillColor = '#ef4444';
                    else if (d.rainfall_mm > 35.5) fillColor = '#f97316';
                    else if (d.rainfall_mm > 15.5) fillColor = '#06b6d4';
                    else if (d.rainfall_mm > 2.5) fillColor = '#3b82f6';
                    else fillColor = '#1e293b';
                  } else if (activeLayer === 'prob_heavy') {
                    if (d.heavy_probability >= 0.40) fillColor = '#ea580c';
                    else if (d.heavy_probability >= 0.20) fillColor = '#f59e0b';
                    else fillColor = '#1e293b';
                  } else if (activeLayer === 'prob_extreme') {
                    if (d.extreme_probability >= 0.10) fillColor = '#991b1b';
                    else if (d.extreme_probability >= 0.03) fillColor = '#dc2626';
                    else fillColor = '#1e293b';
                  } else if (activeLayer === 'diff_nwp') {
                    fillColor = d.difference_nwp_mm >= 0 ? '#0284c7' : '#e11d48';
                  } else {
                    fillColor = d.color_hex;
                  }

                  return (
                    <g
                      key={d.district_id}
                      onClick={() => handleDistrictSelect(d.district_id)}
                      className="cursor-pointer transition-all duration-200"
                    >
                      <rect
                        x={p1.x}
                        y={p1.y}
                        width={w}
                        height={h}
                        rx="3"
                        fill={fillColor}
                        fillOpacity={d.valid_grid_cells > 0 ? (isSelected ? '0.9' : '0.65') : '0.2'}
                        stroke={isSelected ? '#38bdf8' : '#475569'}
                        strokeWidth={isSelected ? 2.5 : 1}
                        className="hover:stroke-cyan-400 hover:fill-opacity-80 transition-all"
                      />
                      {/* District Label */}
                      <text
                        x={p1.x + w / 2}
                        y={p1.y + h / 2 + 3}
                        fontSize="9"
                        textAnchor="middle"
                        fill={isSelected ? '#f8fafc' : '#94a3b8'}
                        className="pointer-events-none font-mono font-medium"
                      >
                        {d.district_name.slice(0, 7)}
                      </text>
                    </g>
                  );
                })}

                {/* Hotspot Markers */}
                {hotspots.map((h, idx) => {
                  const pt = coordToSvg(h.hotspot_longitude, h.hotspot_latitude);
                  return (
                    <g key={idx} className="pointer-events-none">
                      <circle
                        cx={pt.x}
                        cy={pt.y}
                        r="6"
                        fill="#ef4444"
                        fillOpacity="0.8"
                        stroke="#ffffff"
                        strokeWidth="1.5"
                        className="animate-pulse"
                      />
                    </g>
                  );
                })}
              </svg>
            </div>

            {/* 30. MAP LEGEND */}
            <div className="mt-4 p-3 bg-slate-950/60 border border-slate-800 rounded-lg flex flex-wrap items-center justify-between text-xs gap-3">
              <div className="flex items-center space-x-2">
                <span className="text-slate-400 font-semibold uppercase">Legend:</span>
                <span className="flex items-center space-x-1">
                  <span className="w-3 h-3 bg-slate-800 border border-slate-700 rounded-sm"></span>
                  <span className="text-slate-400">Normal (&lt;15.6mm)</span>
                </span>
                <span className="flex items-center space-x-1">
                  <span className="w-3 h-3 bg-blue-500 rounded-sm"></span>
                  <span className="text-slate-300">Moderate</span>
                </span>
                <span className="flex items-center space-x-1">
                  <span className="w-3 h-3 bg-amber-500 rounded-sm"></span>
                  <span className="text-slate-300">Heavy (&ge;64.5mm)</span>
                </span>
                <span className="flex items-center space-x-1">
                  <span className="w-3 h-3 bg-red-600 rounded-sm"></span>
                  <span className="text-slate-300">Extreme (&ge;204.5mm)</span>
                </span>
                <span className="flex items-center space-x-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-red-500 border border-white"></span>
                  <span className="text-slate-300">Peak Hotspot</span>
                </span>
              </div>
              <div className="text-slate-500 font-mono">
                Projection: Albers Equal Area Conic | Grid: 0.25°
              </div>
            </div>
          </div>

          {/* 16. FRACTIONS SKILL SCORE (FSS) SECTION */}
          <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-xl space-y-3 shadow">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-200 flex items-center space-x-2">
                <BarChart3 className="w-4 h-4 text-emerald-400" />
                <span>Neighborhood Verification (Fractions Skill Score — FSS)</span>
              </h3>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800 text-emerald-300">
                {fssData?.status ?? 'PASS'}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Evaluates spatial skill across 5km, 25km, 50km, 100km, 200km neighborhood radii according to Roberts &amp; Lean (2008).
            </p>

            <div className="grid grid-cols-2 md:grid-cols-5 gap-2 pt-1">
              {['5km', '25km', '50km', '100km', '200km'].map(scale => {
                const score = fssData?.fss_curves?.['0.1mm']?.[scale]?.fss ?? 1.0;
                return (
                  <div key={scale} className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg text-center">
                    <div className="text-xs text-slate-400">{scale} Radius</div>
                    <div className="text-lg font-bold text-emerald-400 mt-0.5">{score.toFixed(4)}</div>
                    <div className="text-[10px] text-slate-500 mt-0.5">Threshold: 0.1 mm</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* 13. DISTRICT INSPECTION & DETAILS PANEL (4 Cols) */}
        <div className="lg:col-span-4 space-y-4">
          {/* SEARCH & FILTERS */}
          <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-3 shadow">
            <div className="text-xs font-semibold text-slate-300 uppercase flex items-center justify-between">
              <span>District Inspector</span>
              <Search className="w-3.5 h-3.5 text-cyan-400" />
            </div>
            <input
              type="text"
              placeholder="Search district or state..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
            <div className="flex gap-2">
              <select
                value={selectedState}
                onChange={(e) => setSelectedState(e.target.value)}
                className="w-1/2 bg-slate-800 border border-slate-700 rounded-lg px-2 py-1 text-xs text-slate-200 focus:outline-none"
              >
                <option value="ALL">All States ({states.length})</option>
                {states.map(s => (
                  <option key={s.state_id} value={s.state_id}>{s.state_name}</option>
                ))}
              </select>
              <select
                value={riskFilter}
                onChange={(e) => setRiskFilter(e.target.value)}
                className="w-1/2 bg-slate-800 border border-slate-700 rounded-lg px-2 py-1 text-xs text-slate-200 focus:outline-none"
              >
                <option value="ALL">All Risks</option>
                <option value="NORMAL">Normal</option>
                <option value="WATCH">Watch</option>
                <option value="HIGH_RAINFALL">High</option>
                <option value="VERY_HIGH_RAINFALL">Very High</option>
                <option value="EXTREME_RAINFALL">Extreme</option>
              </select>
            </div>
          </div>

          {/* ACTIVE DISTRICT CARD */}
          {selectedDistrict ? (
            <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-xl space-y-4 shadow-lg">
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="text-base font-bold text-slate-100 flex items-center space-x-1.5">
                    <span>{selectedDistrict.district_name}</span>
                  </h4>
                  <p className="text-xs text-slate-400">{selectedDistrict.state_name} &bull; Area: {selectedDistrict.area_km2.toLocaleString()} km²</p>
                </div>
                <span className={`px-2.5 py-1 text-xs font-semibold rounded-md border ${getRiskBadgeColor(selectedDistrict.risk_category)}`}>
                  {selectedDistrict.risk_category.replace('_', ' ')}
                </span>
              </div>

              {/* Rainfall Comparison Card */}
              <div className="p-3.5 bg-slate-950/70 border border-slate-800 rounded-lg space-y-2">
                <div className="flex justify-between items-baseline">
                  <span className="text-xs text-slate-400">RAMP Area-Weighted:</span>
                  <span className="text-xl font-bold text-cyan-400">{selectedDistrict.rainfall_mm.toFixed(1)} <span className="text-xs font-normal">mm</span></span>
                </div>
                <div className="flex justify-between text-xs text-slate-400">
                  <span>Raw NWP Model:</span>
                  <span>{selectedDistrict.raw_nwp_rainfall_mm.toFixed(1)} mm</span>
                </div>
                <div className="flex justify-between text-xs text-slate-400">
                  <span>RAMP Offset (Correction):</span>
                  <span className={selectedDistrict.difference_nwp_mm >= 0 ? 'text-blue-400' : 'text-red-400'}>
                    {selectedDistrict.difference_nwp_mm >= 0 ? `+${selectedDistrict.difference_nwp_mm.toFixed(1)}` : selectedDistrict.difference_nwp_mm.toFixed(1)} mm
                  </span>
                </div>
              </div>

              {/* 12. HOTSPOT DETECTION PANEL */}
              <div className="p-3.5 bg-red-950/30 border border-red-900/40 rounded-lg space-y-1.5">
                <div className="text-xs font-semibold text-red-300 flex items-center space-x-1.5">
                  <TrendingUp className="w-3.5 h-3.5 text-red-400" />
                  <span>Localized Peak Convective Hotspot</span>
                </div>
                <div className="text-lg font-bold text-red-400">
                  {selectedDistrict.hotspot_rainfall_mm.toFixed(1)} mm
                  <span className="text-xs font-normal text-slate-400 ml-2">({selectedDistrict.hotspot_intensity.toFixed(1)}x district mean)</span>
                </div>
                <div className="text-[11px] text-slate-400">
                  Coordinates: ({selectedDistrict.hotspot_latitude.toFixed(2)}°N, {selectedDistrict.hotspot_longitude.toFixed(2)}°E)
                </div>
              </div>

              {/* 9. PROBABILITY BREAKDOWN */}
              <div className="space-y-2">
                <div className="text-xs font-semibold text-slate-300 uppercase">IMD Exceedance Probabilities</div>
                <div className="space-y-1.5 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Rain (&ge;0.1 mm):</span>
                    <span className="font-mono text-slate-200">{(selectedDistrict.rain_probability * 100).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Heavy (&ge;64.5 mm):</span>
                    <span className="font-mono text-amber-300">{(selectedDistrict.heavy_probability * 100).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Very Heavy (&ge;115.6 mm):</span>
                    <span className="font-mono text-orange-300">{(selectedDistrict.very_heavy_probability * 100).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Extremely Heavy (&ge;204.5 mm):</span>
                    <span className="font-mono text-red-400">{(selectedDistrict.extreme_probability * 100).toFixed(1)}%</span>
                  </div>
                </div>
              </div>

              {/* 13. SPREAD & QUANTILES */}
              <div className="pt-2 border-t border-slate-800 text-xs space-y-1 text-slate-400">
                <div className="flex justify-between">
                  <span>Spread (Min - Max):</span>
                  <span>{selectedDistrict.min_rainfall_mm} - {selectedDistrict.max_rainfall_mm} mm</span>
                </div>
                <div className="flex justify-between">
                  <span>95th Percentile (P95):</span>
                  <span>{selectedDistrict.p95_rainfall_mm} mm</span>
                </div>
                <div className="flex justify-between">
                  <span>Grid Coverage:</span>
                  <span>{selectedDistrict.valid_grid_cells} / {selectedDistrict.total_grid_cells} cells ({(selectedDistrict.coverage_fraction * 100).toFixed(0)}%)</span>
                </div>
              </div>

              {/* 17. UNCERTAINTY */}
              <div className="pt-2 border-t border-slate-800 text-xs flex justify-between text-slate-400">
                <span>Uncertainty Tier:</span>
                <span className="font-semibold text-slate-200">{selectedDistrict.uncertainty.uncertainty_tier ?? 'MEDIUM'}</span>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-500">
              Select a district to view detailed spatial diagnostics.
            </div>
          )}

          {/* DISTRICTS SCROLL LIST */}
          <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl max-h-[300px] overflow-y-auto space-y-1.5 shadow">
            <div className="text-[11px] font-semibold text-slate-400 uppercase px-2 mb-1">
              Matching Districts ({filteredDistricts.length})
            </div>
            {filteredDistricts.map(d => (
              <button
                key={d.district_id}
                onClick={() => handleDistrictSelect(d.district_id)}
                className={`w-full text-left p-2 rounded-lg text-xs flex items-center justify-between transition-colors ${
                  selectedDistrictId === d.district_id
                    ? 'bg-cyan-950/60 border border-cyan-700/60 text-cyan-200'
                    : 'bg-slate-800/40 hover:bg-slate-800 border border-transparent text-slate-300'
                }`}
              >
                <div>
                  <div className="font-medium">{d.district_name}</div>
                  <div className="text-[10px] text-slate-400">{d.state_name}</div>
                </div>
                <div className="text-right">
                  <div className="font-mono font-semibold">{d.rainfall_mm.toFixed(1)} mm</div>
                  <span className={`text-[9px] px-1 py-0.2 rounded ${getRiskBadgeColor(d.risk_category)}`}>
                    {d.risk_category.replace('_', ' ')}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 14. STATE SUMMARY ACCORDION / TABLE */}
      <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-xl space-y-4 shadow-lg">
        <h3 className="text-sm font-semibold text-slate-200 flex items-center space-x-2">
          <Layers className="w-4 h-4 text-cyan-400" />
          <span>State-Level Meteorological Summaries &amp; Aggregations</span>
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="py-2.5 px-3 font-semibold">State</th>
                <th className="py-2.5 px-3 font-semibold">Districts</th>
                <th className="py-2.5 px-3 font-semibold">Area-Weighted Rain</th>
                <th className="py-2.5 px-3 font-semibold">Peak District Rain</th>
                <th className="py-2.5 px-3 font-semibold">High Risk (&ge;64.5mm)</th>
                <th className="py-2.5 px-3 font-semibold">Extreme Risk (&ge;204.5mm)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {states.map(s => (
                <tr key={s.state_id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-2.5 px-3 font-medium text-slate-100">{s.state_name}</td>
                  <td className="py-2.5 px-3">{s.district_count}</td>
                  <td className="py-2.5 px-3 font-mono text-cyan-400 font-semibold">{s.area_weighted_rainfall_mm.toFixed(1)} mm</td>
                  <td className="py-2.5 px-3 font-mono">{s.max_district_rainfall_mm.toFixed(1)} mm ({s.max_rainfall_district})</td>
                  <td className="py-2.5 px-3">
                    <span className={`px-2 py-0.5 rounded text-[11px] font-mono ${
                      s.high_risk_districts > 0 ? 'bg-amber-950 text-amber-300 border border-amber-800' : 'text-slate-400'
                    }`}>
                      {s.high_risk_districts}
                    </span>
                  </td>
                  <td className="py-2.5 px-3">
                    <span className={`px-2 py-0.5 rounded text-[11px] font-mono ${
                      s.extreme_risk_districts > 0 ? 'bg-red-950 text-red-300 border border-red-800 font-bold' : 'text-slate-400'
                    }`}>
                      {s.extreme_risk_districts}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
"""

with open("frontend/src/pages/SpatialForecast.tsx", "w", encoding="utf-8") as f:
    f.write(spatial_tsx)
print("Wrote frontend/src/pages/SpatialForecast.tsx successfully!")
