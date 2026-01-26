"""
State Machine for Agent Entity States.

WHAT:
    Manages state transitions for each entity an agent monitors.
    Handles accumulation tracking and trigger eligibility.

WHY:
    Each entity needs independent state tracking:
    - WATCHING: Evaluating condition each cycle
    - ACCUMULATING: Condition met, counting towards threshold
    - TRIGGERED: Actions executed, may enter cooldown
    - COOLDOWN: Waiting before agent can trigger again
    - ERROR: Evaluation failed, needs attention

STATE TRANSITIONS:
    WATCHING → condition=True → ACCUMULATING
    ACCUMULATING → accumulation_complete → TRIGGERED
    TRIGGERED → cooldown configured → COOLDOWN
    TRIGGERED → no cooldown → WATCHING
    COOLDOWN → cooldown_expired → WATCHING
    Any state → evaluation_error → ERROR
    ERROR → manual_resume → WATCHING

REFERENCES:
    - Agent System Implementation Plan (Phase 2: Evaluation Engine)
    - backend/app/models.py (AgentEntityState, AgentStateEnum)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import logging

from ...models import (
    AgentStateEnum,
    AccumulationUnitEnum,
    AccumulationModeEnum,
    TriggerModeEnum,
)

logger = logging.getLogger(__name__)


@dataclass
class AccumulationState:
    """
    Current accumulation state for an entity.

    WHAT: Tracks progress towards trigger threshold
    WHY: Agents need "ROAS > 2 for 3 days" type conditions

    Attributes:
        count: Number of times condition was met
        required: Number required to trigger
        started_at: When accumulation began
        history: Timestamps of condition=True evaluations (for within_window mode)
    """

    count: int = 0
    required: int = 1
    started_at: Optional[datetime] = None
    history: List[datetime] = field(default_factory=list)


@dataclass
class StateTransitionResult:
    """
    Result of a state transition.

    WHAT: Captures state change and reasoning
    WHY: Need full audit trail for each evaluation

    Attributes:
        state_before: State before transition
        state_after: State after transition
        reason: Human-readable explanation
        accumulation_before: Accumulation state before
        accumulation_after: Accumulation state after
        should_trigger: Whether actions should be executed
        trigger_reason: Why trigger decision was made
    """

    state_before: AgentStateEnum
    state_after: AgentStateEnum
    reason: str
    accumulation_before: Dict[str, Any]
    accumulation_after: Dict[str, Any]
    should_trigger: bool
    trigger_reason: str


class AgentStateMachine:
    """
    State machine for agent entity states.

    WHAT: Handles state transitions based on condition evaluation results
    WHY: Centralized logic for accumulation and trigger determination

    Usage:
        machine = AgentStateMachine(config)
        result = machine.process_evaluation(
            current_state=AgentStateEnum.watching,
            condition_met=True,
            accumulation_state=AccumulationState(),
            evaluated_at=datetime.now()
        )
    """

    def __init__(
        self,
        accumulation_required: int = 1,
        accumulation_unit: AccumulationUnitEnum = AccumulationUnitEnum.evaluations,
        accumulation_mode: AccumulationModeEnum = AccumulationModeEnum.consecutive,
        accumulation_window: Optional[int] = None,
        trigger_mode: TriggerModeEnum = TriggerModeEnum.once,
        cooldown_duration_minutes: Optional[int] = None,
        continuous_interval_minutes: Optional[int] = None,
    ):
        """
        Initialize state machine with agent configuration.

        Parameters:
            accumulation_required: How many times condition must be met
            accumulation_unit: What to count (evaluations, hours, days)
            accumulation_mode: consecutive or within_window
            accumulation_window: Window size for within_window mode
            trigger_mode: once, cooldown, or continuous
            cooldown_duration_minutes: Minutes to wait after trigger
            continuous_interval_minutes: Minutes between continuous triggers
        """
        self.accumulation_required = accumulation_required
        self.accumulation_unit = accumulation_unit
        self.accumulation_mode = accumulation_mode
        self.accumulation_window = accumulation_window
        self.trigger_mode = trigger_mode
        self.cooldown_duration_minutes = cooldown_duration_minutes
        self.continuous_interval_minutes = continuous_interval_minutes

    def process_evaluation(
        self,
        current_state: AgentStateEnum,
        condition_met: bool,
        accumulation_state: AccumulationState,
        evaluated_at: datetime,
        last_triggered_at: Optional[datetime] = None,
        next_eligible_trigger_at: Optional[datetime] = None,
    ) -> StateTransitionResult:
        """
        Process an evaluation and determine state transition.

        Parameters:
            current_state: Current entity state
            condition_met: Whether condition evaluated to True
            accumulation_state: Current accumulation tracking
            evaluated_at: When evaluation occurred
            last_triggered_at: When last trigger happened
            next_eligible_trigger_at: When next trigger is allowed

        Returns:
            StateTransitionResult with new state and trigger decision
        """
        # Capture before state
        accumulation_before = {
            "count": accumulation_state.count,
            "required": accumulation_state.required,
            "started_at": accumulation_state.started_at.isoformat() if accumulation_state.started_at else None,
            "history_length": len(accumulation_state.history),
        }

        # Handle based on current state
        if current_state == AgentStateEnum.error:
            # Stay in error until manually reset
            return StateTransitionResult(
                state_before=current_state,
                state_after=AgentStateEnum.error,
                reason="Agent in error state - manual intervention required",
                accumulation_before=accumulation_before,
                accumulation_after=accumulation_before,
                should_trigger=False,
                trigger_reason="Agent in error state",
            )

        if current_state == AgentStateEnum.cooldown:
            # Check if cooldown has expired
            if next_eligible_trigger_at and evaluated_at >= next_eligible_trigger_at:
                # Cooldown expired, transition to watching
                return StateTransitionResult(
                    state_before=current_state,
                    state_after=AgentStateEnum.watching,
                    reason="Cooldown expired, resuming monitoring",
                    accumulation_before=accumulation_before,
                    accumulation_after=self._reset_accumulation(accumulation_state),
                    should_trigger=False,
                    trigger_reason="Cooldown expired",
                )
            else:
                # Still in cooldown
                return StateTransitionResult(
                    state_before=current_state,
                    state_after=AgentStateEnum.cooldown,
                    reason=f"In cooldown until {next_eligible_trigger_at}",
                    accumulation_before=accumulation_before,
                    accumulation_after=accumulation_before,
                    should_trigger=False,
                    trigger_reason="Still in cooldown",
                )

        # Handle WATCHING or ACCUMULATING states
        if condition_met:
            # Update accumulation
            new_accumulation = self._update_accumulation(
                accumulation_state, evaluated_at
            )
            accumulation_after = {
                "count": new_accumulation.count,
                "required": new_accumulation.required,
                "started_at": new_accumulation.started_at.isoformat() if new_accumulation.started_at else None,
                "history_length": len(new_accumulation.history),
            }

            # Check if accumulation threshold is met
            if self._is_accumulation_complete(new_accumulation, evaluated_at):
                # Determine trigger action
                should_trigger = True
                trigger_reason = f"Accumulation complete ({new_accumulation.count}/{self.accumulation_required})"

                # Determine next state
                if self.trigger_mode == TriggerModeEnum.once:
                    # One-time trigger, go to cooldown or watching
                    if self.cooldown_duration_minutes:
                        next_state = AgentStateEnum.cooldown
                        reason = f"Triggered, entering {self.cooldown_duration_minutes}min cooldown"
                    else:
                        next_state = AgentStateEnum.watching
                        reason = "Triggered (one-time), returning to watching"
                        # Reset accumulation for one-time triggers without cooldown
                        accumulation_after = self._reset_accumulation(new_accumulation)

                elif self.trigger_mode == TriggerModeEnum.cooldown:
                    # Trigger, then cooldown
                    next_state = AgentStateEnum.cooldown
                    reason = f"Triggered, entering {self.cooldown_duration_minutes}min cooldown"

                elif self.trigger_mode == TriggerModeEnum.continuous:
                    # Check if enough time has passed since last trigger
                    if last_triggered_at and self.continuous_interval_minutes:
                        time_since_trigger = (evaluated_at - last_triggered_at).total_seconds() / 60
                        if time_since_trigger < self.continuous_interval_minutes:
                            should_trigger = False
                            trigger_reason = f"Continuous mode: {time_since_trigger:.0f}min since last trigger, need {self.continuous_interval_minutes}min"
                            next_state = AgentStateEnum.triggered
                            reason = "Condition met, waiting for continuous interval"
                        else:
                            next_state = AgentStateEnum.triggered
                            reason = "Continuous trigger"
                    else:
                        next_state = AgentStateEnum.triggered
                        reason = "First continuous trigger"
                else:
                    next_state = AgentStateEnum.watching
                    reason = "Unknown trigger mode"

                return StateTransitionResult(
                    state_before=current_state,
                    state_after=next_state,
                    reason=reason,
                    accumulation_before=accumulation_before,
                    accumulation_after=accumulation_after,
                    should_trigger=should_trigger,
                    trigger_reason=trigger_reason,
                )

            else:
                # Still accumulating
                return StateTransitionResult(
                    state_before=current_state,
                    state_after=AgentStateEnum.accumulating,
                    reason=f"Condition met, accumulating ({new_accumulation.count}/{self.accumulation_required})",
                    accumulation_before=accumulation_before,
                    accumulation_after=accumulation_after,
                    should_trigger=False,
                    trigger_reason=f"Accumulating: {new_accumulation.count}/{self.accumulation_required}",
                )

        else:
            # Condition NOT met
            if self.accumulation_mode == AccumulationModeEnum.consecutive:
                # Reset accumulation for consecutive mode
                accumulation_after = self._reset_accumulation(accumulation_state)
                reason = "Condition not met, resetting consecutive accumulation"
            else:
                # Keep history for within_window mode
                accumulation_after = accumulation_before
                reason = "Condition not met (within_window mode preserves history)"

            return StateTransitionResult(
                state_before=current_state,
                state_after=AgentStateEnum.watching,
                reason=reason,
                accumulation_before=accumulation_before,
                accumulation_after=accumulation_after,
                should_trigger=False,
                trigger_reason="Condition not met",
            )

    def _update_accumulation(
        self, state: AccumulationState, evaluated_at: datetime
    ) -> AccumulationState:
        """
        Update accumulation state when condition is met.

        Parameters:
            state: Current accumulation state
            evaluated_at: When evaluation occurred

        Returns:
            Updated accumulation state
        """
        new_state = AccumulationState(
            count=state.count,
            required=self.accumulation_required,
            started_at=state.started_at,
            history=state.history.copy(),
        )

        # Set start time if not set
        if not new_state.started_at:
            new_state.started_at = evaluated_at

        # Update based on unit type
        if self.accumulation_unit == AccumulationUnitEnum.evaluations:
            new_state.count += 1
            new_state.history.append(evaluated_at)

        elif self.accumulation_unit == AccumulationUnitEnum.hours:
            # Count distinct hours
            hour_key = evaluated_at.replace(minute=0, second=0, microsecond=0)
            if not any(h.replace(minute=0, second=0, microsecond=0) == hour_key for h in state.history):
                new_state.count += 1
                new_state.history.append(evaluated_at)

        elif self.accumulation_unit == AccumulationUnitEnum.days:
            # Count distinct days
            day_key = evaluated_at.date()
            if not any(h.date() == day_key for h in state.history):
                new_state.count += 1
                new_state.history.append(evaluated_at)

        # Prune history for within_window mode
        if self.accumulation_mode == AccumulationModeEnum.within_window and self.accumulation_window:
            cutoff = self._get_window_cutoff(evaluated_at)
            new_state.history = [h for h in new_state.history if h >= cutoff]
            new_state.count = len(new_state.history)

        return new_state

    def _is_accumulation_complete(
        self, state: AccumulationState, evaluated_at: datetime
    ) -> bool:
        """
        Check if accumulation threshold is met.

        Parameters:
            state: Current accumulation state
            evaluated_at: When evaluation occurred

        Returns:
            True if accumulation is complete
        """
        if self.accumulation_mode == AccumulationModeEnum.consecutive:
            return state.count >= self.accumulation_required

        elif self.accumulation_mode == AccumulationModeEnum.within_window:
            if not self.accumulation_window:
                return state.count >= self.accumulation_required

            # Count events within window
            cutoff = self._get_window_cutoff(evaluated_at)
            events_in_window = sum(1 for h in state.history if h >= cutoff)
            return events_in_window >= self.accumulation_required

        return state.count >= self.accumulation_required

    def _get_window_cutoff(self, evaluated_at: datetime) -> datetime:
        """
        Get cutoff time for within_window mode.

        Parameters:
            evaluated_at: Current evaluation time

        Returns:
            Cutoff datetime for window
        """
        if not self.accumulation_window:
            return evaluated_at

        if self.accumulation_unit == AccumulationUnitEnum.evaluations:
            # Window is number of evaluations (not time-based)
            return datetime.min.replace(tzinfo=timezone.utc)

        elif self.accumulation_unit == AccumulationUnitEnum.hours:
            return evaluated_at - timedelta(hours=self.accumulation_window)

        elif self.accumulation_unit == AccumulationUnitEnum.days:
            return evaluated_at - timedelta(days=self.accumulation_window)

        return evaluated_at

    def _reset_accumulation(self, state: AccumulationState) -> Dict[str, Any]:
        """
        Reset accumulation state.

        Parameters:
            state: Current state (for reference)

        Returns:
            Dictionary representation of reset state
        """
        return {
            "count": 0,
            "required": self.accumulation_required,
            "started_at": None,
            "history_length": 0,
        }

    def calculate_next_eligible_trigger(
        self, triggered_at: datetime
    ) -> Optional[datetime]:
        """
        Calculate when the next trigger is allowed.

        Parameters:
            triggered_at: When the trigger occurred

        Returns:
            Next eligible trigger time, or None if no cooldown
        """
        if self.trigger_mode == TriggerModeEnum.once:
            # No future triggers
            return None

        elif self.trigger_mode == TriggerModeEnum.cooldown:
            if self.cooldown_duration_minutes:
                return triggered_at + timedelta(minutes=self.cooldown_duration_minutes)
            return None

        elif self.trigger_mode == TriggerModeEnum.continuous:
            if self.continuous_interval_minutes:
                return triggered_at + timedelta(minutes=self.continuous_interval_minutes)
            return None

        return None
