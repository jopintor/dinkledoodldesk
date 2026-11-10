"""Tool executor: the chat calls propose(); the confirm endpoint runs the action."""

from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models import Role, Ticket, ToolCall, User
from app.tools.schemas import TOOLS

# Members may only raise these kinds of tickets, at P3 or lower priority.
MEMBER_CATEGORIES = {"member_app_booking", "network", "other"}
MEMBER_PRIORITIES = {"P3", "P4"}

CONFIRM_TEXT = {"create_ticket": "Create this ticket for the IT Service Desk?"}


class ToolRefused(Exception):
    """The request was not allowed or not valid. str(exc) is safe to show the user."""


def _role_name(db: Session, user: User) -> str | None:
    role = db.get(Role, user.role_id)
    return role.name if role else None


def tool_call_out(tc: ToolCall) -> dict:
    # TODO: match the ToolCall shape in frontend/src/lib/types.ts.
    return {
        "id": tc.id,
        "tool_name": tc.tool_name,
        "status": tc.status,
        "arguments": tc.arguments,
        "confirm_text": CONFIRM_TEXT.get(tc.tool_name, "Go ahead with this action?"),
    }


def propose(db: Session, user: User, tool_name: str, arguments: dict) -> dict:
    """Validate with TOOLS, check role rules, save a tool_calls row as
    'awaiting_confirmation', and return the ToolCall JSON.

    Raises ToolRefused when the request is invalid or not allowed.
    """
    schema = TOOLS.get(tool_name)
    if schema is None:
        raise ToolRefused("I can't do that action.")

    try:
        parsed = schema(**arguments)
    except ValidationError as exc:
        raise ToolRefused("Some of those details aren't valid for this action.") from exc

    if tool_name != "create_ticket":
        raise ToolRefused("That action isn't available yet.")

    role = _role_name(db, user)
    if role in (None, "member"):
        if parsed.category not in MEMBER_CATEGORIES:
            raise ToolRefused("Members can't raise that kind of ticket.")
        if parsed.priority not in MEMBER_PRIORITIES:
            raise ToolRefused("Members can't set that priority.")

    tool_call = ToolCall(
        user_id=user.id,
        tool_name=tool_name,
        status="awaiting_confirmation",
        arguments=parsed.model_dump(mode="json"),
    )
    db.add(tool_call)
    db.commit()
    db.refresh(tool_call)
    return tool_call_out(tool_call)


def ticket_number(ticket_id: int) -> str:
    return f"DD-{ticket_id:06d}"


def run_create_ticket(db: Session, user: User, arguments: dict) -> dict:
    """Save the ticket. The caller commits."""
    ticket = Ticket(
        # Temporary unique value, replaced as soon as the id exists.
        ticket_number=f"PENDING-{uuid4().hex[:12]}",
        summary=arguments["summary"],
        description=arguments["description"],
        category=arguments["category"],
        affected_system=arguments["affected_system"],
        priority=arguments.get("priority") or "P3",
        status="open",
        requester_id=user.id,
        club_code=arguments.get("club_code"),
        jira_key=None,
        jira_sync_status="pending",
    )
    db.add(ticket)
    db.flush()
    ticket.ticket_number = ticket_number(ticket.id)
    return {
        "ticket_number": ticket.ticket_number,
        "jira_key": ticket.jira_key,
        "jira_sync_status": ticket.jira_sync_status,
    }
