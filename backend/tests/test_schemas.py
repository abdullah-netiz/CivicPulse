import pytest
from app.models import Status
from app.providers.triage.base import Category, Priority
from app.schemas import ComplaintCreate, ComplaintResponse
from datetime import datetime, timezone
from uuid import uuid4


def test_complaint_create_valid():
    model = ComplaintCreate(
        text="Water main leak in the middle of market street",
        location="Sector F-6, Islamabad",
        reporter_contact="0300-1122334"
    )
    assert model.text.startswith("Water main")
    assert model.location == "Sector F-6, Islamabad"
    assert model.reporter_contact == "0300-1122334"


def test_complaint_create_validation_bounds():
    # text min length is 10
    with pytest.raises(Exception):
        ComplaintCreate(text="Short", location="Islamabad")

    # location min length is 3
    with pytest.raises(Exception):
        ComplaintCreate(text="This text is long enough", location="A")


def test_complaint_response_serialization():
    now = datetime.now(timezone.utc)
    cid = uuid4()
    response = ComplaintResponse(
        id=cid,
        text="A valid complaint text for testing schema",
        location="Lahore Cantt",
        reporter_contact=None,
        category=Category.WATER,
        priority=Priority.HIGH,
        status="open",
        ai_summary="Valid complaint summary",
        triaged_by="simulated",
        triage_latency_ms=85,
        created_at=now,
        updated_at=now
    )
    assert response.id == cid
    assert response.category == Category.WATER
    assert response.priority == Priority.HIGH
    assert response.status == "open"
