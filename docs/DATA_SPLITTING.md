# RAMP Temporal Data Splitting & Event Holdout

**Project:** SIH26080 — Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts  
**Organization:** Ministry of Earth Sciences (MoES)  
**Department:** National Centre for Medium Range Weather Forecasting (NCMRWF)  
**Module:** `ml.dataset.split.ChronologicalSplitter`

---

## 1. Why Random Splitting is Forbidden

In standard tabular benchmarks, shuffling samples randomly across train, validation, and test is common practice.

**In weather post-processing, random splitting is scientifically invalid:**
1. **Synoptic Autocorrelation:** Atmospheric circulation patterns (e.g. monsoon depressions) persist for 3–7 days. If Day 1 is in Train and Day 2 is in Test, the model simply memorizes the synoptic state rather than learning generalizable correction dynamics.
2. **Seasonal Clustering:** Shuffling samples allows models to overfit specific seasonal quirks without testing generalization to unseen monsoon seasons.

Therefore, RAMP enforces **chronological splitting with purge embargo buffers**.

---

## 2. Partitioning Strategies

### 1. Chronological Holdout (Primary Default)
- `TRAIN`: Oldest time window (e.g. 70% of chronological timeline).
- `PURGE BUFFER`: 24-hour embargo gap where all samples are dropped to avoid boundary autocorrelation.
- `VALIDATION`: Middle chronological window (e.g. 15%).
- `PURGE BUFFER`: 24-hour embargo gap.
- `TEST`: Most recent chronological window (e.g. 15%).

### 2. Year-Based Holdout
- Partitions by whole monsoon years (e.g. Train on 2018–2022, Val on 2023, Test on 2024).

### 3. Event-Aware Holdout
- Extreme precipitation events (e.g. episodes $\ge 64.5\text{ mm}$ persisting across multiple days) are grouped into cohesive episodes.
- An entire heavy episode is kept within a single partition, rather than being cleaved across train and validation boundaries.

---

## 3. Split Verification Invariants

Every split execution automatically asserts:
$$\max(T_{\text{train}}) < \min(T_{\text{val}}) \quad \text{and} \quad \max(T_{\text{val}}) < \min(T_{\text{test}})$$
$$\min(T_{\text{val}}) - \max(T_{\text{train}}) \ge \text{purge\_gap\_hours}$$
$$\min(T_{\text{test}}) - \max(T_{\text{val}}) \ge \text{purge\_gap\_hours}$$

Violations trigger immediate execution halts.
