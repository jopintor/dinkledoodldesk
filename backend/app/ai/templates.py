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

NOT_INDEXED = (
    "My knowledge base isn't available right now, so I can't look this up. I can create a "
    "ticket for the IT Service Desk or connect you to an IT agent."
)
