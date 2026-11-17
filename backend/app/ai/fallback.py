"""Action cards without the model: used when Gemini is unavailable (degraded mode).

If the user plainly asked for a ticket or a password reset, the chat still offers the
card. reset_password needs no model at all; create_ticket gets plain, honest details from
the user's own words and a few keyword rules (system, branch), priority P3. The user sees
every field on the card before confirming, and the executor checks the role rules again.
"""

import re

from app.ai.routing import asks_for_action

_RESET = re.compile(r"\breset\b[^.?!]{0,30}\bpassword\b|\bpassword\b[^.?!]{0,30}\breset\b", re.I)
_TICKET = re.compile(
    r"\b(create|make|open|file|raise|log|submit|send)\b[^.?!]{0,30}\bticket\b", re.I
)
# The request itself ("..., please create a ticket") is not part of the problem summary.
_REQUEST_TAIL = re.compile(
    r"[\s,.;!-]*\b(can you |could you |pls |please )*(create|make|open|file|raise|log|submit|"
    r"send)\b[^.?!]{0,30}\bticket\b[^.?!]*[.?!]*\s*$",
    re.I,
)

# (pattern, affected_system, category) — first match wins.
_SYSTEMS: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"tappay|card (terminal|payment|reader)|\bterminal\b", re.I), "card_payments",
     "pos_payments"),
    (re.compile(r"dinkpos|\bpos\b|printer|receipt|cash drawer|register", re.I), "dinkpos",
     "pos_payments"),
    (re.compile(r"courtbook", re.I), "courtbook", "member_app_booking"),
    (re.compile(r"member app|\bapp\b|booking", re.I), "member_app", "member_app_booking"),
    (re.compile(r"hubmail|e-?mail", re.I), "hubmail", "accounts_access"),
    (re.compile(r"staff\s?id|password|log ?in|sign ?in|locked", re.I), "staffid",
     "accounts_access"),
    (re.compile(r"vpn|hubconnect", re.I), "hubconnect_vpn", "network"),
    (re.compile(r"guest wi-?fi|member wi-?fi|picklehub-members", re.I), "member_wifi", "network"),
    (re.compile(r"wi-?fi|internet|network", re.I), "staff_wifi", "network"),
    (re.compile(r"rallybracket|tournament", re.I), "rallybracket", "other"),
]  # fmt: skip

_CLUBS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"dasmari|\bdas\b", re.I), "DAS"),
    (re.compile(r"\bimus\b|\bims\b", re.I), "IMS"),
    (re.compile(r"bacoor|\bbac\b", re.I), "BAC"),
    (re.compile(r"general trias|\bgtr\b", re.I), "GTR"),
    (re.compile(r"tagaytay|\btag\b", re.I), "TAG"),
]

MEMBER_CATEGORIES = {"member_app_booking", "network", "other"}
NOTE = "(Logged while the AI assistant was unavailable; details are the user's own words.)"


def ticket_arguments(message: str, role: str) -> dict:
    text = " ".join(message.split())
    summary = _REQUEST_TAIL.sub("", text).strip(" ,.;!-") or text
    system, category = "other", "other"
    for pattern, sys_name, cat in _SYSTEMS:
        if pattern.search(text):
            system, category = sys_name, cat
            break
    if role == "member" and category not in MEMBER_CATEGORIES:
        category = "other"
    club = next((code for pattern, code in _CLUBS if pattern.search(text)), None)
    args = {
        "summary": summary[:120],
        "description": f"{text[:1900]}\n\n{NOTE}",
        "category": category,
        "affected_system": system,
        "priority": "P3",
    }
    if club:
        args["club_code"] = club
    return args


def tool_requests(message: str, role: str, tool_names: tuple[str, ...] | list[str]) -> list[dict]:
    """The card(s) to offer for an explicit request, or [] if the user didn't ask for one."""
    if not tool_names or not asks_for_action(message):
        return []
    if "reset_password" in tool_names and _RESET.search(message):
        return [
            {"name": "reset_password", "args": {"system": "staffid", "reason": "forgot_password"}}
        ]
    if "create_ticket" in tool_names and _TICKET.search(message):
        return [{"name": "create_ticket", "args": ticket_arguments(message, role)}]
    return []
