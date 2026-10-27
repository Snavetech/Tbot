"""
Bot State Machine with strict validation of transitions and persistence
"""
import enum
from datetime import datetime, timezone
from typing import Optional, Set, Dict


class BotState(str, enum.Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTED_DEMO = "CONNECTED_DEMO"
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    RISK_LOCKED = "RISK_LOCKED"
    ERROR = "ERROR"
    STOPPING = "STOPPING"


# Allowed state transitions graph
VALID_TRANSITIONS: Dict[BotState, Set[BotState]] = {
    BotState.DISCONNECTED: {BotState.CONNECTED_DEMO, BotState.INITIALIZING, BotState.ERROR},
    BotState.CONNECTED_DEMO: {BotState.INITIALIZING, BotState.READY, BotState.DISCONNECTED, BotState.ERROR},
    BotState.INITIALIZING: {BotState.READY, BotState.CONNECTED_DEMO, BotState.ERROR, BotState.DISCONNECTED},
    BotState.READY: {BotState.RUNNING, BotState.PAUSED, BotState.DISCONNECTED, BotState.RISK_LOCKED, BotState.ERROR},
    BotState.RUNNING: {BotState.PAUSED, BotState.RISK_LOCKED, BotState.STOPPING, BotState.ERROR, BotState.DISCONNECTED},
    BotState.PAUSED: {BotState.RUNNING, BotState.STOPPING, BotState.READY, BotState.ERROR, BotState.DISCONNECTED},
    BotState.RISK_LOCKED: {BotState.PAUSED, BotState.READY, BotState.ERROR, BotState.DISCONNECTED},
    BotState.STOPPING: {BotState.READY, BotState.CONNECTED_DEMO, BotState.DISCONNECTED, BotState.ERROR},
    BotState.ERROR: {BotState.INITIALIZING, BotState.DISCONNECTED, BotState.READY, BotState.CONNECTED_DEMO},
}


class InvalidStateTransitionError(Exception):
    """Raised when an illegal state transition is attempted"""
    pass


class BotStateMachine:
    """Manages the runtime state of TradePilot AI"""

    def __init__(self, initial_state: BotState = BotState.DISCONNECTED):
        self._current_state: BotState = initial_state
        self._previous_state: Optional[BotState] = None
        self._last_transition_time: datetime = datetime.now(timezone.utc)
        self._transition_reason: str = "Engine initialized"
        self._error_message: Optional[str] = None
        self._is_evaluating: bool = False  # Lock to prevent overlapping runs

    @property
    def current_state(self) -> BotState:
        return self._current_state

    @property
    def previous_state(self) -> Optional[BotState]:
        return self._previous_state

    @property
    def last_transition_time(self) -> datetime:
        return self._last_transition_time

    @property
    def transition_reason(self) -> str:
        return self._transition_reason

    @property
    def error_message(self) -> Optional[str]:
        return self._error_message

    @property
    def is_evaluating(self) -> bool:
        return self._is_evaluating

    def set_evaluating(self, evaluating: bool):
        self._is_evaluating = evaluating

    def can_transition_to(self, new_state: BotState) -> bool:
        return new_state in VALID_TRANSITIONS.get(self._current_state, set())

    def transition_to(self, new_state: BotState, reason: str, error: Optional[str] = None) -> BotState:
        """
        Transition to a new state if valid.
        Raises InvalidStateTransitionError if transition is not allowed.
        """
        if new_state == self._current_state:
            self._transition_reason = reason
            if error:
                self._error_message = error
            return self._current_state

        if not self.can_transition_to(new_state):
            err_msg = (
                f"Invalid state transition from {self._current_state.value} "
                f"to {new_state.value}. Allowed: {[s.value for s in VALID_TRANSITIONS.get(self._current_state, set())]}"
            )
            raise InvalidStateTransitionError(err_msg)

        self._previous_state = self._current_state
        self._current_state = new_state
        self._last_transition_time = datetime.now(timezone.utc)
        self._transition_reason = reason
        self._error_message = error
        return self._current_state

    def can_enter_trades(self) -> bool:
        """Only RUNNING state permits submitting new entry orders"""
        return self._current_state == BotState.RUNNING

    def can_monitor_positions(self) -> bool:
        """Position monitoring is maintained in RUNNING, PAUSED, and RISK_LOCKED"""
        return self._current_state in {
            BotState.RUNNING,
            BotState.PAUSED,
            BotState.RISK_LOCKED,
            BotState.STOPPING,
        }

    def to_dict(self) -> dict:
        return {
            "current_state": self._current_state.value,
            "previous_state": self._previous_state.value if self._previous_state else None,
            "last_transition_time": self._last_transition_time.isoformat(),
            "transition_reason": self._transition_reason,
            "error_message": self._error_message,
            "can_enter_trades": self.can_enter_trades(),
            "can_monitor_positions": self.can_monitor_positions(),
            "is_evaluating": self._is_evaluating,
        }
