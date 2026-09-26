# RAMP Feature Engineering Engine

**Project:** SIH26080 — Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts  
**Organization:** Ministry of Earth Sciences (MoES)  
**Department:** National Centre for Medium Range Weather Forecasting (NCMRWF)  
**Module:** `ml.dataset.features.FeatureEngineer`

---

## 1. Overview

The Feature Engineering Engine transforms raw NWP atmospheric model outputs into physically meaningful predictors for regime classification and rainfall calibration.

Every feature adheres to strict physical and scientific rules:
1. Standard meteorological conventions for wind direction.
2. Cyclic encodings for annual and diurnal periodicities.
3. Configurable regional monsoon seasonality indicators.
4. Spatial neighborhood statistics computed strictly from NWP forecasts (never targets).
5. Honest reporting of unavailable auxiliary features (e.g. elevation).
6. Total exclusion of forecast error ($Y - \hat{Y}$) from predictor matrix $X$.

---

## 2. Derived Meteorological Formulations

### Wind Speed Magnitude at 850 hPa
Low-level monsoon winds (the Low-Level Jet or LLJ) are key determinants of moisture advection across the Arabian Sea into Peninsular and Central India.

$$\text{wind\_speed\_850} = \sqrt{u_{850}^2 + v_{850}^2}$$

### Meteorological Wind Direction at 850 hPa
Follows the standard meteorological convention: **the direction FROM which the wind is blowing**, measured in degrees clockwise from true North ($0^\circ$).

$$\theta_{\text{met}} = \left(270^\circ - \text{atan2}(v_{850}, u_{850}) \times \frac{180^\circ}{\pi}\right) \pmod{360^\circ}$$

- **Westerly Wind** ($u > 0, v = 0$): $\theta_{\text{met}} = 270^\circ$ (blowing from West to East).
- **Northerly Wind** ($u = 0, v < 0$): $\theta_{\text{met}} = 0^\circ$ (blowing from North to South).
- **Easterly Wind** ($u < 0, v = 0$): $\theta_{\text{met}} = 90^\circ$ (blowing from East to West).
- **Southerly Wind** ($u = 0, v > 0$): $\theta_{\text{met}} = 180^\circ$ (blowing from South to North).

---

## 3. Cyclic Temporal Encodings

Arbitrary integer dates (e.g. day 1 to 365 or hour 0 to 23) create artificial discontinuities between Dec 31 and Jan 1, or between 23:00 and 00:00. The engine implements cyclic continuous representations:

### Annual Cycle
$$\text{day\_of\_year\_sin} = \sin\left(\frac{2\pi \times \text{day\_of\_year}}{365.25}\right)$$
$$\text{day\_of\_year\_cos} = \cos\left(\frac{2\pi \times \text{day\_of\_year}}{365.25}\right)$$

### Diurnal Cycle
$$\text{valid\_hour\_sin} = \sin\left(\frac{2\pi \times \text{valid\_hour}}{24.0}\right)$$
$$\text{valid\_hour\_cos} = \cos\left(\frac{2\pi \times \text{valid\_hour}}{24.0}\right)$$

Invariant verified in tests:
$$\sin^2(\theta) + \cos^2(\theta) \equiv 1.0$$

---

## 4. Monsoon Seasonality Indicators

Categorized according to standard IMD seasonal classifications:
- `winter`: January – February (months 1, 2)
- `pre_monsoon`: March – May (months 3, 4, 5)
- `monsoon`: June – September (months 6, 7, 8, 9) — primary southwest monsoon
- `post_monsoon`: October – December (months 10, 11, 12) — northeast / retreating monsoon

---

## 5. Spatial Neighborhood Predictors

Rainfall is a spatial phenomenon with spatial displacement errors common in NWP models. When regular grid slices exist, the engine computes $3 \times 3$ window metrics on raw NWP rainfall:
- `rainfall_mean_3x3`: Local areal average precipitation.
- `rainfall_max_3x3`: Local peak convective core indicator.
- `rainfall_std_3x3`: Local spatial variability / gradient.

**Critical Rule:** These statistics are computed strictly on NWP predictors. They are **never** calculated using ground truth observation fields.
