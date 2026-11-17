from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import Role, Ticket, User
from app.permissions import has_permission

router = APIRouter(prefix="/api/v1/tickets", tags=["tickets"])


def ticket_out(t: Ticket) -> dict:
    # The chat side panel reads id, ticket_number, jira_key, summary and status.
    return {
        "id": t.id,
        "ticket_number": t.ticket_number,
        "summary": t.summary,
        "description": t.description,
        "category": t.category,
        "affected_system": t.affected_system,
        "priority": t.priority,
        "status": t.status,
        "requester_id": t.requester_id,
        "club_code": t.club_code,
        "jira_key": t.jira_key,
        "jira_sync_status": t.jira_sync_status,
        "created_at": t.created_at,
    }


@router.get("")
def list_tickets(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = db.get(Role, user.role_id)
    can_see_all = role is not None and has_permission(role.name, "ticket:read-any")

    query = select(Ticket).order_by(Ticket.id.desc())
    if not can_see_all:
        query = query.where(Ticket.requester_id == user.id)

    rows = db.scalars(query.limit(limit)).all()
    return {"items": [ticket_out(t) for t in rows], "next_cursor": None}
