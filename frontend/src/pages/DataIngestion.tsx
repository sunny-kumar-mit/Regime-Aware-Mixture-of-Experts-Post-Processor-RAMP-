/**
 * Phase 16 — Data Ingestion & Meteorological Archive Monitoring Dashboard
 * SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
 * MoES / NCMRWF
 *
 * PART W Requirements:
 *   - Provider Status Cards: NCMRWF NCUM, NCMRWF NEPS, IMD Gridded Rainfall
 *   - Real-time attributes: Availability, Latest cycle, Latest file, Resolution,
 *     Variables, Coverage, QC, Checksum, Status.
 *   - Discovered operational files catalog with authority filter (Authoritative vs Test Fixture).
 *   - Meteorological QC rule validation matrix.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Database,
  RefreshCw,
  Server,
  CloudRain,
  CheckCircle2,
  XCircle,
  FileText,
  Search,
  ShieldCheck,
  Layers,
} from 'lucide-react';

import {
  fetchIngestionStatus,
  fetchIngestionFiles,
  fetchIngestionQC,
} from '../api/client';

export const DataIngestionPage: React.FC = () => {
  const [refreshing, setRefreshing] = useState(false);
  const [statusData, setStatusData] = useState<any>(null);
  const [files, setFiles] = useState<any[]>([]);
  const [qcData, setQcData] = useState<any>(null);
  const [authorityFilter, setAuthorityFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const loadData = useCallback(async () => {
    try {
      setRefreshing(true);
      const [st, fl, qc] = await Promise.all([
        fetchIngestionStatus(),
        fetchIngestionFiles(100),
        fetchIngestionQC(),
      ]);
      setStatusData(st);
      setFiles(fl.files || []);
      setQcData(qc);
    } catch (err: any) {
      console.error('Failed to load ingestion data:', err);
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 20000);
    return () => clearInterval(interval);
  }, [loadData]);

  const cards = statusData?.provider_cards || {};
  const ncumCard = cards['NCMRWF_NCUM'];
  const nepsCard = cards['NCMRWF_NEPS'];
  const imdCard = cards['IMD_GRIDDED_RAINFALL'];

  const filteredFiles = files.filter((f) => {
    const matchAuth =
      authorityFilter === 'ALL'
        ? true
        : f.authority_level?.toUpperCase() === authorityFilter.toUpperCase();
    const matchQuery =
      searchQuery === ''
        ? true
        : f.file_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
          f.model?.toLowerCase().includes(searchQuery.toLowerCase()) ||
          f.provider?.toLowerCase().includes(searchQuery.toLowerCase());
    return matchAuth && matchQuery;
  });

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 text-slate-100">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-700/60 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Database className="h-7 w-7 text-cyan-400" />
              Meteorological Data Ingestion Dashboard
            </h1>
            <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
              NCMRWF / IMD REAL DATA PIPELINE
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Authoritative source monitoring, recursive archive discovery, CF metadata verification, and meteorological QC.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={refreshing}
          className="flex items-center gap-2 px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-600 rounded-lg text-sm font-medium transition self-start md:self-auto"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin text-cyan-400' : ''}`} />
          Scan Filesystem
        </button>
      </div>

      {/* Provider Status Cards (PART W) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Card 1: NCMRWF NCUM */}
        <div className="bg-slate-900 border border-slate-700/80 rounded-xl p-5 shadow-lg space-y-4 relative overflow-hidden">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <Server className="h-5 w-5 text-blue-400" />
              <div>
                <h3 className="font-bold text-white text-sm">NCMRWF NCUM</h3>
                <div className="text-[11px] text-slate-400">Deterministic NWP Model</div>
              </div>
            </div>
            <span
              className={`px-2 py-0.5 text-[10px] font-bold rounded-full ${
                ncumCard?.availability === 'DETECTED'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                  : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
              }`}
            >
              {ncumCard?.availability || 'UNAVAILABLE'}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs pt-1 border-t border-slate-800">
            <div>
              <span className="text-slate-500 text-[10px] block">NATIVE / TARGET RES</span>
              <span className="font-semibold text-slate-200">
                {ncumCard?.resolution || '0.12°'} / 0.25°
              </span>
            </div>
            <div>
              <span className="text-slate-500 text-[10px] block">VARIABLES REQUIRED</span>
              <span className="font-semibold text-cyan-300">18 Predictors (v1.0.0)</span>
            </div>
            <div>
              <span className="text-slate-500 text-[10px] block">LATEST CYCLE</span>
              <span className="font-semibold text-slate-200">{ncumCard?.latest_cycle || 'None'}</span>
            </div>
            <div>
              <span className="text-slate-500 text-[10px] block">COVERAGE</span>
              <span className="font-semibold text-slate-200">
                {ncumCard?.coverage_percent?.toFixed(1) || '0.0'}%
              </span>
            </div>
          </div>

          <div className="text-[11px] font-mono bg-slate-950/70 p-2.5 rounded border border-slate-800/80 space-y-1">
            <div className="text-slate-400 truncate">
              File: <span className="text-slate-300">{ncumCard?.latest_file || 'None detected'}</span>
            </div>
            <div className="text-slate-500 truncate text-[10px]">
              SHA-256: {ncumCard?.checksum?.slice(0, 16) || 'N/A'}...
            </div>
          </div>

          <div className="text-[10px] text-slate-400">
            Status: <span className="text-amber-400 font-semibold">{ncumCard?.status || 'WAITING_FOR_DATA'}</span>
          </div>
        </div>

        {/* Card 2: NCMRWF NEPS */}
        <div className="bg-slate-900 border border-slate-700/80 rounded-xl p-5 shadow-lg space-y-4 relative overflow-hidden">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <Layers className="h-5 w-5 text-indigo-400" />
              <div>
                <h3 className="font-bold text-white text-sm">NCMRWF NEPS</h3>
                <div className="text-[11px] text-slate-400">23-Member Ensemble NWP</div>
              </div>
            </div>
            <span
              className={`px-2 py-0.5 text-[10px] font-bold rounded-full ${
                nepsCard?.availability === 'DETECTED'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                  : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
              }`}
            >
              {nepsCard?.availability || 'UNAVAILABLE'}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs pt-1 border-t border-slate-800">
            <div>
              <span className="text-slate-500 text-[10px] block">ENSEMBLE MEMBERS</span>
              <span className="font-semibold text-slate-200">23 Members</span>
            </div>
            <div>
              <span className="text-slate-500 text-[10px] block">RESOLUTION</span>
              <span className="font-semibold text-slate-200">0.12° native</span>
            </div>
            <div>
              <span className="text-slate-500 text-[10px] block">LATEST CYCLE</span>
              <span className="font-semibold text-slate-200">{nepsCard?.latest_cycle || 'None'}</span>
            </div>
            <div>
              <span className="text-slate-500 text-[10px] block">COVERAGE</span>
              <span className="font-semibold text-slate-200">
                {nepsCard?.coverage_percent?.toFixed(1) || '0.0'}%
              </span>
            </div>
          </div>

          <div className="text-[11px] font-mono bg-slate-950/70 p-2.5 rounded border border-slate-800/80 space-y-1">
            <div className="text-slate-400 truncate">
              File: <span className="text-slate-300">{nepsCard?.latest_file || 'None detected'}</span>
            </div>
            <div className="text-slate-500 truncate text-[10px]">
              SHA-256: {nepsCard?.checksum?.slice(0, 16) || 'N/A'}...
            </div>
          </div>

          <div className="text-[10px] text-slate-400">
            Status: <span className="text-amber-400 font-semibold">{nepsCard?.status || 'WAITING_FOR_DATA'}</span>
          </div>
        </div>

        {/* Card 3: IMD Gridded Rainfall */}
        <div className="bg-slate-900 border border-slate-700/80 rounded-xl p-5 shadow-lg space-y-4 relative overflow-hidden">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <CloudRain className="h-5 w-5 text-emerald-400" />
              <div>
                <h3 className="font-bold text-white text-sm">IMD Gridded Obs</h3>
                <div className="text-[11px] text-slate-400">0.25° Daily Rainfall (Ground Truth)</div>
              </div>
            </div>
            <span
              className={`px-2 py-0.5 text-[10px] font-bold rounded-full ${
                imdCard?.availability === 'DETECTED'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                  : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
              }`}
            >
              {imdCard?.availability || 'UNAVAILABLE'}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs pt-1 border-t border-slate-800">
            <div>
              <span className="text-slate-500 text-[10px] block">CANONICAL GRID</span>
              <span className="font-semibold text-slate-200">0.25° (129x137)</span>
            </div>
            <div>
              <span className="text-slate-500 text-[10px] block">UNITS</span>
              <span className="font-semibold text-emerald-300">mm / 24h</span>
            </div>
            <div>
              <span className="text-slate-500 text-[10px] block">TARGET CELLS</span>
              <span className="font-semibold text-slate-200">17,673 Cells</span>
            </div>
            <div>
              <span className="text-slate-500 text-[10px] block">COVERAGE</span>
              <span className="font-semibold text-slate-200">
                {imdCard?.coverage_percent?.toFixed(1) || '0.0'}%
              </span>
            </div>
          </div>

          <div className="text-[11px] font-mono bg-slate-950/70 p-2.5 rounded border border-slate-800/80 space-y-1">
            <div className="text-slate-400 truncate">
              File: <span className="text-slate-300">{imdCard?.latest_file || 'None detected'}</span>
            </div>
            <div className="text-slate-500 truncate text-[10px]">
              SHA-256: {imdCard?.checksum?.slice(0, 16) || 'N/A'}...
            </div>
          </div>

          <div className="text-[10px] text-slate-400">
            Status: <span className="text-amber-400 font-semibold">{imdCard?.status || 'WAITING_FOR_DATA'}</span>
          </div>
        </div>
      </div>

      {/* Discovered Files Table */}
      <div className="bg-slate-900 border border-slate-700/80 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <FileText className="h-4 w-4 text-cyan-400" />
              Discovered Meteorological Archives & Fixtures
            </h2>
            <p className="text-xs text-slate-400">
              Recursive discovery scans raw folders for NetCDF, GRIB, and tabular files.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="h-3.5 w-3.5 absolute left-2.5 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search files..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500 w-44"
              />
            </div>

            <select
              value={authorityFilter}
              onChange={(e) => setAuthorityFilter(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
            >
              <option value="ALL">All Authority Levels</option>
              <option value="AUTHORITATIVE_PRIMARY">Authoritative Primary Only</option>
              <option value="TEST_FIXTURE">Test Fixtures Only</option>
              <option value="SECONDARY_PROXY">Secondary / Proxy Only</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[10px]">
                <th className="py-2.5 px-3">File Name</th>
                <th className="py-2.5 px-3">Format</th>
                <th className="py-2.5 px-3">Model</th>
                <th className="py-2.5 px-3">Authority Level</th>
                <th className="py-2.5 px-3">Cycle</th>
                <th className="py-2.5 px-3">Size (Bytes)</th>
                <th className="py-2.5 px-3">Integrity</th>
                <th className="py-2.5 px-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
              {filteredFiles.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-6 text-center text-slate-500 italic">
                    No files found matching criteria.
                  </td>
                </tr>
              ) : (
                filteredFiles.map((f, i) => (
                  <tr key={i} className="hover:bg-slate-800/30">
                    <td className="py-2.5 px-3 text-cyan-300 font-sans font-medium">{f.file_name}</td>
                    <td className="py-2.5 px-3">{f.format}</td>
                    <td className="py-2.5 px-3 text-slate-200">{f.model}</td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                          f.authority_level === 'AUTHORITATIVE_PRIMARY'
                            ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
                            : f.authority_level === 'TEST_FIXTURE'
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {f.authority_level}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">{f.cycle || '—'}</td>
                    <td className="py-2.5 px-3 text-slate-400">{f.file_size_bytes?.toLocaleString()}</td>
                    <td className="py-2.5 px-3">
                      {f.is_valid_integrity ? (
                        <span className="text-emerald-400 flex items-center gap-1">
                          <CheckCircle2 className="h-3 w-3" /> Valid
                        </span>
                      ) : (
                        <span className="text-rose-400 flex items-center gap-1">
                          <XCircle className="h-3 w-3" /> Failed
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="text-[10px] text-slate-300">{f.status}</span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Meteorological QC Rules Active */}
      <div className="bg-slate-900 border border-slate-700/80 rounded-xl p-5 shadow-lg space-y-3">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-emerald-400" />
          Active Meteorological QC Rule Engine (Part I)
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {qcData?.active_rules?.map((r: any) => (
            <div key={r.id} className="p-3 bg-slate-800/40 border border-slate-700/60 rounded-lg text-xs">
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-cyan-300 font-mono">{r.id}</span>
                <span className="text-[10px] text-emerald-400 font-semibold">ENFORCED</span>
              </div>
              <div className="font-semibold text-slate-200">{r.name}</div>
              <div className="text-[11px] text-slate-400 mt-0.5">{r.description}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default DataIngestionPage;
