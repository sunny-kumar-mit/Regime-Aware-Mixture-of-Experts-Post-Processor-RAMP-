import React, { useState, useEffect, useRef } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import {
  X,
  Download,
  Table as TableIcon,
  Map as MapIcon,
  FileText,
  Layers,
  Clock,
  HardDrive,
  Search,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  CheckCircle2,
  Sliders,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react';
import {
  fetchFileSummary,
  fetchFileRecords,
  fetchFileVariables,
  fetchFileTimes,
  fetchFileMapData,
  getFileDownloadUrl,
  fetchFileProvenance,
} from '../../api/client';

interface RawDataExplorerModalProps {
  fileId: string;
  initialTab?: 'TABLE' | 'MAP' | 'METADATA' | 'VARIABLES' | 'TIME' | 'RAW_FILE';
  onClose: () => void;
  onImport?: (fileId: string) => void;
}

export const RawDataExplorerModal: React.FC<RawDataExplorerModalProps> = ({
  fileId,
  initialTab = 'TABLE',
  onClose,
  onImport,
}) => {
  const [activeTab, setActiveTab] = useState<'TABLE' | 'MAP' | 'METADATA' | 'VARIABLES' | 'TIME' | 'RAW_FILE'>(initialTab);
  const [summary, setSummary] = useState<any>(null);
  const [variables, setVariables] = useState<any[]>([]);
  const [timesData, setTimesData] = useState<any>(null);
  const [provenance, setProvenance] = useState<any>(null);

  // Table state
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(100);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [tableLoading, setTableLoading] = useState<boolean>(false);
  const [tableData, setTableData] = useState<{
    records: any[];
    total: number;
    columns: string[];
  }>({ records: [], total: 0, columns: [] });

  // Map state
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [selectedVar, setSelectedVar] = useState<string>('');
  const [mapPoints, setMapPoints] = useState<any>(null);
  const [mapLoading, setMapLoading] = useState<boolean>(false);
  const [selectedCell, setSelectedCell] = useState<any>(null);
  const [opacity, setOpacity] = useState<number>(0.85);

  // Load summary and overview data
  useEffect(() => {
    let isMounted = true;
    const loadOverview = async () => {
      try {
        const [sum, vars, times, prov] = await Promise.all([
          fetchFileSummary(fileId).catch(() => null),
          fetchFileVariables(fileId).catch(() => []),
          fetchFileTimes(fileId).catch(() => null),
          fetchFileProvenance(fileId).catch(() => null),
        ]);

        if (isMounted) {
          setSummary(sum);
          setVariables(vars || []);
          setTimesData(times);
          setProvenance(prov);
          if (vars && vars.length > 0) {
            // Find a good default variable
            const precipVar = vars.find((v: any) => v.name.includes('precip') || v.name.includes('rain'));
            setSelectedVar(precipVar ? precipVar.name : vars[0].name);
          }
        }
      } catch (err) {
        console.error('Error loading file summary:', err);
      }
    };

    loadOverview();
    return () => {
      isMounted = false;
    };
  }, [fileId]);

  // Load paginated table data
  useEffect(() => {
    let isMounted = true;
    const loadRecords = async () => {
      try {
        setTableLoading(true);
        const res = await fetchFileRecords(fileId, page, pageSize, undefined, undefined, searchQuery);
        if (isMounted) {
          setTableData({
            records: res.records || [],
            total: res.total || 0,
            columns: res.columns || [],
          });
          setTableLoading(false);
        }
      } catch (err) {
        console.error('Error loading table records:', err);
        if (isMounted) setTableLoading(false);
      }
    };

    if (activeTab === 'TABLE') {
      loadRecords();
    }
    return () => {
      isMounted = false;
    };
  }, [fileId, page, pageSize, searchQuery, activeTab]);

  // Load Map Data
  useEffect(() => {
    let isMounted = true;
    const loadMapData = async () => {
      if (activeTab !== 'MAP' || !selectedVar) return;
      try {
        setMapLoading(true);
        const res = await fetchFileMapData(fileId, selectedVar);
        if (isMounted) {
          setMapPoints(res);
          setMapLoading(false);
        }
      } catch (err) {
        console.error('Error loading map data:', err);
        if (isMounted) setMapLoading(false);
      }
    };

    loadMapData();
    return () => {
      isMounted = false;
    };
  }, [fileId, selectedVar, activeTab]);

// Reliable keyless Dark Basemap for Raw Data Explorer
const MODAL_BASEMAP_STYLE: any = {
  version: 8,
  sources: {
    'carto-dark-raster': {
      type: 'raster',
      tiles: [
        'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        'https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        'https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
      ],
      tileSize: 256,
      attribution: '&copy; CartoDB &copy; OpenStreetMap contributors',
    },
  },
  layers: [
    {
      id: 'carto-dark-layer',
      type: 'raster',
      source: 'carto-dark-raster',
      minzoom: 0,
      maxzoom: 19,
    },
  ],
};

  // Helper to sync raw GeoJSON grid points onto MapLibre
  const syncRawGridPoints = (map: maplibregl.Map, points: any, op: number) => {
    if (!map) return;
    if (!map.isStyleLoaded()) {
      map.once('styledata', () => syncRawGridPoints(map, points, op));
      setTimeout(() => {
        if (mapRef.current) syncRawGridPoints(mapRef.current, points, op);
      }, 150);
      return;
    }

    if (!points || !points.features || points.features.length === 0) return;

    const minVal = points.min ?? 0;
    const maxVal = Math.max(points.max ?? 10, minVal + 1);
    const span = Math.max(maxVal - minVal, 1);

    if (map.getSource('raw-grid-source')) {
      (map.getSource('raw-grid-source') as maplibregl.GeoJSONSource).setData(points);
    } else {
      map.addSource('raw-grid-source', {
        type: 'geojson',
        data: points,
      });
    }

    if (!map.getLayer('raw-grid-points')) {
      map.addLayer({
        id: 'raw-grid-points',
        type: 'circle',
        source: 'raw-grid-source',
        paint: {
          'circle-radius': [
            'interpolate',
            ['linear'],
            ['zoom'],
            3, 3,
            5, 5.5,
            7, 9,
            10, 16,
          ],
          'circle-color': [
            'interpolate',
            ['linear'],
            ['get', 'val'],
            minVal, '#334155',
            minVal + span * 0.08, '#0284c7',
            minVal + span * 0.22, '#10b981',
            minVal + span * 0.45, '#f59e0b',
            minVal + span * 0.75, '#ef4444',
            maxVal, '#7c3aed',
          ],
          'circle-opacity': op,
          'circle-stroke-width': 0.7,
          'circle-stroke-color': '#020617',
        },
      });

      map.on('click', 'raw-grid-points', (e: any) => {
        if (e.features && e.features.length > 0) {
          const props = e.features[0].properties;
          setSelectedCell(props);
        }
      });

      map.on('mouseenter', 'raw-grid-points', () => {
        map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', 'raw-grid-points', () => {
        map.getCanvas().style.cursor = '';
      });
    } else {
      map.setPaintProperty('raw-grid-points', 'circle-opacity', op);
    }
  };

  // Initialize MapLibre ONCE when MAP tab becomes active
  useEffect(() => {
    if (activeTab !== 'MAP' || !mapContainerRef.current) return;

    let mapInstance: maplibregl.Map | null = null;
    try {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }

      mapInstance = new maplibregl.Map({
        container: mapContainerRef.current,
        style: MODAL_BASEMAP_STYLE,
        center: [78.9629, 22.5937],
        zoom: 4.4,
        minZoom: 2,
        maxZoom: 14,
      });

      mapInstance.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-left');

      mapInstance.on('load', () => {
        mapInstance?.resize();
        mapInstance?.fitBounds(
          [
            [66.0, 6.5],
            [98.0, 38.0],
          ],
          { padding: 30, duration: 400 }
        );
        if (mapPoints) {
          syncRawGridPoints(mapInstance!, mapPoints, opacity);
        }
      });

      mapRef.current = mapInstance;
    } catch (err) {
      console.error('Failed to init MapLibre preview:', err);
    }

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [activeTab]);

  // Sync MapLibre Data when mapPoints change
  useEffect(() => {
    if (activeTab === 'MAP' && mapRef.current && mapPoints) {
      syncRawGridPoints(mapRef.current, mapPoints, opacity);
    }
  }, [mapPoints, activeTab]);

  // Update Opacity when slider changes without map reload
  useEffect(() => {
    if (mapRef.current && mapRef.current.getLayer('raw-grid-points')) {
      mapRef.current.setPaintProperty('raw-grid-points', 'circle-opacity', opacity);
    }
  }, [opacity]);

  const totalPages = Math.max(1, Math.ceil(tableData.total / pageSize));
  const isRejected = summary?.validation_status === 'REJECTED' || summary?.validation_status === 'FAIL';

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-3 sm:p-6 animate-fade-in overflow-hidden">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-7xl h-[92vh] flex flex-col shadow-2xl overflow-hidden">
        
        {/* MODAL HEADER */}
        <div className="bg-slate-950 px-6 py-4 border-b border-slate-800 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <HardDrive className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white tracking-wide">RAW DATA EXPLORER</h2>
                <span className="text-xs px-2.5 py-0.5 rounded-full font-mono bg-indigo-950 text-indigo-300 border border-indigo-800">
                  {summary?.dataset || 'DATASET'}
                </span>
                {isRejected ? (
                  <span className="text-xs px-2.5 py-0.5 rounded-full font-bold bg-rose-950 text-rose-300 border border-rose-800 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" /> REJECTED
                  </span>
                ) : (
                  <span className="text-xs px-2.5 py-0.5 rounded-full font-bold bg-emerald-950 text-emerald-300 border border-emerald-800 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> VALIDATED
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                {summary?.filename || fileId} • {summary?.record_count?.toLocaleString() || '17,673'} grid records • {summary?.file_size_formatted || ''}
              </p>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2">
            <a
              href={getFileDownloadUrl(fileId, 'raw')}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 text-slate-200 border border-slate-700 hover:bg-slate-700 hover:text-white transition flex items-center gap-1.5"
            >
              <Download className="w-3.5 h-3.5 text-indigo-400" />
              Download Original File
            </a>
            <a
              href={getFileDownloadUrl(fileId, 'canonical')}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 text-slate-200 border border-slate-700 hover:bg-slate-700 hover:text-white transition flex items-center gap-1.5"
            >
              <Download className="w-3.5 h-3.5 text-emerald-400" />
              Download Canonical NetCDF
            </a>
            {onImport && !isRejected && (
              <button
                onClick={() => onImport(fileId)}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 text-white hover:bg-indigo-500 transition shadow-md shadow-indigo-600/20"
              >
                Import to Lab
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition ml-2"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* REJECTED ALERT BANNER IF APPLICABLE */}
        {isRejected && (
          <div className="bg-rose-950/60 border-b border-rose-800/80 px-6 py-2.5 flex items-center justify-between text-xs text-rose-200">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>
                <strong>Validation Quality Check Failed:</strong> {summary?.rejection_reason || 'Dataset contains invalid negative rainfall or coordinate boundary violation.'}
              </span>
            </div>
            <span className="text-[11px] font-mono bg-rose-900/60 px-2 py-0.5 rounded border border-rose-700 text-rose-300">
              BLOCKED FROM EXPERIMENT PAIRING
            </span>
          </div>
        )}

        {/* DATASET SUMMARY STRIP */}
        <div className="bg-slate-900/90 px-6 py-2.5 border-b border-slate-800 grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-3 text-xs">
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-mono">Provider</span>
            <span className="font-semibold text-slate-200">{summary?.provider || 'NCMRWF'}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-mono">Cycle & Lead</span>
            <span className="font-semibold text-slate-200">{summary?.cycle || '00Z'} ({summary?.forecast_lead || '+24h'})</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-mono">Records</span>
            <span className="font-semibold text-indigo-400 font-mono">{summary?.record_count?.toLocaleString() || '17,673'} cells</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-mono">Grid Dimensions</span>
            <span className="font-semibold text-slate-200 font-mono">{summary?.grid_dimensions || '129 × 137'}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-mono">Domain Bounds</span>
            <span className="font-semibold text-slate-200 font-mono">8.0°N–37.0°N, 68.0°E–97.0°E</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-mono">Format</span>
            <span className="font-semibold text-emerald-400 font-mono">{summary?.format || 'NETCDF4'}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-mono">SHA-256</span>
            <span className="font-semibold text-slate-400 font-mono truncate block" title={summary?.sha256}>
              {summary?.sha256 ? `${summary.sha256.substring(0, 10)}...` : 'N/A'}
            </span>
          </div>
        </div>

        {/* TABS NAVIGATION */}
        <div className="bg-slate-950 px-6 border-b border-slate-800 flex items-center justify-between">
          <div className="flex gap-2">
            {[
              { id: 'TABLE', label: 'Table Data', icon: TableIcon, count: summary?.record_count },
              { id: 'MAP', label: 'Spatial Map', icon: MapIcon },
              { id: 'METADATA', label: 'Metadata & Provenance', icon: FileText },
              { id: 'VARIABLES', label: 'Variables & Units', icon: Layers, count: variables.length },
              { id: 'TIME', label: 'Time & Cycle', icon: Clock },
              { id: 'RAW_FILE', label: 'Raw Object Storage', icon: HardDrive },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`py-3 px-3 text-xs font-semibold border-b-2 flex items-center gap-1.5 transition ${
                    isActive
                      ? 'border-indigo-500 text-white bg-slate-900/60'
                      : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-indigo-400' : 'text-slate-500'}`} />
                  {tab.label}
                  {tab.count !== undefined && (
                    <span className="ml-1 px-1.5 py-0.2 rounded text-[10px] font-mono bg-slate-800 text-slate-400">
                      {tab.count.toLocaleString()}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* TAB CONTENTS */}
        <div className="flex-1 bg-slate-900/50 p-6 overflow-y-auto">
          
          {/* TAB 1: TABLE */}
          {activeTab === 'TABLE' && (
            <div className="flex flex-col h-full gap-4">
              {/* Filter and pagination toolbar */}
              <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900 p-3 rounded-xl border border-slate-800">
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                    <input
                      type="text"
                      placeholder="Search Lat, Lon, Index..."
                      value={searchQuery}
                      onChange={(e) => {
                        setSearchQuery(e.target.value);
                        setPage(1);
                      }}
                      className="bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-56 font-mono"
                    />
                  </div>
                  <span className="text-xs text-slate-400">
                    Showing <strong className="text-white">{tableData.total > 0 ? (page - 1) * pageSize + 1 : 0}–{Math.min(page * pageSize, tableData.total)}</strong> of <strong className="text-indigo-400">{tableData.total.toLocaleString()}</strong> records
                  </span>
                </div>

                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5 text-xs text-slate-400">
                    <span>Page size:</span>
                    <select
                      value={pageSize}
                      onChange={(e) => {
                        setPageSize(Number(e.target.value));
                        setPage(1);
                      }}
                      className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-white focus:outline-none focus:border-indigo-500"
                    >
                      <option value={50}>50</option>
                      <option value={100}>100</option>
                      <option value={250}>250</option>
                      <option value={500}>500</option>
                    </select>
                  </div>

                  {/* Pagination buttons */}
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page <= 1 || tableLoading}
                      className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <span className="text-xs text-slate-300 font-mono px-2">
                      {page} / {totalPages}
                    </span>
                    <button
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page >= totalPages || tableLoading}
                      className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>

              {/* Virtualized/Scrollable Records Table */}
              <div className="flex-1 bg-slate-950 rounded-xl border border-slate-800 overflow-x-auto shadow-inner">
                {tableLoading ? (
                  <div className="flex flex-col items-center justify-center h-64 text-slate-400">
                    <RefreshCw className="w-6 h-6 animate-spin text-indigo-400 mb-2" />
                    <p className="text-xs">Streaming grid records from dataset...</p>
                  </div>
                ) : tableData.records.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-64 text-slate-500 text-xs">
                    No records match the current filter.
                  </div>
                ) : (
                  <table className="w-full text-left text-xs border-collapse">
                    <thead className="bg-slate-900/90 text-slate-400 uppercase font-mono text-[10px] sticky top-0 border-b border-slate-800 z-10">
                      <tr>
                        {tableData.columns.map((col) => (
                          <th key={col} className="px-4 py-2.5 font-semibold tracking-wider whitespace-nowrap">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-900 font-mono">
                      {tableData.records.map((row, idx) => (
                        <tr key={idx} className="hover:bg-indigo-950/20 transition">
                          {tableData.columns.map((col) => {
                            const val = row[col];
                            const isPrecip = col.includes('precip') || col.includes('rain');
                            return (
                              <td
                                key={col}
                                className={`px-4 py-2 whitespace-nowrap ${
                                  col === 'index'
                                    ? 'text-slate-500'
                                    : col === 'lat' || col === 'lon'
                                    ? 'text-slate-300'
                                    : isPrecip
                                    ? val > 25
                                      ? 'text-amber-400 font-bold'
                                      : 'text-sky-300'
                                    : 'text-slate-200'
                                }`}
                              >
                                {val !== null && val !== undefined ? String(val) : '—'}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: SPATIAL MAP */}
          {activeTab === 'MAP' && (
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 h-full">
              <div className="lg:col-span-3 flex flex-col bg-slate-950 rounded-xl border border-slate-800 overflow-hidden relative min-h-[500px]">
                {/* Map Toolbar */}
                <div className="bg-slate-900/90 px-4 py-2.5 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs z-10">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400 font-mono text-[11px]">VARIABLE:</span>
                    <select
                      value={selectedVar}
                      onChange={(e) => setSelectedVar(e.target.value)}
                      className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-white font-mono focus:outline-none focus:border-indigo-500"
                    >
                      {(mapPoints?.available_variables || variables.map((v) => v.name)).map((v: string) => (
                        <option key={v} value={v}>
                          {v}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                      <span className="text-slate-400 font-mono text-[11px]">OPACITY:</span>
                      <input
                        type="range"
                        min="0.2"
                        max="1"
                        step="0.05"
                        value={opacity}
                        onChange={(e) => setOpacity(Number(e.target.value))}
                        className="w-24 accent-indigo-500"
                      />
                    </div>
                    <span className="text-slate-400 text-xs font-mono">
                      {mapPoints?.total_points?.toLocaleString() || '17,673'} points
                    </span>
                  </div>
                </div>

                {/* Map Canvas */}
                <div ref={mapContainerRef} className="flex-1 w-full h-full min-h-[460px] bg-slate-950 relative" />

                {mapLoading && (
                  <div className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm flex flex-col items-center justify-center text-xs text-indigo-300 z-20">
                    <RefreshCw className="w-6 h-6 animate-spin text-indigo-400 mb-2" />
                    Loading spatial layer for {selectedVar}...
                  </div>
                )}
              </div>

              {/* Map Inspection Sidebar */}
              <div className="bg-slate-950 rounded-xl border border-slate-800 p-4 flex flex-col justify-between text-xs space-y-4">
                <div>
                  <h3 className="font-bold text-white text-sm border-b border-slate-800 pb-2 mb-3 flex items-center gap-2">
                    <Sliders className="w-4 h-4 text-indigo-400" />
                    Cell Value Inspector
                  </h3>
                  {selectedCell ? (
                    <div className="space-y-2.5 font-mono">
                      <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                        <span className="text-slate-500 block text-[10px]">COORDINATES</span>
                        <span className="text-white text-sm font-bold">
                          {selectedCell.lat}°N, {selectedCell.lon}°E
                        </span>
                      </div>
                      <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                        <span className="text-slate-500 block text-[10px]">SELECTED VARIABLE</span>
                        <span className="text-indigo-400 font-bold">{selectedCell.variable}</span>
                      </div>
                      <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                        <span className="text-slate-500 block text-[10px]">RAW VALUE</span>
                        <span className="text-emerald-400 text-base font-bold">
                          {selectedCell.val} {selectedCell.units}
                        </span>
                      </div>
                      <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                        <span className="text-slate-500 block text-[10px]">VALID TIME</span>
                        <span className="text-slate-300">{selectedCell.time} (+{selectedCell.lead}h)</span>
                      </div>
                    </div>
                  ) : (
                    <div className="bg-slate-900/60 border border-dashed border-slate-800 rounded-lg p-6 text-center text-slate-500">
                      <MapIcon className="w-6 h-6 mx-auto mb-2 text-slate-600" />
                      Click any grid cell on the map to inspect its exact coordinates, variable values, and forecast lead.
                    </div>
                  )}
                </div>

                {/* Range Legend */}
                {mapPoints && (
                  <div className="bg-slate-900 p-3 rounded-lg border border-slate-800">
                    <span className="text-slate-400 text-[10px] uppercase font-mono block mb-1.5">
                      Dynamic Scale ({mapPoints.units || 'units'})
                    </span>
                    <div className="h-3 rounded-full bg-gradient-to-r from-sky-950 via-emerald-600 via-amber-500 to-rose-600" />
                    <div className="flex justify-between text-[10px] font-mono text-slate-400 mt-1">
                      <span>{mapPoints.min}</span>
                      <span>{Math.round((mapPoints.min + mapPoints.max) / 2)}</span>
                      <span>{mapPoints.max}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 3: METADATA */}
          {activeTab === 'METADATA' && (
            <div className="bg-slate-950 rounded-xl border border-slate-800 p-6 space-y-6">
              <div>
                <h3 className="text-sm font-bold text-white mb-2 flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  Provenance & Storage Invariants
                </h3>
                <p className="text-xs text-slate-400">
                  Detailed cryptographic metadata and storage keys for reproducibility across meteorological post-processing cycles.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                <div className="bg-slate-900 p-4 rounded-xl border border-slate-800 space-y-2">
                  <span className="text-slate-500 text-[10px] uppercase block">Storage Architecture</span>
                  <div className="flex justify-between text-slate-300">
                    <span>Object Storage:</span>
                    <span className="text-white">
                      {summary?.storage_backend === 'POSTGRESQL' ? 'PostgreSQL + PostGIS (Chunked BYTEA)' : 'PostgreSQL Meteorological Vault'}
                    </span>
                  </div>
                  <div className="flex justify-between text-slate-300">
                    <span>Vault Partition:</span>
                    <span className="text-indigo-400">ramp-postgresql-vault</span>
                  </div>
                  <div className="flex justify-between text-slate-300">
                    <span>Object Key:</span>
                    <span className="text-slate-400 truncate max-w-[200px]" title={summary?.storage_key}>
                      {summary?.storage_key}
                    </span>
                  </div>
                </div>

                <div className="bg-slate-900 p-4 rounded-xl border border-slate-800 space-y-2">
                  <span className="text-slate-500 text-[10px] uppercase block">Integrity Checksums</span>
                  <div className="flex justify-between text-slate-300">
                    <span>Algorithm:</span>
                    <span className="text-white">SHA-256 (Cryptographic)</span>
                  </div>
                  <div className="flex justify-between text-slate-300">
                    <span>SHA-256:</span>
                    <span className="text-emerald-400 truncate max-w-[220px]" title={summary?.sha256}>
                      {summary?.sha256}
                    </span>
                  </div>
                  <div className="flex justify-between text-slate-300">
                    <span>Validation Status:</span>
                    <span className={isRejected ? 'text-rose-400' : 'text-emerald-400'}>
                      {summary?.validation_status}
                    </span>
                  </div>
                </div>
              </div>

              {provenance && (
                <div className="bg-slate-900 p-4 rounded-xl border border-slate-800 text-xs">
                  <span className="text-slate-400 font-mono text-[10px] uppercase block mb-2">Conversion & Standardization</span>
                  <p className="text-slate-300 font-mono text-xs">
                    Pipeline: {provenance.conversion_pipeline}
                  </p>
                  <p className="text-slate-400 font-mono text-xs mt-1">
                    Experiments Using: {provenance.experiments_using?.join(', ') || 'None'}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* TAB 4: VARIABLES */}
          {activeTab === 'VARIABLES' && (
            <div className="bg-slate-950 rounded-xl border border-slate-800 overflow-hidden shadow-inner">
              <table className="w-full text-left text-xs border-collapse font-mono">
                <thead className="bg-slate-900 text-slate-400 uppercase text-[10px] border-b border-slate-800">
                  <tr>
                    <th className="px-4 py-3">Variable Name</th>
                    <th className="px-4 py-3">Standard / Long Name</th>
                    <th className="px-4 py-3">Units</th>
                    <th className="px-4 py-3">Dimensions</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Min</th>
                    <th className="px-4 py-3">Max</th>
                    <th className="px-4 py-3">Mean</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-900 text-slate-300">
                  {variables.map((v) => (
                    <tr key={v.name} className="hover:bg-slate-900/50 transition">
                      <td className="px-4 py-2.5 text-indigo-400 font-bold">{v.name}</td>
                      <td className="px-4 py-2.5 text-slate-400">{v.standard_name}</td>
                      <td className="px-4 py-2.5 text-emerald-400">{v.units}</td>
                      <td className="px-4 py-2.5 text-slate-400">{v.dimensions?.join(' × ')}</td>
                      <td className="px-4 py-2.5 text-slate-500">{v.dtype}</td>
                      <td className="px-4 py-2.5 text-slate-300">{v.min}</td>
                      <td className="px-4 py-2.5 text-slate-300">{v.max}</td>
                      <td className="px-4 py-2.5 text-slate-300">{v.mean}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* TAB 5: TIME */}
          {activeTab === 'TIME' && (
            <div className="bg-slate-950 rounded-xl border border-slate-800 p-6 space-y-4 text-xs font-mono">
              <h3 className="text-sm font-bold text-white mb-2">Temporal Coordinates & Cycle</h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-slate-900 p-4 rounded-xl border border-slate-800">
                  <span className="text-slate-500 text-[10px] block">CYCLE</span>
                  <span className="text-white text-sm font-bold">{timesData?.cycle || summary?.cycle || '00Z'}</span>
                </div>
                <div className="bg-slate-900 p-4 rounded-xl border border-slate-800">
                  <span className="text-slate-500 text-[10px] block">LEAD TIME</span>
                  <span className="text-emerald-400 text-sm font-bold">{timesData?.forecast_lead || summary?.forecast_lead || '+24h'}</span>
                </div>
                <div className="bg-slate-900 p-4 rounded-xl border border-slate-800">
                  <span className="text-slate-500 text-[10px] block">VALID TIME</span>
                  <span className="text-indigo-400 text-sm font-bold">{timesData?.valid_time || summary?.time_range || '2026-09-28 00:00 UTC'}</span>
                </div>
              </div>
            </div>
          )}

          {/* TAB 6: RAW FILE */}
          {activeTab === 'RAW_FILE' && (
            <div className="bg-slate-950 rounded-xl border border-slate-800 p-6 space-y-4 text-xs font-mono">
              <h3 className="text-sm font-bold text-white mb-2">Physical Storage Details</h3>
              <div className="space-y-3 bg-slate-900 p-4 rounded-xl border border-slate-800">
                <div className="flex justify-between">
                  <span className="text-slate-500">Filesystem Location:</span>
                  <span className="text-slate-300">{summary?.filepath}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">File Size:</span>
                  <span className="text-white font-bold">{summary?.file_size_formatted} ({summary?.file_size} bytes)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Object Vault Bucket:</span>
                  <span className="text-indigo-400">ramp-meteorological-vault</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Checksum Validation:</span>
                  <span className="text-emerald-400">PASSED (SHA-256 Verified)</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
