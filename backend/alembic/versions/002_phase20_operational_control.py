"""Phase 20 Operational Control, Cycles & Data Health Schema

Revision ID: 002_phase20_operational_control
Revises: 001_initial_postgres_postgis
Create Date: 2026-10-05 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '002_phase20_operational_control'
down_revision: Union[str, None] = '001_initial_postgres_postgis'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. operations_state
    op.create_table(
        'operations_state',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('current_state', sa.String(length=64), nullable=False, server_default='WAITING_FOR_DATA'),
        sa.Column('data_mode', sa.String(length=32), nullable=False, server_default='SYNTHETIC_DEMO'),
        sa.Column('operational_gate', sa.String(length=32), nullable=False, server_default='BLOCKED'),
        sa.Column('active_cycle_id', sa.String(length=64), nullable=True),
        sa.Column('active_lead_hours', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_by', sa.String(length=128), server_default='SYSTEM'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. operation_events
    op.create_table(
        'operation_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.String(length=64), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('from_state', sa.String(length=64), nullable=False),
        sa.Column('to_state', sa.String(length=64), nullable=False),
        sa.Column('event', sa.String(length=64), nullable=False),
        sa.Column('source', sa.String(length=64), server_default='SYSTEM'),
        sa.Column('cycle_id', sa.String(length=64), nullable=True),
        sa.Column('operator', sa.String(length=128), server_default='SYSTEM'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id')
    )
    op.create_index('ix_operation_events_event_id', 'operation_events', ['event_id'], unique=True)
    op.create_index('ix_operation_events_timestamp', 'operation_events', ['timestamp'])

    # 3. operational_cycles
    op.create_table(
        'operational_cycles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('cycle_id', sa.String(length=64), nullable=False),
        sa.Column('cycle_type', sa.String(length=16), server_default='00Z'),
        sa.Column('initialization_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expected_arrival', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actual_arrival', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='WAITING_FOR_DATA'),
        sa.Column('sla_status', sa.String(length=32), nullable=False, server_default='ON_TIME'),
        sa.Column('delay_minutes', sa.Float(), server_default='0.0'),
        sa.Column('source', sa.String(length=64), server_default='NCMRWF_NCUM'),
        sa.Column('data_mode', sa.String(length=32), server_default='REAL_OPERATIONAL'),
        sa.Column('available_leads', sa.JSON(), nullable=True),
        sa.Column('executed_leads', sa.JSON(), nullable=True),
        sa.Column('published_leads', sa.JSON(), nullable=True),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cycle_id')
    )
    op.create_index('ix_operational_cycles_cycle_id', 'operational_cycles', ['cycle_id'], unique=True)

    # 4. cycle_events
    op.create_table(
        'cycle_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('cycle_id', sa.String(length=64), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='SUCCESS'),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('source', sa.String(length=64), server_default='SYSTEM'),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_cycle_events_cycle_id', 'cycle_events', ['cycle_id'])
    op.create_index('ix_cycle_events_timestamp', 'cycle_events', ['timestamp'])

    # 5. scheduler_state
    op.create_table(
        'scheduler_state',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('scheduler_status', sa.String(length=32), nullable=False, server_default='STOPPED'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_poll_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_poll_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('poll_interval_s', sa.Integer(), server_default='300'),
        sa.Column('total_polls', sa.Integer(), server_default='0'),
        sa.Column('total_jobs', sa.Integer(), server_default='0'),
        sa.Column('successful_jobs', sa.Integer(), server_default='0'),
        sa.Column('failed_jobs', sa.Integer(), server_default='0'),
        sa.Column('success_rate', sa.Float(), server_default='0.0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 6. forecast_jobs
    op.create_table(
        'forecast_jobs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('job_id', sa.String(length=64), nullable=False),
        sa.Column('cycle_id', sa.String(length=64), nullable=False),
        sa.Column('lead_hours', sa.Integer(), nullable=False),
        sa.Column('model_version', sa.String(length=32), server_default='v2.0.0'),
        sa.Column('idempotency_key', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='QUEUED'),
        sa.Column('data_mode', sa.String(length=32), server_default='REAL_OPERATIONAL'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('skip_reason', sa.String(length=255), nullable=True),
        sa.Column('forecast_run_id', sa.String(length=128), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id'),
        sa.UniqueConstraint('idempotency_key')
    )
    op.create_index('ix_forecast_jobs_job_id', 'forecast_jobs', ['job_id'], unique=True)
    op.create_index('ix_forecast_jobs_cycle_id', 'forecast_jobs', ['cycle_id'])
    op.create_index('ix_forecast_jobs_idempotency_key', 'forecast_jobs', ['idempotency_key'], unique=True)

    # 7. alert_rules
    op.create_table(
        'alert_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('rule_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('severity', sa.String(length=32), server_default='WARNING'),
        sa.Column('enabled', sa.Integer(), server_default='1'),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column('evaluation_window', sa.String(length=64), server_default='last_5_jobs'),
        sa.Column('condition_key', sa.String(length=64), nullable=True),
        sa.Column('comparison', sa.String(length=16), server_default='>'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rule_id')
    )
    op.create_index('ix_alert_rules_rule_id', 'alert_rules', ['rule_id'], unique=True)

    # 8. alert_events
    op.create_table(
        'alert_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('alert_id', sa.String(length=64), nullable=False),
        sa.Column('rule_id', sa.String(length=64), nullable=False),
        sa.Column('rule_name', sa.String(length=128), nullable=True),
        sa.Column('severity', sa.String(length=32), server_default='WARNING'),
        sa.Column('cycle_id', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='ACTIVE'),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('acknowledged', sa.Integer(), server_default='0'),
        sa.Column('acknowledged_by', sa.String(length=128), nullable=True),
        sa.Column('resolved', sa.Integer(), server_default='0'),
        sa.Column('resolved_by', sa.String(length=128), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('alert_id')
    )
    op.create_index('ix_alert_events_alert_id', 'alert_events', ['alert_id'], unique=True)
    op.create_index('ix_alert_events_rule_id', 'alert_events', ['rule_id'])
    op.create_index('ix_alert_events_created_at', 'alert_events', ['created_at'])

    # 9. drift_measurements
    op.create_table(
        'drift_measurements',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('feature', sa.String(length=64), nullable=False),
        sa.Column('baseline_count', sa.Integer(), server_default='0'),
        sa.Column('current_count', sa.Integer(), server_default='0'),
        sa.Column('baseline_mean', sa.Float(), nullable=True),
        sa.Column('current_mean', sa.Float(), nullable=True),
        sa.Column('baseline_std', sa.Float(), nullable=True),
        sa.Column('current_std', sa.Float(), nullable=True),
        sa.Column('ks_statistic', sa.Float(), nullable=True),
        sa.Column('p_value', sa.Float(), nullable=True),
        sa.Column('drift_status', sa.String(length=32), server_default='INSUFFICIENT_DATA'),
        sa.Column('data_mode', sa.String(length=32), server_default='REAL_OPERATIONAL'),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_drift_measurements_feature', 'drift_measurements', ['feature'])

    # 10. readiness_runs
    op.create_table(
        'readiness_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(length=64), nullable=False),
        sa.Column('passed_count', sa.Integer(), nullable=False),
        sa.Column('failed_count', sa.Integer(), nullable=False),
        sa.Column('warn_count', sa.Integer(), nullable=False),
        sa.Column('skipped_count', sa.Integer(), nullable=False),
        sa.Column('total_count', sa.Integer(), nullable=False),
        sa.Column('score_pct', sa.Float(), nullable=False),
        sa.Column('overall_status', sa.String(length=32), server_default='NO_GO'),
        sa.Column('gate_real_operational', sa.Integer(), server_default='0'),
        sa.Column('data_mode', sa.String(length=32), server_default='REAL_OPERATIONAL'),
        sa.Column('checks', sa.JSON(), nullable=False),
        sa.Column('category_summary', sa.JSON(), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id')
    )
    op.create_index('ix_readiness_runs_run_id', 'readiness_runs', ['run_id'], unique=True)

    # 11. data_source_health
    op.create_table(
        'data_source_health',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source_id', sa.String(length=64), nullable=False),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('dataset', sa.String(length=64), nullable=False),
        sa.Column('availability', sa.String(length=32), server_default='NOT_AVAILABLE'),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('latest_cycle', sa.String(length=32), nullable=True),
        sa.Column('arrival_delay_minutes', sa.Float(), nullable=True),
        sa.Column('coverage_pct', sa.Float(), server_default='0.0'),
        sa.Column('quality_control', sa.String(length=32), server_default='NOT_AVAILABLE'),
        sa.Column('storage_status', sa.String(length=32), server_default='HEALTHY'),
        sa.Column('record_count', sa.Integer(), server_default='0'),
        sa.Column('total_size_bytes', sa.BigInteger(), server_default='0'),
        sa.Column('checksum', sa.String(length=64), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_id')
    )
    op.create_index('ix_data_source_health_source_id', 'data_source_health', ['source_id'], unique=True)


def downgrade() -> None:
    op.drop_table('data_source_health')
    op.drop_table('readiness_runs')
    op.drop_table('drift_measurements')
    op.drop_table('alert_events')
    op.drop_table('alert_rules')
    op.drop_table('forecast_jobs')
    op.drop_table('scheduler_state')
    op.drop_table('cycle_events')
    op.drop_table('operational_cycles')
    op.drop_table('operation_events')
    op.drop_table('operations_state')
