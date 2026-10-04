"""Initial PostgreSQL and PostGIS Schema for RAMP SIH26080

Revision ID: 001_initial_postgres_postgis
Revises: 
Create Date: 2026-10-04 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

# revision identifiers, used by Alembic.
revision: str = '001_initial_postgres_postgis'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Enable PostGIS Extension (strictly on PostgreSQL)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # 1. datasets
    op.create_table(
        'datasets',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('dataset_id', sa.String(length=128), nullable=False),
        sa.Column('dataset_type', sa.String(length=64), nullable=False),
        sa.Column('source_provider', sa.String(length=64), nullable=False),
        sa.Column('source_model', sa.String(length=64), nullable=True),
        sa.Column('data_mode', sa.String(length=32), nullable=True),
        sa.Column('version', sa.String(length=32), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('native_resolution', sa.String(length=32), nullable=True),
        sa.Column('target_resolution', sa.String(length=32), nullable=True),
        sa.Column('file_count', sa.Integer(), nullable=True),
        sa.Column('total_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('quality_status', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dataset_id')
    )
    op.create_index('ix_datasets_dataset_id', 'datasets', ['dataset_id'], unique=True)

    # 2. file_objects
    op.create_table(
        'file_objects',
        sa.Column('id', sa.String(length=128), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('mime_type', sa.String(length=64), nullable=True),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('dataset_id', sa.String(length=128), nullable=True),
        sa.Column('source_provider', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_file_objects_sha256', 'file_objects', ['sha256'])

    # 3. file_chunks
    op.create_table(
        'file_chunks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('file_id', sa.String(length=128), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('chunk_size', sa.Integer(), nullable=False),
        sa.Column('data', sa.LargeBinary(), nullable=False),
        sa.ForeignKeyConstraint(['file_id'], ['file_objects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('file_id', 'chunk_index', name='uq_file_chunk_index')
    )
    op.create_index('ix_file_chunks_file_id', 'file_chunks', ['file_id'])
    op.create_index('ix_file_chunks_chunk_index', 'file_chunks', ['chunk_index'])

    # 4. forecast_runs
    op.create_table(
        'forecast_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('forecast_run_id', sa.String(length=128), nullable=False),
        sa.Column('cycle', sa.String(length=32), nullable=False),
        sa.Column('initialization_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('valid_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('lead_time_hours', sa.Integer(), nullable=False),
        sa.Column('model_version', sa.String(length=32), nullable=True),
        sa.Column('dataset_version', sa.String(length=32), nullable=True),
        sa.Column('data_mode', sa.String(length=32), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=True),
        sa.Column('runtime_ms', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('provenance', sa.JSON(), nullable=True),
        sa.Column('manifest', sa.JSON(), nullable=True),
        sa.Column('sha256', sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('forecast_run_id')
    )
    op.create_index('ix_forecast_runs_forecast_run_id', 'forecast_runs', ['forecast_run_id'], unique=True)
    op.create_index('ix_forecast_runs_initialization_time', 'forecast_runs', ['initialization_time'])
    op.create_index('ix_forecast_runs_valid_time', 'forecast_runs', ['valid_time'])
    op.create_index('ix_forecast_runs_lead_time_hours', 'forecast_runs', ['lead_time_hours'])
    op.create_index('ix_forecast_runs_status', 'forecast_runs', ['status'])

    # 5. forecast_grid
    op.create_table(
        'forecast_grid',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('forecast_run_id', sa.String(length=128), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('geometry', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326), nullable=True),
        sa.Column('ramp_precip_mm', sa.Float(), nullable=True),
        sa.Column('raw_nwp_mm', sa.Float(), nullable=True),
        sa.Column('correction_mm', sa.Float(), nullable=True),
        sa.Column('neps_mean_mm', sa.Float(), nullable=True),
        sa.Column('neps_spread_mm', sa.Float(), nullable=True),
        sa.Column('imd_observation_mm', sa.Float(), nullable=True),
        sa.Column('error_mm', sa.Float(), nullable=True),
        sa.Column('absolute_error_mm', sa.Float(), nullable=True),
        sa.Column('risk_class', sa.String(length=32), nullable=True),
        sa.Column('regime', sa.String(length=64), nullable=True),
        sa.Column('regime_probability', sa.JSON(), nullable=True),
        sa.Column('extreme_probability', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_forecast_grid_forecast_run_id', 'forecast_grid', ['forecast_run_id'])
    op.create_index('ix_grid_run_lat_lon', 'forecast_grid', ['forecast_run_id', 'latitude', 'longitude'])

    # 6. forecast_districts
    op.create_table(
        'forecast_districts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('district_id', sa.String(length=64), nullable=False),
        sa.Column('district_name', sa.String(length=128), nullable=False),
        sa.Column('state_name', sa.String(length=128), nullable=False),
        sa.Column('geometry', geoalchemy2.types.Geometry(geometry_type='GEOMETRY', srid=4326), nullable=True),
        sa.Column('forecast_run_id', sa.String(length=128), nullable=False),
        sa.Column('mean_rainfall', sa.Float(), nullable=True),
        sa.Column('median_rainfall', sa.Float(), nullable=True),
        sa.Column('maximum_rainfall', sa.Float(), nullable=True),
        sa.Column('p90', sa.Float(), nullable=True),
        sa.Column('p95', sa.Float(), nullable=True),
        sa.Column('p99', sa.Float(), nullable=True),
        sa.Column('risk_class', sa.String(length=32), nullable=True),
        sa.Column('peak_lat', sa.Float(), nullable=True),
        sa.Column('peak_lon', sa.Float(), nullable=True),
        sa.Column('affected_area_km2', sa.Float(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_forecast_districts_forecast_run_id', 'forecast_districts', ['forecast_run_id'])
    op.create_index('ix_forecast_districts_district_id', 'forecast_districts', ['district_id'])

    # 7. forecast_states
    op.create_table(
        'forecast_states',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('state_id', sa.String(length=64), nullable=False),
        sa.Column('state_name', sa.String(length=128), nullable=False),
        sa.Column('geometry', geoalchemy2.types.Geometry(geometry_type='GEOMETRY', srid=4326), nullable=True),
        sa.Column('forecast_run_id', sa.String(length=128), nullable=False),
        sa.Column('mean_rainfall', sa.Float(), nullable=True),
        sa.Column('median_rainfall', sa.Float(), nullable=True),
        sa.Column('maximum_rainfall', sa.Float(), nullable=True),
        sa.Column('p90', sa.Float(), nullable=True),
        sa.Column('p95', sa.Float(), nullable=True),
        sa.Column('p99', sa.Float(), nullable=True),
        sa.Column('risk_class', sa.String(length=32), nullable=True),
        sa.Column('peak_lat', sa.Float(), nullable=True),
        sa.Column('peak_lon', sa.Float(), nullable=True),
        sa.Column('affected_area_km2', sa.Float(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_forecast_states_forecast_run_id', 'forecast_states', ['forecast_run_id'])
    op.create_index('ix_forecast_states_state_id', 'forecast_states', ['state_id'])

    # 8. imd_observations
    op.create_table(
        'imd_observations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('dataset_id', sa.String(length=128), nullable=True),
        sa.Column('observation_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('geometry', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326), nullable=True),
        sa.Column('rainfall_mm', sa.Float(), nullable=False),
        sa.Column('quality_flag', sa.String(length=32), nullable=True),
        sa.Column('source_file_id', sa.String(length=128), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_imd_observations_observation_time', 'imd_observations', ['observation_time'])
    op.create_index('ix_imd_obs_time_lat_lon', 'imd_observations', ['observation_time', 'latitude', 'longitude'])

    # 9. nwp_files
    op.create_table(
        'nwp_files',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('dataset_id', sa.String(length=128), nullable=True),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('model', sa.String(length=64), nullable=False),
        sa.Column('cycle', sa.String(length=32), nullable=False),
        sa.Column('initialization_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('valid_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('lead_time_hours', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_object_id', sa.String(length=128), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('native_resolution', sa.String(length=32), nullable=True),
        sa.Column('variables', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('quality_status', sa.String(length=32), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_nwp_files_file_object_id', 'nwp_files', ['file_object_id'])

    # 10. forecast_provenance
    op.create_table(
        'forecast_provenance',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('forecast_run_id', sa.String(length=128), nullable=False),
        sa.Column('input_file_ids', sa.JSON(), nullable=True),
        sa.Column('input_hashes', sa.JSON(), nullable=True),
        sa.Column('model_version', sa.String(length=32), nullable=True),
        sa.Column('model_hash', sa.String(length=64), nullable=True),
        sa.Column('dataset_version', sa.String(length=32), nullable=True),
        sa.Column('feature_contract', sa.String(length=64), nullable=True),
        sa.Column('target_contract', sa.String(length=64), nullable=True),
        sa.Column('calibration_version', sa.String(length=32), nullable=True),
        sa.Column('software_version', sa.String(length=32), nullable=True),
        sa.Column('git_commit', sa.String(length=64), nullable=True),
        sa.Column('data_mode', sa.String(length=32), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('manifest', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('forecast_run_id')
    )
    op.create_index('ix_forecast_provenance_forecast_run_id', 'forecast_provenance', ['forecast_run_id'], unique=True)

    # 11. audit_events
    op.create_table(
        'audit_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.String(length=128), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('timestamp_utc', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actor_role', sa.String(length=32), nullable=True),
        sa.Column('actor_id', sa.String(length=128), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('sha256_signature', sa.String(length=64), nullable=False),
        sa.Column('previous_hash', sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id')
    )
    op.create_index('ix_audit_events_event_id', 'audit_events', ['event_id'], unique=True)
    op.create_index('ix_audit_events_timestamp_utc', 'audit_events', ['timestamp_utc'])
    op.create_index('ix_audit_events_event_type', 'audit_events', ['event_type'])


def downgrade() -> None:
    op.drop_table('audit_events')
    op.drop_table('forecast_provenance')
    op.drop_table('nwp_files')
    op.drop_table('imd_observations')
    op.drop_table('forecast_states')
    op.drop_table('forecast_districts')
    op.drop_table('forecast_grid')
    op.drop_table('forecast_runs')
    op.drop_table('file_chunks')
    op.drop_table('file_objects')
    op.drop_table('datasets')
