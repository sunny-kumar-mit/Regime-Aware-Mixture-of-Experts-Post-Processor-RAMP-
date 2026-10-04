"""
Requirement 11 Persistence Verification Test
Tests that a controlled record inserted into PostgreSQL remains persistent,
survives connection manager restart / engine recreation, and is retrievable.
"""
import sys
import os
import uuid
from datetime import datetime, timezone

# Ensure project path is accessible
sys.path.insert(0, ".")
sys.path.insert(0, "./backend/src")

from ramp.storage.connection import DatabaseManager
from ramp.storage.models import ForecastRunModel, SystemStateModel
from ramp.storage.postgres_storage import PostgresStorageProvider

def test_persistence(database_url: str = None):
    print("=== Step 1: Initializing Database Manager ===")
    if database_url:
        mgr = DatabaseManager(database_url=database_url)
    else:
        mgr = DatabaseManager.get_instance()
    mgr.init_schema()
    
    test_run_id = f"TEST_PERSIST_RUN_{uuid.uuid4().hex[:8]}"
    test_state_key = f"test_state_{uuid.uuid4().hex[:8]}"
    
    print(f"=== Step 2: Inserting Controlled Test Record into Database: {test_run_id} ===")
    with mgr.session() as session:
        # Insert test run
        run_record = ForecastRunModel(
            forecast_run_id=test_run_id,
            cycle="20260927_00UTC",
            initialization_time=datetime.now(timezone.utc),
            valid_time=datetime.now(timezone.utc),
            lead_time_hours=24,
            status="SUCCESS",
            data_mode="REAL_OPERATIONAL",
            manifest={"source": "controlled_test_verification", "benchmark": "IMD_NCUM"}
        )
        session.add(run_record)
        
        # Insert test persistent system state
        state_record = SystemStateModel(
            state_key=test_state_key,
            state_json={"status": "ACTIVE", "verified_at": datetime.now(timezone.utc).isoformat()},
            updated_by="persistence_test_suite"
        )
        session.add(state_record)
        session.commit()
    print("Record committed successfully.")
    
    print("=== Step 3: Querying Back via Session ===")
    with mgr.session() as session:
        queried_run = session.query(ForecastRunModel).filter_by(forecast_run_id=test_run_id).first()
        assert queried_run is not None, "Failed to query run record from database!"
        assert queried_run.cycle == "20260927_00UTC"
        print(f"Run Query Success: {queried_run.forecast_run_id}, status={queried_run.status}")
        
        queried_state = session.query(SystemStateModel).filter_by(state_key=test_state_key).first()
        assert queried_state is not None, "Failed to query state record from database!"
        print(f"State Query Success: {queried_state.state_key}, json={queried_state.state_json}")

    print("=== Step 4: Simulating Server/Service Restart (Resetting Singleton & Connection Pool) ===")
    DatabaseManager.reset_instance()
    mgr_restarted = DatabaseManager.get_instance()
    
    print("=== Step 5: Querying Again After Restart Simulation ===")
    if database_url:
        mgr_restarted = DatabaseManager(database_url=database_url)
    with mgr_restarted.session() as session:
        persisted_run = session.query(ForecastRunModel).filter_by(forecast_run_id=test_run_id).first()
        assert persisted_run is not None, "CRITICAL: Record lost after restart simulation!"
        assert persisted_run.forecast_run_id == test_run_id
        print(f"Persisted Run Verified: {persisted_run.forecast_run_id} remains intact!")
        
        # Also verify via DatabaseManager get_state helper
        persisted_state = mgr_restarted.get_state(test_state_key)
        assert persisted_state is not None, "CRITICAL: State lost after restart simulation!"
        assert persisted_state.get("status") == "ACTIVE"
        print(f"Persisted State Verified via get_state: {persisted_state}")

        # Cleanup controlled test records
        session.delete(persisted_run)
        state_row = session.query(SystemStateModel).filter_by(state_key=test_state_key).first()
        if state_row:
            session.delete(state_row)
        session.commit()
        print("Controlled test records cleaned up cleanly.")

    print("\n>>> ALL PERSISTENCE CHECKS PASSED: Data persists across engine and session lifecycles! <<<")

if __name__ == "__main__":
    test_persistence(database_url="sqlite:///data/test_persistence.db")
