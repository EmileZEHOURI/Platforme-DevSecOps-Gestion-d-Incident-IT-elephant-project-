import pytest
from pydantic import ValidationError

from app.models.enums import IncidentPriority
from app.schemas.incident import IncidentCreate

PAYLOAD = {
    "title": "Incident réseau",
    "description": "Le réseau est indisponible.",
    "category": "ANOMALY",
}


def test_normalizes_text_and_defaults_priority():
    incident = IncidentCreate(
        **{
            **PAYLOAD,
            "title": "  Incident réseau  ",
            "description": "  Le réseau est indisponible.\n",
        }
    )
    assert incident.title == PAYLOAD["title"]
    assert incident.description == PAYLOAD["description"]
    assert incident.priority == IncidentPriority.MEDIUM


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", "     "),
        ("title", "  abc  "),
        ("title", "x" * 151),
        ("description", " " * 10),
        ("description", "x" * 5001),
        ("category", "INVALID"),
        ("priority", "INVALID"),
        ("created_by_id", 999),
        ("status", "CLOSED"),
        ("assigned_to_id", 999),
    ],
)
def test_rejects_invalid_or_server_owned_fields(field, value):
    with pytest.raises(ValidationError):
        IncidentCreate(**{**PAYLOAD, field: value})


@pytest.mark.parametrize("field", ["title", "description", "category"])
def test_requires_fields(field):
    with pytest.raises(ValidationError):
        IncidentCreate(**{k: v for k, v in PAYLOAD.items() if k != field})
