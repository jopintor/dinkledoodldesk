from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db, not_found
from app.models import ToolCall, User
from app.ratelimit import limiter
from app.tools.directory import DirectoryClient, get_directory
from app.tools.executor import run_create_ticket, tool_call_out
from app.tools.jira_sync import sync_ticket
from app.tools.reset import TryAgain, finish_reset, public_result, start_reset

router = APIRouter(prefix="/api/v1/tool-calls", tags=["tool-calls"])


class VerifyBody(BaseModel):
    otp: str = Field(pattern=r"^\d{6}$")


def _owned(db: Session, user: User, tool_call_id: int) -> ToolCall:
    """Someone else's tool call looks exactly like one that doesn't exist (404)."""
    tool_call = db.get(ToolCall, tool_call_id)
    if tool_call is None or tool_call.user_id != user.id:
        raise not_found()
    return tool_call


def _response(tool_call: ToolCall, message: str) -> dict:
    """`ToolCall` in frontend/src/lib/types.ts. Internal `_` keys are never returned."""
    result = public_result(tool_call.result)
    return {**tool_call_out(tool_call), "result": result, "message": message}


def _confirm_ticket(db: Session, user: User, tool_call: ToolCall) -> dict:
    try:
        result = run_create_ticket(db, user, tool_call.arguments)
        tool_call.status = "succeeded"
        tool_call.result = result
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        tool_call = db.get(ToolCall, tool_call.id)
        tool_call.status = "failed"
        tool_call.result = {"error": "Could not save the ticket."}
        db.commit()
        return _response(tool_call, "Sorry, I couldn't create the ticket.")

    # Hand the ticket to n8n for Jira (best effort; the ticket exists either way).
    synced = sync_ticket(db, result["ticket_number"])
    tool_call.result = {**result, **synced}
    db.commit()
    jira = f" (Jira {synced['jira_key']})" if synced.get("jira_key") else ""
    return _response(
        tool_call,
        f"Ticket {result['ticket_number']}{jira} created. The IT team will follow up; "
        "you can track it under My tickets.",
    )


@router.post("/{tool_call_id}/confirm")
def confirm_tool_call(
    tool_call_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    directory: DirectoryClient = Depends(get_directory),
):
    tool_call = _owned(db, user, tool_call_id)
    if tool_call.status != "awaiting_confirmation":
        raise HTTPException(status.HTTP_409_CONFLICT, "This action was already handled.")

    if tool_call.tool_name == "create_ticket":
        return _confirm_ticket(db, user, tool_call)
    if tool_call.tool_name == "reset_password":
        try:
            message = start_reset(db, user, tool_call, directory)
        except TryAgain as exc:
            raise HTTPException(exc.status, str(exc)) from exc
        return _response(tool_call, message)
    raise HTTPException(status.HTTP_409_CONFLICT, "That action isn't available yet.")


@router.post("/{tool_call_id}/verify")
@limiter.limit("5/10minutes")
def verify_tool_call(
    request: Request,
    tool_call_id: int,
    body: VerifyBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    directory: DirectoryClient = Depends(get_directory),
):
    """The code goes straight to the directory; it never reaches the chat or the model."""
    tool_call = _owned(db, user, tool_call_id)
    if tool_call.tool_name != "reset_password" or tool_call.status != "awaiting_verification":
        raise HTTPException(status.HTTP_409_CONFLICT, "This action isn't waiting for a code.")
    try:
        message = finish_reset(db, user, tool_call, body.otp, directory)
    except TryAgain as exc:
        raise HTTPException(exc.status, str(exc)) from exc
    return _response(tool_call, message)


@router.post("/{tool_call_id}/cancel")
def cancel_tool_call(
    tool_call_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tool_call = _owned(db, user, tool_call_id)
    if tool_call.status not in ("awaiting_confirmation", "awaiting_verification"):
        raise HTTPException(status.HTTP_409_CONFLICT, "This action was already handled.")

    tool_call.status = "cancelled"
    db.commit()
    return _response(tool_call, "Okay, I didn't change anything.")
