# DATA CONTRACTS — RAMP
## Regime-Aware Mixture-of-Experts Post-Processor
**SIH26080 | NCMRWF / Ministry of Earth Sciences**

> All contracts are versioned. Breaking changes increment the major version.
> Contract version: **v1.0.0**

---

## 1. NWP Input Forecast Bundle

### 1.1 xarray Dataset Schema

**Dimensions**

| Dimension | Type | Description |
|-----------|------|-------------|
| `time` | `datetime64[ns]` UTC | Valid time (not init time) |
| `lat` | `float32` | Latitude, degrees North, WGS84 |
| `lon` | `float32` | Longitude, degrees East, WGS84 |
| `pressure_level` | `float32` (optional) | hPa; omit for surface-only |

**Required Variables**

| Variable | Shape | Units | Description |
|----------|-------|-------|-------------|
| `precip_24h` | (time, lat, lon) | mm/24h | Total precipitation accumulation |
| `u850` | (time, lat, lon) | m/s | Zonal wind at 850 hPa |
| `v850` | (time, lat, lon) | m/s | Meridional wind at 850 hPa |
| `u200` | (time, lat, lon) | m/s | Zonal wind at 200 hPa |
| `v200` | (time, lat, lon) | m/s | Meridional wind at 200 hPa |
| `mslp` | (time, lat, lon) | Pa | Mean sea-level pressure |
| `t2m` | (time, lat, lon) | K | 2-metre temperature |
| `q850` | (time, lat, lon) | kg/kg | Specific humidity at 850 hPa |
| `pwat` | (time, lat, lon) | kg/m² | Precipitable water column |

**Optional Variables (improve regime classification)**

| Variable | Shape | Units | Description |
|----------|-------|-------|-------------|
| `cape` | (time, lat, lon) | J/kg | Convective Available Potential Energy |
| `olr` | (time, lat, lon) | W/m² | Outgoing Longwave Radiation |
| `vort850` | (time, lat, lon) | s⁻¹ | Relative vorticity at 850 hPa |
| `rh500` | (time, lat, lon) | % | Relative humidity at 500 hPa |

**Global Attributes (required)**

```python
ds.attrs = {
    "provider":       str,   # "ncum" | "neps" | "gfs" | "gefs" | "synthetic_demo"
    "init_time":      str,   # ISO8601 UTC, e.g. "2026-06-15T00:00:00Z"
    "grid_resolution":float, # degrees, e.g. 0.25
    "lead_hours":     list,  # e.g. [24, 48, 72, 96, 120]
    "data_mode":      str,   # "REAL" | "SYNTHETIC_DEMO"
    "ramp_version":   str,   # e.g. "1.0.0"
    "bbox":           list,  # [lon_min, lat_min, lon_max, lat_max]
                             # India default: [66.5, 6.5, 100.0, 38.5]
}
```

**Coordinate constraints**
- `lat` range: 6.5°N to 38.5°N (India domain)
- `lon` range: 66.5°E to 100.0°E
- Standard grid resolution: 0.25° × 0.25°
- CRS: WGS84 EPSG:4326

---

## 2. IMD Observation Bundle

### 2.1 xarray Dataset Schema

| Variable | Shape | Units | Source |
|----------|-------|-------|--------|
| `obs_precip_24h` | (time, lat, lon) | mm/24h | IMD gridded (0.25°) |
| `obs_qc_flag` | (time, lat, lon) | int8 | 0=good, 1=suspect, 2=missing |

**Global Attributes**

```python
ds.attrs = {
    "source":          "IMD_GRIDDED_RAINFALL",
    "version":         str,   # IMD product version
    "valid_date":      str,   # ISO8601 UTC date
    "data_mode":       str,   # "REAL" | "SYNTHETIC_DEMO"
    "missing_value":   -999.0,
}
```

---

## 3. Feature Vector Contract

### 3.1 Regime Classifier Input Features

All features are computed per grid point per valid_time.

| # | Feature Name | Units | Description |
|---|-------------|-------|-------------|
| 1 | `wind_shear_850_200` | m/s | Vector wind shear magnitude (850–200 hPa) |
| 2 | `u850_anom` | m/s | U850 anomaly vs daily climatology |
| 3 | `v850_anom` | m/s | V850 anomaly vs daily climatology |
| 4 | `mslp_anom` | Pa | MSLP anomaly vs daily climatology |
| 5 | `pwat` | kg/m² | Precipitable water |
| 6 | `pwat_anom` | kg/m² | PWAT anomaly vs climatology |
| 7 | `cape` | J/kg | CAPE (0 if not available) |
| 8 | `vort850` | s⁻¹ | Vorticity at 850 hPa |
| 9 | `olr_anom` | W/m² | OLR anomaly (proxy for convection) |
| 10 | `rh500` | % | Relative humidity at 500 hPa |
| 11 | `hadley_index` | dimensionless | Monsoon Hadley circulation index |
| 12 | `lp_proximity` | km | Distance to nearest low-pressure centre |
| 13 | `orographic_lift` | dimensionless | Windward terrain uplift index |
| 14 | `wd_jet_index` | m/s | Western Disturbance jet stream index |
| 15 | `coastal_dist` | km | Distance to nearest coastline |
| 16 | `dem_elevation` | m | Terrain elevation from DEM |
| 17 | `month_sin` | dimensionless | sin(2π × month/12) — seasonal cycle |
| 18 | `month_cos` | dimensionless | cos(2π × month/12) — seasonal cycle |
| 19 | `day_of_year_sin` | dimensionless | sin(2π × doy/365) |
| 20 | `day_of_year_cos` | dimensionless | cos(2π × doy/365) |
| 21 | `precip_24h_nwp` | mm/24h | Raw NWP precipitation (untouched) |
| 22 | `lat_norm` | dimensionless | Normalised latitude in India domain |
| 23 | `lon_norm` | dimensionless | Normalised longitude in India domain |

