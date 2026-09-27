# RAMP Operational Runbook
**Project:** SIH26080 — Regime-Aware Mixture-of-Experts Post-Processor (RAMP)  
**Organization:** Ministry of Earth Sciences (MoES) / NCMRWF  
**Status:** Standard Operating Procedures (SOP)  

---

## 1. Routine Operational Procedures

### Daily Synoptic Schedule
- **00 UTC Cycle:**
  - Expected NWP Arrival: 04:30 UTC
  - Execution Window: 04:35 – 04:45 UTC
  - Publication Deadline: 05:00 UTC
- **12 UTC Cycle:**
  - Expected NWP Arrival: 16:30 UTC
  - Execution Window: 16:35 – 16:45 UTC
  - Publication Deadline: 17:00 UTC
- **03 UTC Observation Daily Verification:**
  - IMD Gridded Rainfall Arrival: 04:00 UTC
  - Automated Daily Pairing & Verification Report: 05:30 UTC

---

## 2. Incident Response & Troubleshooting

### Incident 1: `REAL_DATA_LOST` / `OPERATIONAL_DEGRADED`
- **Symptom:** Ingestion monitor reports `UNMOUNTED` or `MOUNTED_EMPTY`; alert `REAL_DATA_LOST` fired.
- **Action:**
  1. Inspect network mount: `df -h /mnt/operational/ncmrwf`.
  2. Remount NFS if unmounted: `sudo mount -a`.
  3. Verify file permissions: `ls -la /mnt/operational/ncmrwf`.
  4. Once files reappear, status returns to `AVAILABLE`; operator confirms resumption.

### Incident 2: Exceedance Probability Monotonicity Violation
- **Symptom:** Product publication fails with `Monotonicity violation`.
- **Action:**
  1. Inspect raw predictions in `data/audit/forecasts/`.
  2. The system automatically halts publication to protect downstream meteorological users.
  3. Trigger job retry: `POST /api/production/cycle/{cycle_id}/retry`.

### Incident 3: Emergency Operational Halt (`EMERGENCY_STOP`)
- **Execution:**
  ```bash
  ./deployment/scripts/emergency_stop.sh "Severe input corruption detected in raw NWP feed"
  ```
- **Recovery:**
  - Only Shift Supervisor or Admin can clear emergency stop via Web Console (`/production`) or API.

---

## 3. Data Retention & Backup Policy

- **Audit Logs:** Never delete. Retained permanently under `data/audit/`.
- **Forecast Archives:** Online storage for 90 days; monthly tarballs archived to tape/cold storage.
- **Daily Backups:** Automated nightly tarball created at 01:00 UTC under `data/backups/`.
