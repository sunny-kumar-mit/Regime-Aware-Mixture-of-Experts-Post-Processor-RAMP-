-- =============================================================================
-- RAMP — PostgreSQL + PostGIS Canonical Storage Schema (SIH26080)
-- MoES / NCMRWF Operational Production & Development
-- =============================================================================

-- 0. Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. Datasets Catalog
CREATE TABLE IF NOT EXISTS datasets (
    id SERIAL PRIMARY KEY,
    dataset_id VARCHAR(128) UNIQUE NOT NULL,
    dataset_type VARCHAR(64) NOT NULL,
    source_provider VARCHAR(64) NOT NULL,
    source_model VARCHAR(64),
    data_mode VARCHAR(32) DEFAULT 'REAL_OPERATIONAL',
    version VARCHAR(32) DEFAULT 'v1.0',
    description TEXT,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    native_resolution VARCHAR(32) DEFAULT '0.12°',
    target_resolution VARCHAR(32) DEFAULT '0.25°',
    file_count INT DEFAULT 0,
    total_size_bytes BIGINT DEFAULT 0,
    quality_status VARCHAR(32) DEFAULT 'VALIDATED',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS ix_datasets_dataset_id ON datasets(dataset_id);

-- 2. File Objects (Metadata for raw meteorological binary payloads)
CREATE TABLE IF NOT EXISTS file_objects (
    id VARCHAR(128) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(64) DEFAULT 'application/octet-stream',
    size_bytes BIGINT NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    dataset_id VARCHAR(128),
    source_provider VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS ix_file_objects_sha256 ON file_objects(sha256);
CREATE INDEX IF NOT EXISTS ix_file_objects_dataset_id ON file_objects(dataset_id);

-- 3. File Chunks (Chunked binary data segments, replaces MinIO)
CREATE TABLE IF NOT EXISTS file_chunks (
    id BIGSERIAL PRIMARY KEY,
    file_id VARCHAR(128) REFERENCES file_objects(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    chunk_size INT NOT NULL,
    data BYTEA NOT NULL,
    CONSTRAINT uq_file_chunk_index UNIQUE (file_id, chunk_index)
);
CREATE INDEX IF NOT EXISTS ix_file_chunks_file_id ON file_chunks(file_id);
CREATE INDEX IF NOT EXISTS ix_file_chunks_chunk_index ON file_chunks(chunk_index);

-- 4. Forecast Runs
CREATE TABLE IF NOT EXISTS forecast_runs (
    id SERIAL PRIMARY KEY,
    forecast_run_id VARCHAR(128) UNIQUE NOT NULL,
    cycle VARCHAR(32) NOT NULL,
    initialization_time TIMESTAMPTZ NOT NULL,
    valid_time TIMESTAMPTZ NOT NULL,
    lead_time_hours INT NOT NULL,
    model_version VARCHAR(32) DEFAULT 'v2.0.0',
    dataset_version VARCHAR(32) DEFAULT 'v1.8',
    data_mode VARCHAR(32) DEFAULT 'REAL_OPERATIONAL',
    status VARCHAR(32) DEFAULT 'SUCCESS',
    runtime_ms DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    provenance JSONB DEFAULT '{}'::jsonb,
    manifest JSONB DEFAULT '{}'::jsonb,
    sha256 VARCHAR(64)
);
CREATE INDEX IF NOT EXISTS ix_forecast_runs_run_id ON forecast_runs(forecast_run_id);
CREATE INDEX IF NOT EXISTS ix_forecast_runs_init_time ON forecast_runs(initialization_time);
CREATE INDEX IF NOT EXISTS ix_forecast_runs_valid_time ON forecast_runs(valid_time);
CREATE INDEX IF NOT EXISTS ix_forecast_runs_lead ON forecast_runs(lead_time_hours);
CREATE INDEX IF NOT EXISTS ix_forecast_runs_status ON forecast_runs(status);

-- 5. Forecast Grid (Canonical 0.25° Grid Cells with PostGIS Point geometry)
CREATE TABLE IF NOT EXISTS forecast_grid (
    id BIGSERIAL PRIMARY KEY,
    forecast_run_id VARCHAR(128) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    geometry GEOMETRY(Point, 4326),
    ramp_precip_mm DOUBLE PRECISION DEFAULT 0.0,
    raw_nwp_mm DOUBLE PRECISION DEFAULT 0.0,
    correction_mm DOUBLE PRECISION DEFAULT 0.0,
    neps_mean_mm DOUBLE PRECISION,
    neps_spread_mm DOUBLE PRECISION,
    imd_observation_mm DOUBLE PRECISION,
    error_mm DOUBLE PRECISION,
    absolute_error_mm DOUBLE PRECISION,
    risk_class VARCHAR(32) DEFAULT 'LIGHT',
    regime VARCHAR(64) DEFAULT 'active_monsoon',
    regime_probability JSONB DEFAULT '{}'::jsonb,
    extreme_probability JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS ix_forecast_grid_run_id ON forecast_grid(forecast_run_id);
CREATE INDEX IF NOT EXISTS ix_forecast_grid_geom ON forecast_grid USING GIST(geometry);
CREATE INDEX IF NOT EXISTS ix_forecast_grid_coords ON forecast_grid(forecast_run_id, latitude, longitude);

-- 6. Spatial Products: Districts (PostGIS Geometry)
CREATE TABLE IF NOT EXISTS forecast_districts (
    id SERIAL PRIMARY KEY,
    district_id VARCHAR(64) NOT NULL,
    district_name VARCHAR(128) NOT NULL,
    state_name VARCHAR(128) NOT NULL,
    geometry GEOMETRY(GEOMETRY, 4326),
    forecast_run_id VARCHAR(128) NOT NULL,
    mean_rainfall DOUBLE PRECISION DEFAULT 0.0,
    median_rainfall DOUBLE PRECISION DEFAULT 0.0,
    maximum_rainfall DOUBLE PRECISION DEFAULT 0.0,
    p90 DOUBLE PRECISION DEFAULT 0.0,
    p95 DOUBLE PRECISION DEFAULT 0.0,
    p99 DOUBLE PRECISION DEFAULT 0.0,
    risk_class VARCHAR(32) DEFAULT 'LIGHT',
    peak_lat DOUBLE PRECISION,
    peak_lon DOUBLE PRECISION,
    affected_area_km2 DOUBLE PRECISION DEFAULT 0.0,
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS ix_forecast_districts_run_id ON forecast_districts(forecast_run_id);
CREATE INDEX IF NOT EXISTS ix_forecast_districts_geom ON forecast_districts USING GIST(geometry);

-- 7. Spatial Products: States (PostGIS Geometry)
CREATE TABLE IF NOT EXISTS forecast_states (
    id SERIAL PRIMARY KEY,
    state_id VARCHAR(64) NOT NULL,
    state_name VARCHAR(128) NOT NULL,
    geometry GEOMETRY(GEOMETRY, 4326),
    forecast_run_id VARCHAR(128) NOT NULL,
    mean_rainfall DOUBLE PRECISION DEFAULT 0.0,
    median_rainfall DOUBLE PRECISION DEFAULT 0.0,
    maximum_rainfall DOUBLE PRECISION DEFAULT 0.0,
    p90 DOUBLE PRECISION DEFAULT 0.0,
    p95 DOUBLE PRECISION DEFAULT 0.0,
    p99 DOUBLE PRECISION DEFAULT 0.0,
    risk_class VARCHAR(32) DEFAULT 'LIGHT',
    peak_lat DOUBLE PRECISION,
    peak_lon DOUBLE PRECISION,
    affected_area_km2 DOUBLE PRECISION DEFAULT 0.0,
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS ix_forecast_states_run_id ON forecast_states(forecast_run_id);
CREATE INDEX IF NOT EXISTS ix_forecast_states_geom ON forecast_states USING GIST(geometry);

-- 8. Observations: IMD 0.25° Gridded Ground Truth
CREATE TABLE IF NOT EXISTS imd_observations (
    id BIGSERIAL PRIMARY KEY,
    dataset_id VARCHAR(128),
    observation_time TIMESTAMPTZ NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    geometry GEOMETRY(Point, 4326),
    rainfall_mm DOUBLE PRECISION NOT NULL,
    quality_flag VARCHAR(32) DEFAULT 'VALID',
    source_file_id VARCHAR(128),
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS ix_imd_obs_time ON imd_observations(observation_time);
CREATE INDEX IF NOT EXISTS ix_imd_obs_geom ON imd_observations USING GIST(geometry);
CREATE INDEX IF NOT EXISTS ix_imd_obs_time_coords ON imd_observations(observation_time, latitude, longitude);

-- 9. NWP Inputs Catalog
CREATE TABLE IF NOT EXISTS nwp_files (
    id SERIAL PRIMARY KEY,
    dataset_id VARCHAR(128),
    provider VARCHAR(64) NOT NULL,
    model VARCHAR(64) NOT NULL,
    cycle VARCHAR(32) NOT NULL,
    initialization_time TIMESTAMPTZ NOT NULL,
    valid_time TIMESTAMPTZ NOT NULL,
    lead_time_hours INT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_object_id VARCHAR(128) NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    native_resolution VARCHAR(32) DEFAULT '0.12°',
    variables JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    quality_status VARCHAR(32) DEFAULT 'VALIDATED'
);
CREATE INDEX IF NOT EXISTS ix_nwp_files_file_object_id ON nwp_files(file_object_id);
CREATE INDEX IF NOT EXISTS ix_nwp_files_cycle_lead ON nwp_files(cycle, lead_time_hours);

-- 10. Forecast Provenance (Immutable Execution Manifests)
CREATE TABLE IF NOT EXISTS forecast_provenance (
    id SERIAL PRIMARY KEY,
    forecast_run_id VARCHAR(128) UNIQUE NOT NULL,
    input_file_ids JSONB DEFAULT '[]'::jsonb,
    input_hashes JSONB DEFAULT '{}'::jsonb,
    model_version VARCHAR(32) DEFAULT 'v2.0.0',
    model_hash VARCHAR(64),
    dataset_version VARCHAR(32) DEFAULT 'v1.8',
    feature_contract VARCHAR(64) DEFAULT 'ramp_features_v1.0.0',
    target_contract VARCHAR(64) DEFAULT 'ramp_targets_v1.0.0',
    calibration_version VARCHAR(32) DEFAULT 'v1.0',
    software_version VARCHAR(32) DEFAULT '2.0.0',
    git_commit VARCHAR(64),
    data_mode VARCHAR(32) DEFAULT 'REAL_OPERATIONAL',
    generated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    manifest JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS ix_forecast_provenance_run_id ON forecast_provenance(forecast_run_id);

-- 11. Audit Events (Append-Only Cryptographic Chain)
CREATE TABLE IF NOT EXISTS audit_events (
    id BIGSERIAL PRIMARY KEY,
    event_id VARCHAR(128) UNIQUE NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    timestamp_utc TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    actor_role VARCHAR(32) DEFAULT 'SYSTEM',
    actor_id VARCHAR(128) DEFAULT 'RAMP_DAEMON',
    details JSONB DEFAULT '{}'::jsonb,
    sha256_signature VARCHAR(64) NOT NULL,
    previous_hash VARCHAR(64) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_audit_events_event_id ON audit_events(event_id);
CREATE INDEX IF NOT EXISTS ix_audit_events_time ON audit_events(timestamp_utc);
CREATE INDEX IF NOT EXISTS ix_audit_events_type ON audit_events(event_type);
