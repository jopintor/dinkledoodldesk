import pytest
from pydantic import ValidationError

from app.tools import TOOLS, CreateTicket, ResetPassword

GOOD_TICKET = {
    "summary": "CourtBook shows Court 3 double-booked at 6 PM (Imus)",
    "description": "Two members booked Court 3 for 6 PM. Error text: none.",
    "category": "member_app_booking",
    "affected_system": "courtbook",
}


def test_tools_registry():
    assert TOOLS == {"create_ticket": CreateTicket, "reset_password": ResetPassword}


def test_reset_password_accepts_a_valid_example():
    tool = ResetPassword(system="staffid", reason="forgot_password")
    assert tool.reason == "forgot_password"


def test_reset_password_rejects_a_bad_enum():
    with pytest.raises(ValidationError):
        ResetPassword(system="staffid", reason="because")
    with pytest.raises(ValidationError):
        ResetPassword(system="hubmail", reason="forgot_password")


def test_create_ticket_accepts_a_valid_example_and_defaults():
    tool = CreateTicket(**GOOD_TICKET)
    assert tool.priority == "P3"
    assert tool.club_code is None


def test_create_ticket_accepts_every_optional_field():
    tool = CreateTicket(**GOOD_TICKET, priority="P1", club_code="IMS")
    assert tool.priority == "P1"
    assert tool.club_code == "IMS"


def test_create_ticket_rejects_bad_values():
    for bad in (
        {**GOOD_TICKET, "category": "not-a-category"},
        {**GOOD_TICKET, "affected_system": "toaster"},
        {**GOOD_TICKET, "priority": "P9"},
        {**GOOD_TICKET, "club_code": "XXX"},
        {**GOOD_TICKET, "summary": "s" * 121},
        {**GOOD_TICKET, "description": "d" * 2001},
    ):
        with pytest.raises(ValidationError):
            CreateTicket(**bad)


def test_create_ticket_requires_the_four_required_fields():
    for missing in ("summary", "description", "category", "affected_system"):
        data = {k: v for k, v in GOOD_TICKET.items() if k != missing}
        with pytest.raises(ValidationError):
            CreateTicket(**data)
