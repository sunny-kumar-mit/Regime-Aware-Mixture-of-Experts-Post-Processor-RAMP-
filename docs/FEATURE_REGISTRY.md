# RAMP Centralized Feature Registry

**Project:** SIH26080 — Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts  
**Organization:** Ministry of Earth Sciences (MoES)  
**Department:** National Centre for Medium Range Weather Forecasting (NCMRWF)  
**Module:** `ml.feature_registry.FeatureAvailabilityRegistry`

---

## 1. Registry Architecture

The Feature Registry acts as the single source of truth for all predictors entering the ML pipeline. It defines canonical variable names, units, physical derivations, and honesty flags for missing data sources.

---

## 2. Canonical Registered Features

| Feature Name | Source | Unit | Dtype | Required | Derivation / Formula | Available |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `raw_nwp_rainfall` | `nwp.tp` | mm | `float32` | Yes | Accumulated surface precipitation over lead window | Yes |
| `lead_time_hours` | `forecast_spec` | hours | `int32` | Yes | $T_{\text{valid}} - T_{\text{init}}$ | Yes |
| `u850` | `nwp.u850` | m/s | `float32` | No | Zonal wind component at 850 hPa | Yes |
| `v850` | `nwp.v850` | m/s | `float32` | No | Meridional wind component at 850 hPa | Yes |
| `wind_speed_850` | `u850, v850` | m/s | `float32` | No | $\sqrt{u_{850}^2 + v_{850}^2}$ | Yes |
| `wind_direction_850` | `u850, v850` | deg | `float32` | No | $(270^\circ - \text{atan2}(v, u) \times 180 / \pi) \pmod{360^\circ}$ | Yes |
| `mslp` | `nwp.mslp` | Pa | `float32` | No | Mean sea level atmospheric pressure | Yes |
| `temperature` | `nwp.t2m` | K | `float32` | No | 2-meter surface air temperature | Yes |
| `relative_humidity` | `nwp.rh` | % | `float32` | No | Relative humidity at near-surface / 850 hPa | Yes |
| `precipitable_water` | `nwp.tcwv` | kg/m² | `float32` | No | Total column integrated water vapour | Yes |
| `cape` | `nwp.cape` | J/kg | `float32` | No | Convective Available Potential Energy | Yes |
| `geopotential_height` | `nwp.gh500`| m | `float32` | No | 500 hPa geopotential height surface | Yes |
| `rainfall_mean_3x3` | `raw_nwp_rainfall` | mm | `float32` | No | $3 \times 3$ grid areal mean on NWP predictor | Yes |
| `rainfall_max_3x3` | `raw_nwp_rainfall` | mm | `float32` | No | $3 \times 3$ grid local max on NWP predictor | Yes |
| `rainfall_std_3x3` | `raw_nwp_rainfall` | mm | `float32` | No | $3 \times 3$ local standard deviation on NWP | Yes |
| `latitude` | `grid.lat` | deg N | `float32` | Yes | Canonical India grid latitude coordinate | Yes |
| `longitude` | `grid.lon` | deg E | `float32` | Yes | Canonical India grid longitude coordinate | Yes |
| `elevation` | `dem.elevation` | m | `float32` | No | SRTM / CartoDEM surface elevation | **No (Not Loaded)** |
| `distance_to_coast` | `gis.coastline` | km | `float32` | No | Shortest geodesic distance to Indian coast | **No (Not Loaded)** |
| `day_of_year_sin` | `forecast_valid_time` | dimless | `float32` | Yes | $\sin(2\pi \times \text{doy} / 365.25)$ | Yes |
| `day_of_year_cos` | `forecast_valid_time` | dimless | `float32` | Yes | $\cos(2\pi \times \text{doy} / 365.25)$ | Yes |
| `valid_hour_sin` | `forecast_valid_time` | dimless | `float32` | Yes | $\sin(2\pi \times \text{hour} / 24.0)$ | Yes |
| `valid_hour_cos` | `forecast_valid_time` | dimless | `float32` | Yes | $\cos(2\pi \times \text{hour} / 24.0)$ | Yes |
| `pre_monsoon` | `month in [3,4,5]` | binary | `int32` | Yes | 1 if month in March–May, else 0 | Yes |
| `monsoon` | `month in [6,7,8,9]` | binary | `int32` | Yes | 1 if month in June–September, else 0 | Yes |
| `post_monsoon` | `month in [10,11,12]` | binary | `int32` | Yes | 1 if month in October–December, else 0 | Yes |
| `winter` | `month in [1,2]` | binary | `int32` | Yes | 1 if month in January–February, else 0 | Yes |
| `ensemble_mean_rainfall` | `gefs.tp` | mm | `float32` | No | Mean across ensemble members | Yes |
| `ensemble_std_rainfall` | `gefs.tp` | mm | `float32` | No | Spread (std) across ensemble members | Yes |
| `ensemble_min_rainfall` | `gefs.tp` | mm | `float32` | No | Minimum across ensemble members | Yes |
| `ensemble_max_rainfall` | `gefs.tp` | mm | `float32` | No | Maximum across ensemble members | Yes |

---

## 3. Honest Availability

Notice that `elevation` and `distance_to_coast` are marked with `available: false` because auxiliary DEM datasets are not yet loaded. The model dataset builder handles missing auxiliary features gracefully by assigning `None`/NaN without fabricating unrealistic values.
