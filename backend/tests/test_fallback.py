"""Action cards offered without the model (Gemini unavailable)."""

import pytest

from app.ai import fallback
from app.tools.schemas import TOOLS

STAFF_TOOLS = ("create_ticket", "reset_password")


def test_reset_request_gets_the_fixed_reset_card():
    out = fallback.tool_requests("Please reset my StaffID password", "staff", STAFF_TOOLS)
    assert out == [
        {"name": "reset_password", "args": {"system": "staffid", "reason": "forgot_password"}}
    ]


def test_ticket_request_uses_the_users_words_and_keywords():
    message = "The printer at Bacoor isn't working, please create a ticket"
    [request] = fallback.tool_requests(message, "staff", STAFF_TOOLS)
    args = request["args"]
    assert request["name"] == "create_ticket"
    assert args["summary"] == "The printer at Bacoor isn't working"
    assert args["affected_system"] == "dinkpos" and args["category"] == "pos_payments"
    assert args["club_code"] == "BAC" and args["priority"] == "P3"
    assert args["description"].startswith(message)
    assert fallback.NOTE in args["description"]
    TOOLS["create_ticket"](**args)  # valid for the executor's schema


def test_members_only_get_categories_they_may_use():
    message = "The card terminal at Imus is broken, can you open a ticket"
    [request] = fallback.tool_requests(message, "member", ("create_ticket",))
    assert request["args"]["category"] == "other"
    assert request["args"]["affected_system"] == "card_payments"


def test_no_branch_or_system_falls_back_to_other():
    [request] = fallback.tool_requests("Please create a ticket", "staff", STAFF_TOOLS)
    args = request["args"]
    assert args["category"] == args["affected_system"] == "other"
    assert "club_code" not in args
    assert args["summary"] == "Please create a ticket"  # nothing else to summarise
    TOOLS["create_ticket"](**args)


@pytest.mark.parametrize(
    ("message", "tools"),
    [
        ("How do I reset my StaffID password?", ()),  # no tools (flagged turn / no role)
        ("The printer at Bacoor is jammed", STAFF_TOOLS),  # no explicit request
        ("Please reset my StaffID password", ("create_ticket",)),  # member: no reset tool
    ],
)
def test_no_card_without_an_explicit_request_and_the_tool(message, tools):
    assert fallback.tool_requests(message, "member", tools) == []


def test_long_messages_fit_the_schema():
    message = "The member app crashes " * 40 + "please create a ticket"
    [request] = fallback.tool_requests(message, "staff", STAFF_TOOLS)
    TOOLS["create_ticket"](**request["args"])
