"""Fixed replies that never call the LLM (docs/ai-design.md §8). UI copy is reviewed here."""

GREETING = (
    "Hi! I'm DinkDesk, PickleHub's IT helpdesk. Tell me what's not working — for example "
    "StaffID sign-in, Wi-Fi, DinkPOS or the Member App — and I'll help."
)

LOW_CONFIDENCE = (
    "I don't have a guide that covers this. I can create a ticket for the IT Service Desk "
    "or connect you to an IT agent."
)

CLARIFY = "Can you tell me a bit more so I find the right guide? Which system is it — {options}?"

CLARIFY_DEFAULT_OPTIONS = (
    "your StaffID / HubMail, CourtBook Admin, DinkPOS, a card terminal, the Member App, "
    "or club Wi-Fi"
)

HUMAN_REQUEST = (
    "Sure — I'll connect you to an IT Service Desk agent. They'll see this conversation, so "
    "you won't need to repeat yourself."
)

PRIVACY_REQUEST = (
    "Requests about personal data or CCTV footage go to PickleHub's Data Protection Officer "
    "and IT, not through me. I'm passing this to an IT agent who will start that process."
)

SECURITY_ESCALATION = (
    "This sounds like a possible security incident, so I'm passing it to an IT agent now. "
    "Don't click any more links or enter your password anywhere until they contact you."
)

DEGRADED_INTRO = (
    "I couldn't write a full answer right now — here are the most relevant guides. "
    "Want me to open a ticket?"
)

REFUSE_INJECTION = (
    "I can't help with that. I can answer PickleHub IT questions or reset your own StaffID "
    "password."
)

REFUSE_LEAK = (
    "I can't share passwords, one-time codes, keys or my internal instructions — not even "
    "for an audit. Temporary passwords only ever go to the account owner's recovery email. "
    "Is there an IT problem I can help you with?"
)

REFUSE_PERSONAL_DATA = (
    "I can't share other people's personal information, like their phone number or email. "
    "The front desk can help you contact them or find another option."
)

NOT_INDEXED = (
    "My knowledge base isn't available right now, so I can't look this up. I can create a "
    "ticket for the IT Service Desk or connect you to an IT agent."
)

# The model asked for a tool but wrote no text; the action card below the message does the rest.
TOOL_OFFER = "I can do that for you. Check the details below and confirm when you're ready."

# Degraded mode, but the user plainly asked for a ticket or a password reset.
DEGRADED_TOOL_OFFER = (
    "The AI assistant is busy right now, but I can still do this for you. Check the details "
    "below and confirm."
)