All features are `float32`. Missing values: `np.nan` (handled by imputer).

### 3.2 Expert Input Features

Each expert receives:
- All 23 regime features above
- Plus `p_active`, `p_break`, `p_depression`, `p_coastal`, `p_orographic`, `p_wd`, `p_transition`
  (regime probabilities as soft context features)

---

## 4. Regime Probability Vector

### 4.1 Pydantic Schema

```python
class RegimeProbVector(BaseModel):
    """
    Soft regime probability vector.
    Constraint: sum of all fields == 1.0 (within 1e-6 tolerance).
    """
    p_active:               float = Field(ge=0.0, le=1.0)
    p_break:                float = Field(ge=0.0, le=1.0)
    p_depression:           float = Field(ge=0.0, le=1.0)
    p_coastal:              float = Field(ge=0.0, le=1.0)
    p_orographic:           float = Field(ge=0.0, le=1.0)
    p_western_disturbance:  float = Field(ge=0.0, le=1.0)
    p_transition:           float = Field(ge=0.0, le=1.0)

    @model_validator(mode='after')
    def check_sum_to_one(self) -> 'RegimeProbVector':
        total = sum([
            self.p_active, self.p_break, self.p_depression,
            self.p_coastal, self.p_orographic,
            self.p_western_disturbance, self.p_transition,
        ])
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Regime probabilities must sum to 1.0, got {total:.8f}")
        return self
```

### 4.2 Example (as shown in problem statement)

```json
{
  "p_active":              0.20,
  "p_break":               0.05,
  "p_depression":          0.62,
  "p_coastal":             0.03,
  "p_orographic":          0.05,
  "p_western_disturbance": 0.02,
  "p_transition":          0.03
}
```

---

## 5. RAMP Corrected Forecast Output

### 5.1 API Response Schema

```python
class RAMPForecastPoint(BaseModel):
    lat:                float
    lon:                float
    valid_time:         datetime
    data_mode:          Literal["REAL", "SYNTHETIC_DEMO"]
    nwp_rain_mm:        float               # Raw NWP (unchanged)
    ramp_rain_mm:       float               # RAMP corrected
    regime_probs:       RegimeProbVector
    p_heavy:            float = Field(ge=0.0, le=1.0)     # P(R >= 64.5)
    p_very_heavy:       float = Field(ge=0.0, le=1.0)     # P(R >= 115.6)
    p_extreme:          float = Field(ge=0.0, le=1.0)     # P(R >= 204.5)

class RAMPForecastResponse(BaseModel):
    run_id:             str
    provider:           str
    init_time:          datetime
    data_mode:          Literal["REAL", "SYNTHETIC_DEMO"]
    points:             list[RAMPForecastPoint]
    generated_at:       datetime
```

### 5.2 NetCDF Output Variables

| Variable | Units | Description |
|----------|-------|-------------|
| `nwp_rain_mm` | mm/24h | Raw NWP (pass-through) |
| `ramp_rain_mm` | mm/24h | RAMP corrected rainfall |
| `p_active` | [0,1] | Regime probability |
| `p_break` | [0,1] | Regime probability |
| `p_depression` | [0,1] | Regime probability |
| `p_coastal` | [0,1] | Regime probability |
| `p_orographic` | [0,1] | Regime probability |
| `p_western_disturbance` | [0,1] | Regime probability |
| `p_transition` | [0,1] | Regime probability |
| `p_heavy` | [0,1] | P(R >= 64.5 mm) |
| `p_very_heavy` | [0,1] | P(R >= 115.6 mm) |
| `p_extreme` | [0,1] | P(R >= 204.5 mm) |
| `data_mode_flag` | int8 | 0=REAL, 1=SYNTHETIC_DEMO |

---

## 6. District Forecast Output

```python
class DistrictForecast(BaseModel):
    run_id:             str
    valid_time:         datetime
    state_name:         str
    district_name:      str
    district_code:      str                 # LGD/Census code
    nwp_rain_mm:        float               # Area-weighted mean
    ramp_rain_mm:       float               # Area-weighted mean
    p_heavy:            float
    p_very_heavy:       float
    p_extreme:          float
    dominant_regime:    str                 # Highest-probability regime name
    data_mode:          Literal["REAL", "SYNTHETIC_DEMO"]
```

