"""Job state machine and lifecycle management.

Implements the state machine for the updated JobState enum:
IDLE → IMPORTING → ANALYZING → GENERATING_CANDIDATES →
PREVIEW_RENDERING → AWAITING_REVIEW → FINAL_RENDERING → COMPLETED

Any state → FAILED or CANCELLED.
"""

from __future__ import annotations

import logging
from typing import Callable

from cutclipshort.types import JobState

logger = logging.getLogger(__name__)

# ── Valid Transitions ────────────────────────────────────────────────────

_TRANSITIONS: dict[JobState, set[JobState]] = {
    JobState.IDLE: {
        JobState.IMPORTING,
        JobState.GENERATING_CANDIDATES,  # open existing project
    },
    JobState.IMPORTING: {
        JobState.ANALYZING,
        JobState.IDLE,
    },
    JobState.ANALYZING: {
        JobState.GENERATING_CANDIDATES,
    },
    JobState.GENERATING_CANDIDATES: {
        JobState.PREVIEW_RENDERING,
        JobState.GENERATING_CANDIDATES,  # strategy change, reuse analysis
    },
    JobState.PREVIEW_RENDERING: {
        JobState.AWAITING_REVIEW,
    },
    JobState.AWAITING_REVIEW: {
        JobState.PREVIEW_RENDERING,      # re-preview after edit
        JobState.FINAL_RENDERING,        # user accepts, export
        JobState.GENERATING_CANDIDATES,  # change genre/strategy
    },
    JobState.FINAL_RENDERING: {
        JobState.COMPLETED,
    },
    JobState.COMPLETED: {
        JobState.AWAITING_REVIEW,        # modify and re-export
        JobState.FINAL_RENDERING,        # re-export different profile
        JobState.IDLE,                   # close project
    },
    JobState.FAILED: {
        JobState.IDLE,
        JobState.ANALYZING,              # retry from analysis
        JobState.GENERATING_CANDIDATES,  # retry from editorial
        JobState.FINAL_RENDERING,        # retry from render
    },
    JobState.CANCELLED: {
        JobState.IDLE,
    },
}

# Every active state can transition to FAILED and CANCELLED
for _state in JobState:
    if _state not in (JobState.FAILED, JobState.CANCELLED, JobState.IDLE, JobState.COMPLETED):
        _TRANSITIONS[_state].add(JobState.FAILED)
        _TRANSITIONS[_state].add(JobState.CANCELLED)


class JobStateMachine:
    """Manages job state transitions with validation."""

    def __init__(
        self,
        initial_state: JobState = JobState.IDLE,
        on_transition: Callable[[JobState, JobState, str], None] | None = None,
    ) -> None:
        self._state = initial_state
        self._on_transition = on_transition

    @property
    def state(self) -> JobState:
        return self._state

    def can_transition(self, target: JobState) -> bool:
        return target in _TRANSITIONS.get(self._state, set())

    def transition(self, target: JobState, reason: str = "") -> None:
        if not self.can_transition(target):
            valid = sorted(s.value for s in _TRANSITIONS.get(self._state, set()))
            raise ValueError(
                f"Invalid transition: {self._state.value} → {target.value}. "
                f"Valid targets: {valid}"
            )
        previous = self._state
        self._state = target
        logger.info(
            "Job state: %s → %s%s",
            previous.value, target.value,
            f" ({reason})" if reason else "",
        )
        if self._on_transition:
            self._on_transition(previous, target, reason)

    def is_terminal(self) -> bool:
        return self._state in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED)

    def is_active(self) -> bool:
        return self._state in (
            JobState.IMPORTING,
            JobState.ANALYZING,
            JobState.GENERATING_CANDIDATES,
            JobState.PREVIEW_RENDERING,
            JobState.FINAL_RENDERING,
        )

    def is_user_interactive(self) -> bool:
        return self._state == JobState.AWAITING_REVIEW

    def reset(self) -> None:
        self._state = JobState.IDLE
