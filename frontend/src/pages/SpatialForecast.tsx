/**
 * Phase 21 – RAMP Spatial Forecast Module
 * SIH26080 | MoES / NCMRWF
 *
 * Real Leaflet map (react-leaflet@4) with:
 *  – OSM basemap tiles
 *  – GeoJSON administrative boundaries (India, States, Districts) from /api/spatial/geojson
 *  – 0.25° grid CircleMarkers from district products
 *  – Rainfall color scale legend
 *  – Layer / Horizon / State / Risk filters
 *  – District inspector panel
 *  – State-level aggregation table
 *  – Verification section with honest PENDING disclaimer
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  MapPin, Layers, AlertTriangle, Download,
  RefreshCw, ShieldAlert, Search, CheckCircle2, BarChart3,
  Globe, Compass, TrendingUp, Lock,
} from 'lucide-react';
import {
  MapContainer,
  TileLayer,
  GeoJSON,
  CircleMarker,
  Tooltip,
  Popup,
  useMap,
} from 'react-leaflet';
import type { GeoJSON as GeoJSONType } from 'geojson';
import 'leaflet/dist/leaflet.css';
import {
  fetchSpatialStatus,
  fetchSpatialDistricts,
  fetchSpatialStates,
  fetchNationalSummary,
  fetchSpatialGeoJSON,
  fetchSpatialVerification,
  fetchSpatialExport,
} from '../api/client';
import type {
  SpatialStatusResponse,
  DistrictForecastProductItem,
  StateForecastProductItem,
  NationalSummaryResponse,
} from '../types/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
type ActiveLayer =
  | 'ramp_rainfall' | 'raw_nwp' | 'diff_nwp'
  | 'prob_rain' | 'prob_heavy' | 'prob_very_heavy' | 'prob_extreme'
  | 'regime' | 'uncertainty';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const INDIA_CENTER: [number, number] = [22.5, 82.0];
const INDIA_ZOOM = 5;

const RAIN_SCALE = [
  { label: 'Trace (<0.1)', color: '#1e293b' },
  { label: '0.1–15 mm',   color: '#0ea5e9' },
  { label: '15–64.5 mm',  color: '#22c55e' },
  { label: '64.5–115 mm (Heavy)', color: '#eab308' },
  { label: '115–204.5 mm (Very Heavy)', color: '#f97316' },
  { label: '≥204.5 mm (Extreme)', color: '#ef4444' },
];

function rainfallColor(mm: number): string {
  if (mm < 0.1)   return '#1e293b';
  if (mm < 15)    return '#0ea5e9';
  if (mm < 64.5)  return '#22c55e';
  if (mm < 115.6) return '#eab308';
  if (mm < 204.5) return '#f97316';
  return '#ef4444';
}

function probColor(p: number): string {
  if (p < 0.05)  return '#1e293b';
  if (p < 0.15)  return '#0ea5e9';
  if (p < 0.35)  return '#22c55e';
  if (p < 0.55)  return '#eab308';
  if (p < 0.75)  return '#f97316';
  return '#ef4444';
}

function getDistrictColor(d: DistrictForecastProductItem, layer: ActiveLayer): string {
  switch (layer) {
    case 'ramp_rainfall':   return rainfallColor(d.rainfall_mm ?? 0);
    case 'raw_nwp':         return rainfallColor(d.raw_nwp_rainfall_mm ?? 0);
    case 'diff_nwp':        return rainfallColor(Math.abs(d.difference_nwp_mm ?? 0));
    case 'prob_rain':       return probColor(d.rain_probability ?? 0);
    case 'prob_heavy':      return probColor(d.heavy_probability ?? 0);
    case 'prob_very_heavy': return probColor(d.very_heavy_probability ?? 0);
    case 'prob_extreme':    return probColor(d.extreme_probability ?? 0);
    case 'regime':          return d.color_hex ?? '#475569';
    case 'uncertainty':     return rainfallColor(((d.uncertainty?.composite_uncertainty_score ?? (typeof (d as any).uncertainty === 'number' ? (d as any).uncertainty : 0)) * 100));
    default:                return rainfallColor(d.rainfall_mm ?? 0);
  }
}

const RISK_BADGE: Record<string, string> = {
  EXTREME_RAINFALL:  'bg-red-950 border-red-700 text-red-300',
  VERY_HIGH_RAINFALL:'bg-orange-950 border-orange-600 text-orange-300',
  HIGH_RAINFALL:     'bg-amber-950 border-amber-600 text-amber-300',
  WATCH:             'bg-yellow-950 border-yellow-600 text-yellow-300',
  NORMAL:            'bg-emerald-950 border-emerald-700 text-emerald-300',
};

// ---------------------------------------------------------------------------
// Leaflet Map Bounds Controller
// ---------------------------------------------------------------------------
function MapBoundsController({ district }: { district: DistrictForecastProductItem | null }) {
  const map = useMap();
  useEffect(() => {
    if (!district) return;
    const lat = district.hotspot_latitude ?? 22.5;
    const lon = district.hotspot_longitude ?? 82.0;
    map.setView([lat, lon], 8, { animate: true });
  }, [district, map]);
  return null;
}

// ---------------------------------------------------------------------------
// Rainfall Legend
// ---------------------------------------------------------------------------
const RainfallLegend: React.FC = () => (
  <div className="bg-slate-900/95 backdrop-blur-sm border border-slate-700 rounded-xl p-3 space-y-1.5 shadow-2xl min-w-[180px]">
    <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-2">
      Rainfall Scale
    </div>
    {RAIN_SCALE.map(({ label, color }) => (
      <div key={label} className="flex items-center gap-2 text-[11px] text-slate-300">
        <span className="w-3.5 h-3.5 rounded-sm shrink-0 border border-slate-700" style={{ backgroundColor: color }} />
        {label}
      </div>
    ))}
  </div>
);

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------
export const SpatialForecastPage: React.FC = () => {
  const [status, setStatus]     = useState<SpatialStatusResponse | null>(null);
  const [districts, setDistricts] = useState<DistrictForecastProductItem[]>([]);
  const [states, setStates]     = useState<StateForecastProductItem[]>([]);
  const [summary, setSummary]   = useState<NationalSummaryResponse | null>(null);
  const [geoJsonDistricts, setGeoJsonDistricts] = useState<GeoJSONType | null>(null);
  const [geoJsonStates, setGeoJsonStates]       = useState<GeoJSONType | null>(null);
  const [geoJsonIndia, setGeoJsonIndia]         = useState<GeoJSONType | null>(null);
  const [verification, setVerification]         = useState<Record<string, any> | null>(null);

  const [leadHours, setLeadHours]       = useState(24);
  const [activeLayer, setActiveLayer]   = useState<ActiveLayer>('ramp_rainfall');
  const [selectedState, setSelectedState] = useState('ALL');
  const [selectedDistrict, setSelectedDistrict] = useState<DistrictForecastProductItem | null>(null);
  const [riskFilter, setRiskFilter]     = useState('ALL');
  const [searchQuery, setSearchQuery]   = useState('');
  const [loading, setLoading]           = useState(true);
  const [exportNotice, setExportNotice] = useState<string | null>(null);
  const [showLegend, setShowLegend]     = useState(true);

  const mapRef = useRef<any>(null);

  const loadAll = useCallback(async (lead: number) => {
    setLoading(true);
    try {
      const [st, distRes, stRes, sumRes, geoD, geoS, geoI, ver] = await Promise.all([
        fetchSpatialStatus(),
        fetchSpatialDistricts(lead),
        fetchSpatialStates(lead),
        fetchNationalSummary(lead),
        fetchSpatialGeoJSON('districts', lead),
        fetchSpatialGeoJSON('states', lead),
        fetchSpatialGeoJSON('india', lead),
        fetchSpatialVerification(lead),
      ]);
      setStatus(st);
      setDistricts(distRes.districts || []);
      setStates(stRes.states || []);
      setSummary(sumRes);
      setGeoJsonDistricts(geoD as GeoJSONType);
      setGeoJsonStates(geoS as GeoJSONType);
      setGeoJsonIndia(geoI as GeoJSONType);
      setVerification(ver);
      if ((distRes.districts || []).length > 0 && !selectedDistrict) {
        setSelectedDistrict(distRes.districts[0]);
      }
    } catch (err) {
      console.error('Spatial forecast load failed:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedDistrict]);

  useEffect(() => { loadAll(leadHours); }, [leadHours]);

  const handleExport = async () => {
    try {
      const res = await fetchSpatialExport(leadHours);
      setExportNotice(`Export ready at ${res.generated_at}`);
      setTimeout(() => setExportNotice(null), 5000);
    } catch {
      setExportNotice('Export failed');
    }
  };

  // Filtered districts
  const filteredDistricts = districts.filter(d => {
    const matchState  = selectedState === 'ALL' || d.state_id === selectedState;
    const matchRisk   = riskFilter === 'ALL' || d.risk_category === riskFilter;
    const matchSearch = searchQuery === '' ||
      d.district_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.state_name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchState && matchRisk && matchSearch;
  });

  // State list for filter
  const stateOptions = Array.from(new Set(districts.map(d => d.state_id)))
    .map(sId => ({ id: sId, name: districts.find(d => d.state_id === sId)?.state_name || sId }));

  const highRisk = filteredDistricts.filter(d =>
    d.risk_category === 'HIGH_RAINFALL' || d.risk_category === 'VERY_HIGH_RAINFALL'
  ).length;
  const extremeRisk = filteredDistricts.filter(d => d.risk_category === 'EXTREME_RAINFALL').length;

  // GeoJSON styling for district layer
  const districtStyle = (feature: any) => {
    const props = feature?.properties || {};
    const d = districts.find(d => d.district_id === props.district_id) || (props as any);
    const color = d ? getDistrictColor(d, activeLayer) : '#1e293b';
    return {
      fillColor: color,
      fillOpacity: 0.65,
      color: '#334155',
      weight: 1,
    };
  };

  const stateStyle = () => ({
    fillColor: 'transparent',
    fillOpacity: 0,
    color: '#475569',
    weight: 1.5,
    dashArray: '4 3',
  });

  const indiaStyle = () => ({
    fillColor: 'transparent',
    fillOpacity: 0,
    color: '#64748b',
    weight: 2,
  });

  const onEachDistrict = (feature: any, layer: any) => {
    const props = feature?.properties || {};
    const d = districts.find(d => d.district_id === props.district_id) || (props as any);
    if (!d || !d.district_id) return;
    layer.on('click', () => {
      const full = districts.find(item => item.district_id === d.district_id) || d;
      setSelectedDistrict(full);
    });
    const distName = d.district_name || props.district_name || 'District';
    const stateName = d.state_name || props.state_name || '';
    const rainVal = d.rainfall_mm !== undefined ? d.rainfall_mm.toFixed(1) : (props.rainfall_mm !== undefined ? Number(props.rainfall_mm).toFixed(1) : '—');
    const riskCat = d.risk_category || props.risk_category || 'NORMAL';
    layer.bindTooltip(
      `<div style="background:#0f172a;border:1px solid #334155;border-radius:8px;padding:8px 12px;font-size:12px;color:#e2e8f0">
        <strong>${distName}</strong><br/>
        <span style="color:#94a3b8">${stateName}</span><br/>
        RAMP: <strong>${rainVal} mm</strong> &nbsp;
        Risk: <span style="color:${RISK_BADGE[riskCat] ? '#fbbf24' : '#34d399'}">${riskCat.replace(/_/g, ' ')}</span>
      </div>`,
      { className: 'ramp-leaflet-tooltip', sticky: true }
    );
  };

  const LEAD_OPTIONS = [24, 48, 72, 96, 120];
  const isSynthetic = status?.data_mode === 'SYNTHETIC_DEMO' || !status?.data_mode;

  return (
    <div className="space-y-6 pb-12">

      {/* 0. DATA MODE BANNER */}
      <div className={`flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 rounded-xl border
        ${isSynthetic
          ? 'bg-amber-950/30 border-amber-600/40'
          : 'bg-emerald-950/30 border-emerald-600/40'}`}>
        <div className="flex items-center gap-3">
          <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0" />
          <div>
            <div className="text-sm font-semibold text-amber-200 uppercase tracking-wide">
              {isSynthetic ? 'SYNTHETIC DEMONSTRATION — REAL OPERATIONAL DATA NOT AVAILABLE' : 'REAL OPERATIONAL DATA'}
            </div>
            <div className="text-xs text-amber-300/70 mt-0.5">
              District aggregations computed from synthetic demo grids. Not official IMD warnings.
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="px-2.5 py-1 text-xs font-mono bg-amber-900/60 border border-amber-600/40 rounded text-amber-200">
            {status?.boundary_metadata?.projected_crs || 'EPSG:7755'}
          </span>
          <button
            onClick={() => loadAll(leadHours)}
            className="p-1.5 rounded-lg bg-amber-900/40 hover:bg-amber-800/60 border border-amber-600/40 text-amber-200 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* 1. KPI CARDS */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="glass-card rounded-xl p-4 space-y-1">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] uppercase tracking-widest font-semibold">Districts Evaluated</span>
            <MapPin className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100">{summary?.total_districts_evaluated ?? filteredDistricts.length}</div>
          <div className="text-[11px] text-slate-400">Across {summary?.total_states_evaluated ?? stateOptions.length} states</div>
        </div>
        <div className="glass-card rounded-xl p-4 space-y-1">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] uppercase tracking-widest font-semibold">Peak District Forecast</span>
            <TrendingUp className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100">
            {summary?.max_predicted_district_rainfall_mm != null
              ? `${summary.max_predicted_district_rainfall_mm.toFixed(1)} mm`
              : filteredDistricts.reduce((m, d) => Math.max(m, d.rainfall_mm ?? 0), 0).toFixed(1) + ' mm'}
          </div>
          <div className="text-[11px] text-slate-400">{summary?.max_rainfall_district_name || (filteredDistricts[0]?.district_name ?? '—')}</div>
        </div>
        <div className="glass-card rounded-xl p-4 space-y-1">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] uppercase tracking-widest font-semibold">High Risk Districts</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400">{highRisk}</div>
          <div className="text-[11px] text-slate-400">≥64.5 mm threshold</div>
        </div>
        <div className="glass-card rounded-xl p-4 space-y-1">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] uppercase tracking-widest font-semibold">Extreme Risk</span>
            <ShieldAlert className="w-4 h-4 text-red-400" />
          </div>
          <div className="text-2xl font-bold text-red-400">{extremeRisk}</div>
          <div className="text-[11px] text-slate-400">≥204.5 mm threshold</div>
        </div>
      </div>

      {/* 2. TOOLBAR */}
      <div className="glass-panel rounded-2xl p-4 space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          {/* Lead time */}
          <div className="flex items-center gap-2">
            <Globe className="w-4 h-4 text-slate-400 shrink-0" />
            <select
              value={leadHours}
              onChange={e => setLeadHours(Number(e.target.value))}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              {LEAD_OPTIONS.map(h => <option key={h} value={h}>Day {h / 24} (+{h}h)</option>)}
            </select>
          </div>

          {/* Layer */}
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-slate-400 shrink-0" />
            <select
              value={activeLayer}
              onChange={e => setActiveLayer(e.target.value as ActiveLayer)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <optgroup label="Deterministic Rainfall">
                <option value="ramp_rainfall">RAMP MoE Rainfall</option>
                <option value="raw_nwp">Raw NWP Baseline</option>
                <option value="diff_nwp">Spatial Correction</option>
              </optgroup>
              <optgroup label="Extreme Probabilities">
                <option value="prob_rain">P(Rain ≥0.1 mm)</option>
                <option value="prob_heavy">P(Heavy ≥64.5 mm)</option>
                <option value="prob_very_heavy">P(Very Heavy ≥115.6 mm)</option>
                <option value="prob_extreme">P(Extreme ≥204.5 mm)</option>
              </optgroup>
              <optgroup label="Diagnostics">
                <option value="regime">Dominant Regime</option>
                <option value="uncertainty">Uncertainty</option>
              </optgroup>
            </select>
          </div>

          {/* State filter */}
          <select
            value={selectedState}
            onChange={e => setSelectedState(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">All States</option>
            {stateOptions.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>

          {/* Risk filter */}
          <select
            value={riskFilter}
            onChange={e => setRiskFilter(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">All Risk Levels</option>
            <option value="EXTREME_RAINFALL">Extreme Rainfall</option>
            <option value="VERY_HIGH_RAINFALL">Very High</option>
            <option value="HIGH_RAINFALL">High</option>
            <option value="WATCH">Watch</option>
            <option value="NORMAL">Normal</option>
          </select>

          {/* Search */}
          <div className="relative flex-1 min-w-[160px]">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search district or state…"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* Legend toggle */}
          <button
            onClick={() => setShowLegend(v => !v)}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs text-slate-300 transition-colors"
          >
            {showLegend ? 'Hide Legend' : 'Show Legend'}
          </button>

          {/* Export */}
          <button
            onClick={handleExport}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs text-slate-300 transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-cyan-400" />
            Export GIS
          </button>
        </div>

        {exportNotice && (
          <div className="flex items-center gap-2 p-2.5 bg-emerald-950/60 border border-emerald-600/40 rounded-lg text-xs text-emerald-300">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            {exportNotice}
          </div>
        )}
      </div>

      {/* 3. MAIN WORKSPACE: MAP + DISTRICT PANEL */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* MAP COLUMN (8 cols) */}
        <div className="lg:col-span-8 space-y-4">
          <div className="rounded-2xl border border-slate-800 overflow-hidden shadow-2xl">
            {/* Map Header */}
            <div className="flex items-center justify-between bg-slate-900/90 px-4 py-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Compass className="w-4 h-4 text-cyan-400" />
                <span className="text-sm font-semibold text-slate-200">
                  India Spatial Forecast Map · 0.25° Grid
                </span>
              </div>
              <span className="text-xs px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">
                Layer: <strong className="text-cyan-400">{activeLayer.replace(/_/g, ' ').toUpperCase()}</strong>
              </span>
            </div>

            {/* Leaflet Map */}
            <div className="relative" style={{ height: '520px' }}>
              <MapContainer
                center={INDIA_CENTER}
                zoom={INDIA_ZOOM}
                style={{ height: '100%', width: '100%', background: '#0f172a' }}
                zoomControl={true}
                scrollWheelZoom={true}
                ref={mapRef}
              >
                {/* OSM Basemap */}
                <TileLayer
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                  opacity={0.25}
                />

                {/* India outline */}
                {geoJsonIndia && (
                  <GeoJSON
                    key={`india-${leadHours}`}
                    data={geoJsonIndia}
                    style={indiaStyle}
                  />
                )}

                {/* State boundaries */}
                {geoJsonStates && (
                  <GeoJSON
                    key={`states-${leadHours}`}
                    data={geoJsonStates}
                    style={stateStyle}
                  />
                )}

                {/* District forecast polygons */}
                {geoJsonDistricts && (
                  <GeoJSON
                    key={`districts-${leadHours}-${activeLayer}-${districts.length}-${districts[0]?.rainfall_mm ?? 0}`}
                    data={geoJsonDistricts}
                    style={districtStyle}
                    onEachFeature={onEachDistrict}
                  />
                )}

                {/* District centroid markers for filtered districts */}
                {filteredDistricts.map(d => {
                  const lat = d.hotspot_latitude;
                  const lon = d.hotspot_longitude;
                  if (!lat || !lon) return null;
                  const color = getDistrictColor(d, activeLayer);
                  const isSelected = selectedDistrict?.district_id === d.district_id;
                  return (
                    <CircleMarker
                      key={`cm-${d.district_id}`}
                      center={[lat, lon]}
                      radius={isSelected ? 8 : 5}
                      pathOptions={{
                        fillColor: color,
                        fillOpacity: 0.9,
                        color: isSelected ? '#ffffff' : '#1e293b',
                        weight: isSelected ? 2 : 0.5,
                      }}
                      eventHandlers={{ click: () => setSelectedDistrict(d) }}
                    >
                      <Tooltip sticky>
                        <div className="text-xs">
                          <strong>{d.district_name}</strong><br />
                          {d.state_name}<br />
                          RAMP: {d.rainfall_mm?.toFixed(1) ?? '—'} mm
                        </div>
                      </Tooltip>
                      <Popup>
                        <div style={{ fontFamily: 'monospace', fontSize: '12px', minWidth: '160px' }}>
                          <strong>{d.district_name}, {d.state_name}</strong><br />
                          RAMP: {d.rainfall_mm?.toFixed(1)} mm<br />
                          NWP: {d.raw_nwp_rainfall_mm?.toFixed(1)} mm<br />
                          Risk: {d.risk_category?.replace(/_/g, ' ')}<br />
                          P(Heavy): {((d.heavy_probability ?? 0) * 100).toFixed(1)}%<br />
                          P(Extreme): {((d.extreme_probability ?? 0) * 100).toFixed(1)}%
                        </div>
                      </Popup>
                    </CircleMarker>
                  );
                })}

                {/* Pan map when district selected */}
                <MapBoundsController district={selectedDistrict} />
              </MapContainer>

              {/* Legend overlay */}
              {showLegend && (
                <div className="absolute bottom-4 left-4 z-[1000] pointer-events-none">
                  <RainfallLegend />
                </div>
              )}

              {/* Loading overlay */}
              {loading && (
                <div className="absolute inset-0 flex items-center justify-center bg-slate-950/60 z-[2000]">
                  <div className="flex items-center gap-3 px-5 py-3 bg-slate-900 border border-slate-700 rounded-xl text-slate-300 text-sm">
                    <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />
                    Loading spatial products…
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* State aggregation table */}
          <div className="glass-panel rounded-2xl p-5 space-y-3">
            <div className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-violet-400" />
              <h3 className="text-sm font-semibold text-white">State-Level Aggregation</h3>
            </div>
            <div className="overflow-x-auto rounded-xl border border-slate-800">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-slate-900/80">
                    {['State', 'Districts', 'Mean Rainfall', 'Max Rainfall', 'High Risk', 'Extreme Risk'].map(h => (
                      <th key={h} className="px-3 py-2 text-left text-slate-400 font-semibold whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {states.length === 0
                    ? <tr><td colSpan={6} className="px-3 py-6 text-center text-slate-500">Loading state data…</td></tr>
                    : states.map(s => (
                      <tr
                        key={s.state_id}
                        className={`border-t border-slate-800/80 hover:bg-slate-900/40 cursor-pointer transition-colors
                          ${selectedState === s.state_id ? 'bg-slate-800/60' : ''}`}
                        onClick={() => setSelectedState(prev => prev === s.state_id ? 'ALL' : s.state_id)}
                      >
                        <td className="px-3 py-2 text-slate-200 font-medium">{s.state_name}</td>
                        <td className="px-3 py-2 text-slate-300">{s.district_count ?? (s.districts?.length ?? '—')}</td>
                        <td className="px-3 py-2 text-slate-300">{(s.area_weighted_rainfall_mm ?? s.mean_rainfall_mm ?? 0).toFixed(1)} mm</td>
                        <td className="px-3 py-2 text-slate-300">{(s.max_district_rainfall_mm ?? 0).toFixed(1)} mm</td>
                        <td className="px-3 py-2 text-amber-300">{s.high_risk_districts ?? (s.districts || []).filter((d: any) => d.risk_category === 'HIGH_RAINFALL' || d.risk_category === 'VERY_HIGH_RAINFALL').length}</td>
                        <td className="px-3 py-2 text-red-300">{s.extreme_risk_districts ?? (s.districts || []).filter((d: any) => d.risk_category === 'EXTREME_RAINFALL').length}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* DISTRICT PANEL (4 cols) */}
        <div className="lg:col-span-4 space-y-4">

          {/* District list */}
          <div className="glass-panel rounded-2xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <MapPin className="w-4 h-4 text-cyan-400" /> Districts
              </h3>
              <span className="text-xs text-slate-400">{filteredDistricts.length} shown</span>
            </div>
            <div className="space-y-1.5 max-h-72 overflow-y-auto pr-1">
              {filteredDistricts.map(d => (
                <button
                  key={d.district_id}
                  onClick={() => setSelectedDistrict(d)}
                  className={`w-full text-left px-3 py-2.5 rounded-xl border transition-all duration-150
                    ${selectedDistrict?.district_id === d.district_id
                      ? 'bg-slate-800 border-slate-600 ring-1 ring-cyan-500/30'
                      : 'bg-slate-900/40 border-slate-800 hover:border-slate-600'}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span
                        className="w-2.5 h-2.5 rounded-full shrink-0"
                        style={{ backgroundColor: getDistrictColor(d, activeLayer) }}
                      />
                      <div className="min-w-0">
                        <div className="text-xs font-semibold text-slate-200 truncate">{d.district_name}</div>
                        <div className="text-[10px] text-slate-400 truncate">{d.state_name}</div>
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-xs font-mono text-slate-200">{d.rainfall_mm?.toFixed(1)} mm</div>
                      <span className={`text-[9px] px-1.5 py-0.5 rounded border font-semibold ${RISK_BADGE[d.risk_category] || ''}`}>
                        {d.risk_category?.replace(/_/g, ' ')}
                      </span>
                    </div>
                  </div>
                </button>
              ))}
              {filteredDistricts.length === 0 && (
                <div className="py-6 text-center text-slate-500 text-xs">No districts match filters</div>
              )}
            </div>
          </div>

          {/* District inspector */}
          {selectedDistrict && (
            <div className="glass-panel rounded-2xl p-4 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white">{selectedDistrict.district_name}</h3>
                <span className={`text-[10px] px-2 py-0.5 rounded border font-semibold ${RISK_BADGE[selectedDistrict.risk_category] || ''}`}>
                  {selectedDistrict.risk_category?.replace(/_/g, ' ')}
                </span>
              </div>
              <div className="text-xs text-slate-400">{selectedDistrict.state_name}</div>

              {/* Rainfall bars */}
              <div className="space-y-2.5">
                {[
                  { label: 'RAMP MoE Forecast', value: selectedDistrict.rainfall_mm ?? 0, color: '#22c55e' },
                  { label: 'Raw NWP Baseline',  value: selectedDistrict.raw_nwp_rainfall_mm ?? 0, color: '#0ea5e9' },
                  { label: 'Correction (RAMP−NWP)', value: Math.abs(selectedDistrict.difference_nwp_mm ?? 0), color: '#a855f7' },
                ].map(({ label, value, color }) => (
                  <div key={label} className="space-y-1">
                    <div className="flex justify-between text-[11px]">
                      <span className="text-slate-400">{label}</span>
                      <span className="text-slate-200 font-mono">{value.toFixed(1)} mm</span>
                    </div>
                    <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${Math.min(100, (value / 250) * 100)}%`, backgroundColor: color }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              {/* Exceedance probabilities */}
              <div className="rounded-xl bg-slate-950/60 border border-slate-800 p-3 space-y-2">
                <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-1">
                  Exceedance Probabilities
                </div>
                {[
                  { label: 'P(Rain ≥0.1 mm)',  value: selectedDistrict.rain_probability ?? 0,       color: '#0ea5e9' },
                  { label: 'P(Heavy ≥64.5 mm)', value: selectedDistrict.heavy_probability ?? 0,     color: '#eab308' },
                  { label: 'P(VH ≥115.6 mm)',   value: selectedDistrict.very_heavy_probability ?? 0, color: '#f97316' },
                  { label: 'P(Extreme ≥204.5)', value: selectedDistrict.extreme_probability ?? 0,   color: '#ef4444' },
                ].map(({ label, value, color }) => (
                  <div key={label} className="flex items-center justify-between text-[11px]">
                    <span className="text-slate-400">{label}</span>
                    <span className="font-mono font-bold" style={{ color }}>{(value * 100).toFixed(1)}%</span>
                  </div>
                ))}
              </div>

              {/* Hotspot & Coverage */}
              <div className="rounded-xl bg-slate-950/60 border border-slate-800 p-3 space-y-1.5 text-[11px]">
                <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 mb-1">Diagnostics</div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Peak hotspot</span>
                  <span className="text-slate-200 font-mono">{selectedDistrict.hotspot_rainfall_mm?.toFixed(1) ?? '—'} mm</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Hotspot coords</span>
                  <span className="text-slate-200 font-mono text-[10px]">
                    {selectedDistrict.hotspot_latitude?.toFixed(2)}°N, {selectedDistrict.hotspot_longitude?.toFixed(2)}°E
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Grid coverage</span>
                  <span className="text-slate-200 font-mono">{((selectedDistrict.coverage_fraction ?? 0) * 100).toFixed(0)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Lead time</span>
                  <span className="text-slate-200 font-mono">+{selectedDistrict.lead_time_hours}h</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 4. VERIFICATION SECTION */}
      <div className="glass-panel rounded-2xl p-5 space-y-4">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-emerald-400" />
          <h3 className="text-sm font-semibold text-white">Neighbourhood Verification (FSS)</h3>
          <span className="ml-auto px-2 py-1 rounded-full bg-amber-950/60 border border-amber-700/40 text-amber-300 text-[10px] font-semibold uppercase tracking-wide">
            {verification?.fss_status || 'FSS — VERIFICATION PENDING'}
          </span>
        </div>
        <div className="rounded-xl bg-amber-950/20 border border-amber-700/30 p-4 text-xs text-amber-300 flex items-start gap-2">
          <Lock className="w-3.5 h-3.5 shrink-0 mt-0.5 text-amber-400" />
          <div>
            <span className="font-semibold text-amber-200">{verification?.disclaimer || 'REAL VERIFICATION NOT AVAILABLE:'}</span>{' '}
            {verification?.reason || 'Authoritative IMD gridded observations are not mounted for this cycle. FSS, RMSE, MAE, CSI, POD, FAR, and ETS will appear here once ground truth is paired.'}
          </div>
        </div>
        {/* Placeholder table */}
        <div className="overflow-x-auto rounded-xl border border-slate-800">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-slate-900/80">
                <th className="px-3 py-2 text-left text-slate-400 font-semibold">Scale</th>
                {(verification?.thresholds_mm || [0.1, 15.6, 64.5, 115.6, 204.5]).map((t: number) => (
                  <th key={t} className="px-3 py-2 text-center text-slate-400 font-semibold">{t} mm</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(verification?.scales_km || [5, 25, 50, 100, 200]).map((km: number) => (
                <tr key={km} className="border-t border-slate-800/80">
                  <td className="px-3 py-2 text-slate-300 font-mono">{km} km</td>
                  {Array.from({ length: 5 }).map((_, i) => (
                    <td key={i} className="px-3 py-2 text-center text-slate-600 font-mono">—</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
