# RAMP Production Deployment Guide
**Project:** SIH26080 — Regime-Aware Mixture-of-Experts Post-Processor (RAMP)  
**Organization:** Ministry of Earth Sciences (MoES) / NCMRWF  
**Status:** Operational Deployment Architecture  

---

## 1. System Requirements & Hardware Sizing

- **Host Operating System:** Red Hat Enterprise Linux 8/9, Rocky Linux 9, or Ubuntu 22.04 LTS.
- **CPU:** 16 vCPUs (Intel Xeon / AMD EPYC recommended for spatial GIS rasters).
- **RAM:** 32 GB minimum (64 GB recommended for full 17,673-cell 23-member NEPS processing).
- **Disk Storage:**
  - High-Speed NVMe for Model Registry and Active Ingestion (`/data/ncmrwf`, `/data/imd`).
  - Network Attached Storage (NFSv4) for Historical Archive (`/data/processed/forecasts`).
- **Network Ports:**
  - `80` / `443`: Public Reverse Proxy (Nginx)
  - `8000`: Backend FastAPI (internal container network only)
  - `5173` / `80`: Frontend React/Vite serving

---

## 2. Directory Layout & Permissions

Ensure the following path structure exists and is owned by `ramp:ramp` (`chmod 750`):

```bash
/opt/ramp/                     # Application root
/mnt/operational/ncmrwf/       # Authoritative NCUM & NEPS input mount
/mnt/operational/imd/          # Authoritative IMD gridded observation mount
/mnt/operational/forecasts/    # Final published forecast products
/var/log/ramp/audit/           # Tamper-evident audit logs (production_audit.jsonl)
/var/log/ramp/logs/            # Application logs
```

---

## 3. Deployment Modes

### A. Containerized (Docker Compose)
```bash
cd deployment/docker
docker compose -f docker-compose.prod.yml up -d --build
```

### B. Systemd Native Host Services
```bash
# Copy systemd units
sudo cp deployment/systemd/*.service /etc/systemd/system/
sudo cp deployment/configuration/production.env.example /etc/ramp/production.env

# Reload and enable
sudo systemctl daemon-reload
sudo systemctl enable --now ramp-backend ramp-scheduler ramp-worker
```

---

## 4. Operational Cutover Checklist (14-Point Gate)

Before transitioning to `REAL_OPERATIONAL_ACTIVE`:
1. Authoritative NCUM directory mounted and non-empty.
2. Authoritative NEPS directory mounted and non-empty.
3. Authoritative IMD observations directory mounted and non-empty.
4. All 15 ingestion and activation gates report `PASS`.
5. Model Registry checksums verified against `model_registry_manifest.json`.
6. Feature schema matches `ramp_features_v1.0.0` (18 canonical variables).
7. Target schema matches `ramp_targets_v1.0.0` (4 IMD thresholds).
8. Inference latency $< 1000$ ms for test cycle.
9. Probability monotonicity verified ($P(\ge 2.5) \ge P(\ge 15.6) \ge P(\ge 64.5) \ge P(\ge 115.6)$).
10. Automated backup manifest created and verified.
11. Security headers and path sanitization active.
12. Health endpoints report `LIVE=UP`, `READY=UP`.
13. Formal Operator Request submitted with operational rationale.
14. Shift Supervisor Approval token signed.