---

## 7. Verification Report Contract

```python
class ThresholdVerification(BaseModel):
    threshold_mm:   Optional[float]         # None for continuous metrics
    rmse:           Optional[float]         # Continuous only
    csi:            Optional[float]         # Categorical
    pod:            Optional[float]         # Categorical
    far:            Optional[float]         # Categorical
    ets:            Optional[float]         # Categorical
    fss:            Optional[float]         # Spatial
    fss_scale_km:   Optional[float]         # Neighbourhood scale used

class ModelVerification(BaseModel):
    model_name:         str                 # raw_nwp | mean_bias | qmap | global_ml | ramp
    valid_time:         datetime
    n_obs:              int                 # Number of observation points used
    thresholds:         list[ThresholdVerification]
    data_mode:          Literal["REAL", "SYNTHETIC_DEMO"]

class VerificationReport(BaseModel):
    run_id:             str
    init_time:          datetime
    computed_at:        datetime
    observation_source: str                 # "IMD_GRIDDED" | "SYNTHETIC_DEMO"
    models:             list[ModelVerification]
    data_mode:          Literal["REAL", "SYNTHETIC_DEMO"]
```

**Rainfall Thresholds for Categorical Verification**

| Label | Threshold |
|-------|-----------|
| Heavy | >= 64.5 mm/24h |
| Very Heavy | >= 115.6 mm/24h |
| Extremely Heavy | >= 204.5 mm/24h |

---

## 8. Data Mode Propagation Rules

| Rule | Description |
|------|-------------|
| R1 | If ANY input has `data_mode=SYNTHETIC_DEMO`, the entire output chain must carry `SYNTHETIC_DEMO` |
| R2 | `SYNTHETIC_DEMO` can never be upgraded to `REAL` in the same pipeline run |
| R3 | Every API response body MUST include `data_mode` at the top level |
| R4 | The frontend MUST display the orange demo banner if `data_mode=SYNTHETIC_DEMO` |
| R5 | Verification reports with `SYNTHETIC_DEMO` must be labelled in any published output |

---

## 9. Supported NWP Providers

| Provider ID | Full Name | Format | Grid | Frequency |
|-------------|-----------|--------|------|-----------|
| `ncum` | NCMRWF Unified Model | NetCDF4 | 0.17° | 6-hourly |
| `neps` | NCMRWF Ensemble Prediction | NetCDF4 | 0.25° | Daily |
| `gfs` | NOAA Global Forecast System | GRIB2 | 0.25° | 6-hourly |
| `gefs` | NOAA Global Ensemble Forecast | GRIB2 | 0.25° | Daily |
| `synthetic_demo` | Synthetic Demo Generator | In-memory | 0.25° | Any |

---

## 10. Phase 3 Training Dataset Contract

### 10.1 Spatio-Temporal Join Invariant
Every training record MUST satisfy:
$$\text{forecast\_valid\_time} = \text{forecast\_initialization\_time} + \text{lead\_time\_hours}$$
Observation target $Y$ matches strictly on `(round(latitude, 2), round(longitude, 2), forecast_valid_time)`.

### 10.2 Canonical Training Sample Contract
```python
class TrainingSample(BaseModel):
    sample_id: str                          # 16-char deterministic SHA-256 hash
    forecast_initialization_time: datetime  # UTC
    forecast_valid_time: datetime           # UTC
    lead_time_hours: int                    # Forecast horizon
    latitude: float                         # 6.5°N - 38.5°N
    longitude: float                        # 66.5°E - 100.5°E
    provider: str
    model: str
    ensemble_member: Optional[str]

    # Predictors (X)
    raw_nwp_rainfall: float                 # mm
    u850: Optional[float]                   # m/s
    v850: Optional[float]                   # m/s
    wind_speed_850: Optional[float]         # sqrt(u^2 + v^2)
    wind_direction_850: Optional[float]     # met convention (0-360 deg)
    mslp: Optional[float]                   # Pa
    temperature: Optional[float]            # K
    relative_humidity: Optional[float]      # %
    precipitable_water: Optional[float]     # kg/m^2
    cape: Optional[float]                   # J/kg
    geopotential_height: Optional[float]    # m
    day_of_year_sin: float
    day_of_year_cos: float
    valid_hour_sin: float
    valid_hour_cos: float
    pre_monsoon: int
    monsoon: int
    post_monsoon: int
    winter: int

    # Targets (Y)
    observed_rainfall_mm: float
    rainfall_occurrence: int                # >= 0.1 mm
    heavy_rainfall: int                     # >= 64.5 mm
    very_heavy_rainfall: int                # >= 115.6 mm
    extremely_heavy_rainfall: int           # >= 204.5 mm
    rainfall_anomaly: Optional[float]       # relative to train climatology
    observation_quality_flag: str           # VALID, VALID_EXTREME, SUSPICIOUS

    # Reserved for Phase 4 (must be None)
    regime_label: Optional[str] = None
    regime_label_source: Optional[str] = None
    regime_label_confidence: Optional[float] = None
```

