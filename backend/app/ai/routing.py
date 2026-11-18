"""Deterministic routing rules that run before retrieval (docs/ai-design.md §3.2, §4).

Only the high-precision regex overrides and the "ambiguous" check live here. The
embedding-exemplar intent classifier (design §4) is a separate task; until it lands,
everything else is routed by retrieval confidence.
"""

import re

from app.ai import templates

GREETING = "greeting"
HUMAN_REQUEST = "human_request"
PRIVACY_REQUEST = "privacy_request"
SECURITY_INCIDENT = "security_incident"
HIGH_PRIORITY = "high_priority"
AMBIGUOUS = "ambiguous"
OUT_OF_SCOPE = "out_of_scope"
TERMINAL_TAMPER = "terminal_tamper"

# Intents that are always escalated, whatever the retrieval confidence (KB-024 §4).
ALWAYS_ESCALATE = {
    HUMAN_REQUEST,
    PRIVACY_REQUEST,
    SECURITY_INCIDENT,
    TERMINAL_TAMPER,
    HIGH_PRIORITY,
}

_RULES: list[tuple[str, re.Pattern[str]]] = [
    (
        GREETING,
        re.compile(
            r"^\s*(hi|hello|hey|good (morning|afternoon|evening)|thanks?( you)?|ty|salamat)"
            r"[\s!.,]*(dinkdesk)?[\s!.]*$",
            re.I,
        ),
    ),
    (
        HUMAN_REQUEST,
        re.compile(
            r"\b(talk|speak|chat)\s+(to|with)\s+(a|an|the|some)?\s*"
            r"(real\s+)?(person|human|agent|someone|technician)\b|\breal person\b|\bhuman agent\b",
            re.I,
        ),
    ),
    (
        PRIVACY_REQUEST,
        re.compile(
            r"\bcctv (footage|recording|video)s?\b|\b(delete|erase|remove|copy of) (all )?my "
            r"(member |personal )?(data|information|account data)\b|\bdata subject\b|"
            r"\b(data|information) (you have |you hold )?about me\b",
            re.I,
        ),
    ),
    (
        # A tampered card terminal is a P1 security incident (KB-027 §3, KB-016). It gets a
        # fixed reply: the model tends to suggest restarting it, which is the wrong advice.
        TERMINAL_TAMPER,
        re.compile(r"\btamper(ed|ing)?\b", re.I),
    ),
    (
        SECURITY_INCIDENT,
        re.compile(
            r"\bphish|\bhacked\b|\bsomeone (else )?(has )?(logged|signed) in(to)?\b|"
            r"\bmalware\b|\bransomware\b|\bvirus\b|\bclicked (a|on a|the) (weird|strange|"
            r"suspicious|bad) link\b|\blost my (work|company) (phone|laptop)\b",
            re.I,
        ),
    ),
    (
        HIGH_PRIORITY,
        re.compile(
            r"\b(can'?t|cannot|unable to) take (any )?(card )?(payments|bookings)\b|"
            r"\b(all|every) (card )?(payments?|terminals?|registers?) (are |is )?"
            r"(down|failing|offline)\b|\bwhole (branch|club) (is )?(down|offline)\b",
            re.I,
        ),
    ),
    (
        # Clearly not PickleHub IT (KB-026 "What DinkDesk can't do"): refunds and fees,
        # equipment and coaching, writing code, personal home devices, weather and small talk.
        # Narrow on purpose: anything that might be IT still goes to retrieval.
        OUT_OF_SCOPE,
        re.compile(
            r"\b(can|could|may) i (get|have|request) (a |my )?(cash |full )?refund\b|"
            r"\b(get|want) my money back\b|"
            r"\b(best|good|which|recommend\w*) [^.?!]{0,25}\bpaddles?\b|"
            r"\bimprove my (game|dinks?|serves?|backhand|forehand|footwork)\b|"
            r"\b(write|code|make|build) (me )?(a |an )?(\w+ )?(script|program|scraper|bot)\b|"
            r"\bscrapes?\b[^.?!]{0,40}\bwebsites?\b|"
            r"\bplaystation\b|\bps[345]\b|\bxbox\b|\bnintendo\b|\bnat type\b|"
            r"\bmy home (router|wi-?fi|internet|network|pc|computer|printer)\b|"
            r"\bweather\b|\bforecast\b|\btell me a joke\b|\brecipe\b",
            re.I,
        ),
    ),
]

# Messages that name a system are specific enough to search for.
_SYSTEM_TERMS = re.compile(
    r"staff\s?id|hubmail|e-?mail|courtbook|member app|\bapp\b|dinkpos|\bpos\b|pin\b|tappay|"
    r"terminal|card|rallybracket|tournament|hubwatch|cctv|vpn|hubconnect|picklehub-|guest|"
    r"printer|receipt|drawer|mfa|authenticator|status page|\bkb-\d+|ticket|court\b",
    re.I,
)
_WORD = re.compile(r"[\w'-]+")
_AMBIGUOUS_MAX_WORDS = 6

_CLARIFY_OPTIONS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"password|log ?in|sign ?in|locked", re.I),
        "your StaffID (HubMail, CourtBook Admin, Wi-Fi, VPN), your DinkPOS PIN, RallyBracket, "
        "or the PickleHub Member App",
    ),
    (
        re.compile(r"wi-?fi|internet|network", re.I),
        "the staff network (PickleHub-Staff) or the member/guest network (PickleHub-Members)",
    ),
    (
        re.compile(r"pay|card|cash", re.I),
        "DinkPOS (the register app) or the TapPay card terminal — and is it one device or the "
        "whole branch",
    ),
    (
        re.compile(r"book", re.I),
        "a booking in the Member App or in CourtBook Admin at the front desk",
    ),
    (
        re.compile(r"access", re.I),
        "which system you need access to (for example CourtBook Admin, DinkPOS, RallyBracket, "
        "HubWatch or the VPN)",
    ),
]


_ACTION_REQUEST = re.compile(
    r"\b(create|make|open|file|raise|log|submit|send)\b[^.?!]{0,30}\bticket\b|"
    r"\breset\b[^.?!]{0,30}\bpassword\b|\bpassword\b[^.?!]{0,30}\breset\b",
    re.I,
)


def asks_for_action(message: str) -> bool:
    """The user explicitly asks for a ticket or a password reset (one of the two tools)."""
    return bool(_ACTION_REQUEST.search(message))


def rule_intent(message: str) -> str | None:
    """First matching override intent, `ambiguous`, or None (let retrieval decide)."""
    for intent, pattern in _RULES:
        if pattern.search(message):
            return intent
    words = _WORD.findall(message)
    if len(words) <= _AMBIGUOUS_MAX_WORDS and not _SYSTEM_TERMS.search(message):
        return AMBIGUOUS
    return None


def clarify_question(message: str) -> str:
    for pattern, options in _CLARIFY_OPTIONS:
        if pattern.search(message):
            return templates.CLARIFY.format(options=options)
    return templates.CLARIFY.format(options=templates.CLARIFY_DEFAULT_OPTIONS)
