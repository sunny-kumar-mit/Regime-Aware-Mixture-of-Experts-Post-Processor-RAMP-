# RAMP Documentation Directory
## SIH26080 | MoES - NCMRWF

This directory contains architectural and operational documentation for the Regime-Aware Mixture-of-Experts Post-Processor (RAMP).

### Core Documents

- **[System Architecture](../ARCHITECTURE.md)**: End-to-end design, data pipelines, MoE post-processor formulation, database schema, and API contracts.
- **[Data Contracts](../DATA_CONTRACTS.md)**: Strict schemas for input NWP bundles, 23 atmospheric features, regime probabilities, corrected rainfall fields, extreme threshold calibration, and verification metrics.
- **[Model Card](../MODEL_CARD.md)**: Specifications for the 7-class regime classifier, per-regime LightGBM experts, extreme rainfall calibrator, and baseline benchmarks.
- **[Development Plan](../DEVELOPMENT_PLAN.md)**: Multi-phase engineering roadmap and testing gates.
- **[Implementation Checklist](../TODO.md)**: Detailed phase-by-phase tracker.
