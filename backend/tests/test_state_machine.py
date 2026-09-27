import pytest
from app.models import Status

# Valid state machine transitions specified in PDF:
# open -> in_progress -> resolved;
# open -> rejected;
# in_progress -> rejected.
# resolved and rejected are terminal.
VALID_TRANSITIONS = {
    Status.OPEN: {Status.IN_PROGRESS, Status.REJECTED},
    Status.IN_PROGRESS: {Status.RESOLVED, Status.REJECTED},
    Status.RESOLVED: set(),
    Status.REJECTED: set(),
}


def is_valid_transition(current: Status, target: Status) -> bool:
    return target in VALID_TRANSITIONS.get(current, set())


def test_valid_transitions():
    assert is_valid_transition(Status.OPEN, Status.IN_PROGRESS) is True
    assert is_valid_transition(Status.OPEN, Status.REJECTED) is True
    assert is_valid_transition(Status.IN_PROGRESS, Status.RESOLVED) is True
    assert is_valid_transition(Status.IN_PROGRESS, Status.REJECTED) is True


def test_invalid_transitions():
    # Cannot move from resolved to anything (terminal)
    assert is_valid_transition(Status.RESOLVED, Status.OPEN) is False
    assert is_valid_transition(Status.RESOLVED, Status.IN_PROGRESS) is False
    assert is_valid_transition(Status.RESOLVED, Status.REJECTED) is False

    # Cannot move from rejected to anything (terminal)
    assert is_valid_transition(Status.REJECTED, Status.OPEN) is False
    assert is_valid_transition(Status.REJECTED, Status.IN_PROGRESS) is False

    # Cannot skip from open straight to resolved without in_progress
    assert is_valid_transition(Status.OPEN, Status.RESOLVED) is False
