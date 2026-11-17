"""Send a new ticket to n8n WF-01, which creates the Jira issue and answers with its key.

Prototype version of docs/automation.md §3: one synchronous webhook call instead of the
outbox + HMAC callback. If n8n or Jira is down the ticket still exists in DinkDesk with
`jira_sync_status = "failed"`; nothing is retried automatically.
"""

import logging

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Role, Ticket, User

log = logging.getLogger(__name__)

WEBHOOK_PATH = "ticket-created"
TIMEOUT_S = 15

# Tests replace this with an httpx.MockTransport.
transport: httpx.BaseTransport | None = None


def ticket_payload(db: Session, ticket: Ticket) -> dict:
    """`ticket.created` payload (docs/automation.md §3) plus where n8n should file it.

    The Jira site, project and issue type come from .env, so the workflow export holds no
    site-specific values (its only secrets are the two n8n credentials).
    """
    s = get_settings()
    requester = db.get(User, ticket.requester_id)
    role = db.get(Role, requester.role_id) if requester else None
    return {
        "event": "ticket.created",
        "jira": {
            "base_url": s.jira_base_url.rstrip("/"),
            "project_key": s.jira_project_key,
            "issue_type": s.jira_issue_type,
        },
        "data": {
            "ticket_number": ticket.ticket_number,
            "summary": ticket.summary,
            "description": ticket.description or "",
            "category": ticket.category,
            "affected_system": ticket.affected_system,
            "priority": ticket.priority,
            "club_code": ticket.club_code,
            "requester": {
                "display_name": requester.full_name if requester else None,
                "role": role.name if role else None,
                "email": requester.email if requester else None,
            },
            "source": "ai_tool",
        },
    }


def sync_ticket(db: Session, ticket_number: str) -> dict:
    """POST the ticket to n8n and store the Jira key. Returns {jira_key, jira_sync_status}.

    The caller commits.
    """
    ticket = db.scalar(select(Ticket).where(Ticket.ticket_number == ticket_number))
    if ticket is None:
        return {"jira_key": None, "jira_sync_status": "failed"}

    s = get_settings()
    url = f"{s.n8n_webhook_base_url.rstrip('/')}/{WEBHOOK_PATH}"
    headers = {"X-DinkDesk-Token": s.n8n_webhook_token.get_secret_value()}
    try:
        with httpx.Client(timeout=TIMEOUT_S, transport=transport) as client:
            res = client.post(url, json=ticket_payload(db, ticket), headers=headers)
        res.raise_for_status()
        key = (res.json() or {}).get("jira_key")
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("Jira sync failed for %s: %s", ticket_number, type(exc).__name__)
        key = None

    if key:
        ticket.jira_key = str(key)[:30]
        ticket.jira_sync_status = "synced"
    else:
        ticket.jira_sync_status = "failed"
    db.flush()
    return {"jira_key": ticket.jira_key, "jira_sync_status": ticket.jira_sync_status}
