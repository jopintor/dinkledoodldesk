"""PII redaction: replace personal data with labels before text goes to the LLM or logs.

    clean, found = redact("call me at 09171234567")
    # clean == "call me at [PH_MOBILE]", found == ["PH_MOBILE"]

TODO: compare the labels and patterns with the table in security doc section 1.
"""

import re

# Official addresses that are not personal data and must never be changed.
PROTECTED_EMAILS = {"it-help@picklehub.example"}


def luhn_ok(digits: str) -> bool:
    """Standard Luhn checksum, used so random long numbers aren't treated as cards."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


# "my password is hunter2" / "my PIN is 4821": keep the words, hide only the value.
_VALUE = r"(?P<value>\S+?)(?=[.,;!?]*(?:\s|$))"
_PASSWORD = re.compile(
    r"\b(?P<prefix>my\s+(?:password|passcode)\s*(?:is|=|:)\s*)" + _VALUE,
    re.IGNORECASE,
)
_PIN = re.compile(
    r"\b(?P<prefix>my\s+pin(?:\s+(?:code|number))?\s*(?:is|=|:)\s*)" + _VALUE,
    re.IGNORECASE,
)

# 13 to 19 digits, optionally separated by spaces or dashes (checked with Luhn below).
_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")

# Government IDs (PH formats). All are labelled GOV_ID.
_GOV_ID = re.compile(
    r"(?<![\w-])(?:"
    r"\d{2}-\d{7}-\d"  # SSS
    r"|\d{3}-\d{3}-\d{3}(?:-\d{3,5})?"  # TIN
    r"|\d{2}-\d{9}-\d"  # PhilHealth
    r"|\d{4}-\d{7}-\d"  # UMID / CRN
    r"|[A-Z]\d{2}-\d{2}-\d{6}"  # driver's license
    r"|[A-Z]\d{7}[A-Z]"  # passport (new)
    r"|[A-Z]{2}\d{7}"  # passport (old)
    r")(?![\w-])"
)

# 09171234567, 0917 123 4567, 0917-123-4567, +63 917 123 4567, 639171234567
_MOBILE = re.compile(r"(?<![\w+-])(?:\+?63[ -]?|0)9\d{2}[ -]?\d{3}[ -]?\d{4}(?!\d)")

# (02) 8123 4567, 02-8123-4567, (046) 123 4567, +63 2 8123 4567
_LANDLINE = re.compile(
    r"(?<![\w-])(?:"
    r"(?:\(0\d{1,2}\)|0\d{1,2})[ -]?\d{3,4}[ -]?\d{4}"
    r"|\+63[ -]?\(?\d{1,2}\)?[ -]?\d{3,4}[ -]?\d{4}"
    r")(?!\d)"
)

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def redact(text: str) -> tuple[str, list[str]]:
    """Return (cleaned_text, types_found). Types are listed once, in the order found."""
    found: list[str] = []

    def note(kind: str) -> None:
        if kind not in found:
            found.append(kind)

    def label(kind: str, pattern: re.Pattern, s: str) -> str:
        def repl(_m: re.Match) -> str:
            note(kind)
            return f"[{kind}]"

        return pattern.sub(repl, s)

    def keep_prefix(kind: str, pattern: re.Pattern, s: str) -> str:
        def repl(m: re.Match) -> str:
            note(kind)
            return f"{m.group('prefix')}[{kind}]"

        return pattern.sub(repl, s)

    def cards(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        if 13 <= len(digits) <= 19 and luhn_ok(digits):
            note("CARD")
            return "[CARD]"
        return m.group(0)

    def emails(m: re.Match) -> str:
        if m.group(0).lower() in PROTECTED_EMAILS:
            return m.group(0)
        note("EMAIL")
        return "[EMAIL]"

    # Order matters: secrets first, then the longest digit patterns, then the rest.
    text = keep_prefix("PASSWORD", _PASSWORD, text)
    text = keep_prefix("PIN", _PIN, text)
    text = _CARD.sub(cards, text)
    text = label("GOV_ID", _GOV_ID, text)
    text = label("PH_MOBILE", _MOBILE, text)
    text = label("PH_LANDLINE", _LANDLINE, text)
    text = _EMAIL.sub(emails, text)
    return text, found
