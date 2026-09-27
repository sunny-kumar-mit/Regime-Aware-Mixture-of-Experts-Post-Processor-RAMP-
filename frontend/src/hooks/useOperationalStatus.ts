import { useState, useEffect, useCallback, useRef } from 'react';
import { fetchOperationalAvailability, fetchHealth } from '../api/client';
import { HealthResponse } from '../types/api';

export interface OperationalStatusData {
  ncmrwf_ncum: boolean;
  ncmrwf_neps: boolean;
  imd_obs: boolean;
  ramp_model: boolean;
  overall_mode: string;
  honesty_notice: string;
  timestamp?: string;
  last_scan?: string;
  ncum_details?: {
    status?: string;
    cycle?: string;
    lead_hours?: number;
    features_contract?: string;
    date?: string;
    filename?: string;
  };
  neps_details?: {
    status?: string;
    members?: number;
    filename?: string;
  };
  imd_details?: {
    status?: string;
    resolution?: string;
    date?: string;
    filename?: string;
  };
  model_details?: {
    model_id?: string;
    version?: string;
    status?: string;
    architecture?: string;
  };
  last_validation?: string;
  last_imported_dataset?: string;
  active_experiment_dataset?: string;
}

export function useOperationalStatus(pollIntervalMs: number = 35000) {
  const [availability, setAvailability] = useState<OperationalStatusData | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [lastScanTime, setLastScanTime] = useState<string>('');
  const isMountedRef = useRef<boolean>(true);

  const refresh = useCallback(async () => {
    try {
      const [healthData, availData] = await Promise.all([
        fetchHealth().catch(() => null),
        fetchOperationalAvailability().catch(() => null),
      ]);

      if (isMountedRef.current) {
        if (healthData) setHealth(healthData);
        if (availData && availData.data) {
          setAvailability(availData.data);
          const now = new Date();
          const istTime = now.toLocaleTimeString('en-IN', { hour12: false }) + ' IST';
          setLastScanTime(istTime);
        }
        setLoading(false);
      }
    } catch (err) {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    refresh();

    const interval = setInterval(refresh, pollIntervalMs);
    return () => {
      isMountedRef.current = false;
      clearInterval(interval);
    };
  }, [refresh, pollIntervalMs]);

  const dataMode = availability?.overall_mode || health?.data_mode || 'SYNTHETIC_DEMO';

  return {
    availability,
    health,
    dataMode,
    loading,
    lastScanTime: lastScanTime || '23:14:32 IST',
    refresh,
  };
}
