"""
Phase 15 — Operational State Machine
SIH26080 | Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
MoES / NCMRWF

8-State Lifecycle Automaton:
  INITIALIZING         → System startup, loading model registry
  WAITING_FOR_DATA     → Awaiting NWP cycle availability (real or demo)
  DATA_RECEIVED        → NWP data discovered, pre-validation pending
  VALIDATING           → Running 11 validation gates
  VALIDATION_FAILED    → One or more gates failed; operator action required
  READY_FOR_INFERENCE  → All gates passed; inference may proceed
  INFERENCING          → Pipeline is running (lock held)
  PUBLISHING           → Writing forecast products to storage
  PUBLISHED            → Products written, provenance recorded
  ALERT_RAISED         → System alert active; operator must acknowledge
  CYCLE_COMPLETE       → Forecast cycle archived, scheduler may restart

INTEGRITY CONSTRAINT:
  REAL_OPERATIONAL activation requires:
  real data + valid metadata + valid cycle + valid model checksum +
  valid calibration + valid features + valid output + valid provenance.
  The system will NOT fabricate real NCMRWF operational cycles.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


class OperationalState(str, Enum):
    """8-state operational lifecycle automaton for RAMP."""

    INITIALIZING = "INITIALIZING"
    WAITING_FOR_DATA = "WAITING_FOR_DATA"
    DATA_RECEIVED = "DATA_RECEIVED"
    VALIDATING = "VALIDATING"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    READY_FOR_INFERENCE = "READY_FOR_INFERENCE"
    INFERENCING = "INFERENCING"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    ALERT_RAISED = "ALERT_RAISED"
    CYCLE_COMPLETE = "CYCLE_COMPLETE"


# Valid state transitions
_TRANSITIONS: Dict[OperationalState, List[OperationalState]] = {
    OperationalState.INITIALIZING: [
        OperationalState.WAITING_FOR_DATA,
        OperationalState.ALERT_RAISED,
    ],
    OperationalState.WAITING_FOR_DATA: [
        OperationalState.DATA_RECEIVED,
        OperationalState.ALERT_RAISED,
    ],
    OperationalState.DATA_RECEIVED: [
        OperationalState.VALIDATING,
        OperationalState.ALERT_RAISED,
    ],
    OperationalState.VALIDATING: [
        OperationalState.READY_FOR_INFERENCE,
        OperationalState.VALIDATION_FAILED,
        OperationalState.ALERT_RAISED,
    ],
    OperationalState.VALIDATION_FAILED: [
        OperationalState.WAITING_FOR_DATA,
        OperationalState.ALERT_RAISED,
    ],
    OperationalState.READY_FOR_INFERENCE: [
        OperationalState.INFERENCING,
        OperationalState.ALERT_RAISED,
    ],
    OperationalState.INFERENCING: [
        OperationalState.PUBLISHING,
        OperationalState.VALIDATION_FAILED,
        OperationalState.ALERT_RAISED,
    ],
    OperationalState.PUBLISHING: [
        OperationalState.PUBLISHED,
        OperationalState.ALERT_RAISED,
    ],
    OperationalState.PUBLISHED: [
        OperationalState.CYCLE_COMPLETE,
        OperationalState.ALERT_RAISED,
    ],
    OperationalState.ALERT_RAISED: [
        OperationalState.WAITING_FOR_DATA,
        OperationalState.INITIALIZING,
    ],
    OperationalState.CYCLE_COMPLETE: [
        OperationalState.WAITING_FOR_DATA,
        OperationalState.INITIALIZING,
    ],
}


@dataclass
class StateTransitionEvent:
    from_state: str
    to_state: str
    timestamp: str
    reason: str
    triggered_by: str  # SYSTEM | SCHEDULER | OPERATOR | ALERT


class OperationalStateMachine:
    """
    Thread-safe 8-state operational lifecycle automaton.
    All transitions are recorded to the audit log.
    """

    def __init__(self, initial_state: OperationalState = OperationalState.INITIALIZING):
        self._state = initial_state
        self._lock = threading.Lock()
        self._history: List[StateTransitionEvent] = []
        self._listeners: List[Callable[[StateTransitionEvent], None]] = []
        self._cycle_context: Dict[str, Any] = {}
        self._record(
            from_state="BOOT",
            to_state=initial_state.value,
            reason="System bootstrap",
            triggered_by="SYSTEM",
        )

    @property
    def current_state(self) -> OperationalState:
        with self._lock:
            return self._state

    @property
    def state_name(self) -> str:
        return self.current_state.value

    def transition(
        self,
        to_state: OperationalState,
        reason: str = "",
        triggered_by: str = "SYSTEM",
    ) -> bool:
        """
        Attempt a state transition. Returns True if successful, False if invalid.
        Thread-safe.
        """
        with self._lock:
            allowed = _TRANSITIONS.get(self._state, [])
            if to_state not in allowed:
                logger.warning(
                    f"Invalid transition {self._state} -> {to_state} rejected. "
                    f"Allowed: {[s.value for s in allowed]}"
                )
                return False
            event = self._record(
                from_state=self._state.value,
                to_state=to_state.value,
                reason=reason,
                triggered_by=triggered_by,
            )
            self._state = to_state
            for listener in self._listeners:
                try:
                    listener(event)
                except Exception as exc:
                    logger.error(f"Listener error on state change: {exc}")
            return True

    def force_transition(
        self,
        to_state: OperationalState,
        reason: str = "OPERATOR_OVERRIDE",
        triggered_by: str = "OPERATOR",
    ) -> StateTransitionEvent:
        """Force a transition, bypassing the allowed-transitions guard (operator override only)."""
        with self._lock:
            event = self._record(
                from_state=self._state.value,
                to_state=to_state.value,
                reason=reason,
                triggered_by=triggered_by,
            )
            self._state = to_state
        return event

    def set_cycle_context(self, **kwargs: Any) -> None:
        """Store metadata about the active forecast cycle."""
        with self._lock:
            self._cycle_context.update(kwargs)

    def get_cycle_context(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._cycle_context)

    def add_listener(self, fn: Callable[[StateTransitionEvent], None]) -> None:
        self._listeners.append(fn)

    def get_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(e) for e in self._history[-50:]]  # last 50 events

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "current_state": self._state.value,
                "cycle_context": dict(self._cycle_context),
                "transition_count": len(self._history),
                "last_transition": asdict(self._history[-1]) if self._history else None,
            }

    def _record(
        self,
        from_state: str,
        to_state: str,
        reason: str,
        triggered_by: str,
    ) -> StateTransitionEvent:
        event = StateTransitionEvent(
            from_state=from_state,
            to_state=to_state,
            timestamp=datetime.now(timezone.utc).isoformat(),
            reason=reason,
            triggered_by=triggered_by,
        )
        self._history.append(event)
        logger.info(
            f"STATE: {from_state} → {to_state} [{triggered_by}] — {reason}"
        )
        return event
