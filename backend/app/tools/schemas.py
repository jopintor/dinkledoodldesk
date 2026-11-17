"""Tool contracts the LLM can call (docs/ai-design.md section 6)."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class ResetReason(StrEnum):
    forgot_password = "forgot_password"  # noqa: S105
    expired_or_locked = "expired_or_locked"
    suspected_compromise = "suspected_compromise"
    other = "other"


class Category(StrEnum):
    accounts_access = "accounts_access"
    access_request = "access_request"
    network = "network"
    pos_payments = "pos_payments"
    member_app_booking = "member_app_booking"
    security = "security"
    privacy = "privacy"
    other = "other"


class AffectedSystem(StrEnum):
    staffid = "staffid"
    hubmail = "hubmail"
    courtbook = "courtbook"
    member_app = "member_app"
    dinkpos = "dinkpos"
    card_payments = "card_payments"
    rallybracket = "rallybracket"
    hubwatch = "hubwatch"
    hubconnect_vpn = "hubconnect_vpn"
    staff_wifi = "staff_wifi"
    member_wifi = "member_wifi"
    other = "other"


class Priority(StrEnum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class ClubCode(StrEnum):
    DAS = "DAS"
    IMS = "IMS"
    BAC = "BAC"
    GTR = "GTR"
    TAG = "TAG"


class ResetPassword(BaseModel):
    """Reset a staff member's password."""

    system: Literal["staffid"]
    reason: ResetReason


class CreateTicket(BaseModel):
    """Create an IT Service Desk ticket."""

    summary: str = Field(max_length=120)
    description: str = Field(max_length=2000)
    category: Category
    affected_system: AffectedSystem
    priority: Priority = Priority.P3
    club_code: ClubCode | None = None


TOOLS = {"create_ticket": CreateTicket, "reset_password": ResetPassword}
