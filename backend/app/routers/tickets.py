from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db, not_found, require
from app.models import Conversation, Role, Ticket, User
from app.permissions import has_permission
from app.ratelimit import limiter
from app.utils import decode_cursor, encode_cursor, parse_ticket_ref, ticket_number

router = APIRouter(prefix="/api/v1/tickets", tags=["tickets"])

# TODO: match the allowed values in the API doc.
TicketStatus = Literal["open", "in_progress", "resolved", "closed"]
Priority = Literal["low", "normal", "high", "urgent"]


class TicketCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    description: str | None = None
    priority: Priority = "normal"
    conversation_id: int | None = None


class TicketUpdate(BaseModel):
    subject: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: TicketStatus | None = None
    priority: Priority | None = None
    assigned_to: int | None = None


def ticket_out(t: Ticket) -> dict:
    # TODO: match the response shape in the API doc.
    return {
        "id": t.id,
        "number": ticket_number(t.id),
        "subject": t.subject,
        "description": t.description,
        "status": t.status,
        "priority": t.priority,
        "user_id": t.user_id,
        "assigned_to": t.assigned_to,
        "conversation_id": t.conversation_id,
        "created_at": t.created_at,
    }


def _role_name(db: Session, user: User) -> str | None:
    role = db.get(Role, user.role_id)
    return role.name if role else None


def _can(db: Session, user: User, permission: str) -> bool:
    name = _role_name(db, user)
    return name is not None and has_permission(name, permission)


def _load_visible(db: Session, user: User, ref: str) -> Ticket:
    """Returns the ticket, or 404 if it doesn't exist or isn't the caller's."""
    ticket_id = parse_ticket_ref(ref)
    if ticket_id is None:
        raise not_found()
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise not_found()
    if ticket.user_id != user.id and not _can(db, user, "ticket:read-any"):
        raise not_found()
    return ticket


@router.get("")
@limiter.limit("60/minute")
def list_tickets(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = None,
    status_filter: TicketStatus | None = Query(None, alias="status"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(Ticket).order_by(Ticket.id.desc())

    if not _can(db, user, "ticket:read-any"):
        query = query.where(Ticket.user_id == user.id)
    if status_filter:
        query = query.where(Ticket.status == status_filter)
    if cursor:
        last_id = decode_cursor(cursor)
        if last_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid cursor")
        query = query.where(Ticket.id < last_id)

    rows = db.scalars(query.limit(limit + 1)).all()
    page = rows[:limit]
    next_cursor = encode_cursor(page[-1].id) if len(rows) > limit else None

    return {"items": [ticket_out(t) for t in page], "next_cursor": next_cursor}


@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
def create_ticket(
    request: Request,
    body: TicketCreate,
    user: User = Depends(require("ticket:create")),
    db: Session = Depends(get_db),
):
    if body.conversation_id is not None:
        convo = db.get(Conversation, body.conversation_id)
        if convo is None or convo.user_id != user.id:
            raise not_found()

    ticket = Ticket(
        user_id=user.id,
        conversation_id=body.conversation_id,
        subject=body.subject,
        description=body.description,
        priority=body.priority,
        status="open",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket_out(ticket)


@router.get("/{ticket_ref}")
@limiter.limit("60/minute")
def get_ticket(
    request: Request,
    ticket_ref: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ticket_out(_load_visible(db, user, ticket_ref))


@router.patch("/{ticket_ref}")
@limiter.limit("30/minute")
def update_ticket(
    request: Request,
    ticket_ref: str,
    body: TicketUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Visibility first: someone else's ticket is always 404, never 403.
    ticket = _load_visible(db, user, ticket_ref)

    if not _can(db, user, "ticket:update"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")

    changes = body.model_dump(exclude_unset=True)

    if changes.get("assigned_to") is not None:
        if db.get(User, changes["assigned_to"]) is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Assignee not found")

    for field, value in changes.items():
        setattr(ticket, field, value)

    db.commit()
    db.refresh(ticket)
    return ticket_out(ticket)
