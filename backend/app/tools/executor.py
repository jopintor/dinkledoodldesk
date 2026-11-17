"""Tool executor: the chat calls propose(); the confirm endpoint runs the action."""

from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models import Role, Ticket, ToolCall, User
from app.tools.schemas import TOOLS

# Members may only raise these kinds of tickets, at P3 or lower priority.
MEMBER_CATEGORIES = {"member_app_booking", "network", "other"}
MEMBER_PRIORITIES = {"P3", "P4"}

CONFIRM_TEXT = {
    "create_ticket": "Create this ticket for the IT Service Desk?",
    "reset_password": (
        "Send a verification code to your recovery address to reset your staff password?"
    ),
}


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


def _check_create_ticket(role: str | None, parsed) -> None:
    if role in (None, "member"):
        if parsed.category not in MEMBER_CATEGORIES:
            raise ToolRefused("Members can't raise that kind of ticket.")
        if parsed.priority not in MEMBER_PRIORITIES:
            raise ToolRefused("Members can't set that priority.")


def _check_reset_password(role: str | None, user: User) -> None:
    if role in ("agent", "admin"):
        raise ToolRefused("Please contact IT for privileged accounts.")
    if role != "staff":
        raise ToolRefused("Password resets are only available to staff accounts.")
    if not user.directory_username:
        raise ToolRefused("I can't find a staff directory account for you. Please contact IT.")


# The model sometimes writes enum values in another case ("StaffID", "p2", "Pos Payments").
_LOWER_FIELDS = ("system", "reason", "category", "affected_system")
_UPPER_FIELDS = ("priority", "club_code")


def normalise_arguments(arguments: dict) -> dict:
    out = dict(arguments)
    for key in _LOWER_FIELDS:
        if isinstance(out.get(key), str):
            out[key] = out[key].strip().lower().replace(" ", "_").replace("-", "_")
    for key in _UPPER_FIELDS:
        if isinstance(out.get(key), str):
            out[key] = out[key].strip().upper()
    return out


def propose(db: Session, user: User, tool_name: str, arguments: dict) -> dict:
    """Validate with TOOLS, check role rules, save a tool_calls row as
    'awaiting_confirmation', and return the ToolCall JSON.

    Raises ToolRefused when the request is invalid or not allowed.
    """
    schema = TOOLS.get(tool_name)
    if schema is None:
        raise ToolRefused("I can't do that action.")

    try:
        parsed = schema(**normalise_arguments(arguments))
    except ValidationError as exc:
        raise ToolRefused("Some of those details aren't valid for this action.") from exc

    role = _role_name(db, user)
    if tool_name == "create_ticket":
        _check_create_ticket(role, parsed)
    elif tool_name == "reset_password":
        _check_reset_password(role, user)
    else:
        raise ToolRefused("That action isn't available yet.")

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
