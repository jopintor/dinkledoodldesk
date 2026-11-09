"""PII redactor used by the guardrail tests.

Uses the real `app.guardrails.pii.redact` once PR #16 is merged; until then a minimal
stand-in with the same signature that knows the two entity types the golden set uses
(PH mobile numbers and emails) plus Luhn-valid card numbers.
"""

import re

from app.guardrails.injection import load_pii_redactor

_MOBILE = re.compile(r"(?<![\w+-])(?:\+?63[ -]?|0)9\d{2}[ -]?\d{3}[ -]?\d{4}(?!\d)")
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")


def _luhn(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch) * (2 if i % 2 else 1)
        total += d - 9 if d > 9 else d
    return total % 10 == 0


def _stand_in(text: str) -> tuple[str, list[str]]:
    found: list[str] = []

    def sub(kind: str, pattern: re.Pattern[str], s: str, check=lambda m: True) -> str:
        def repl(m: re.Match[str]) -> str:
            if not check(m):
                return m.group(0)
            if kind not in found:
                found.append(kind)
            return f"[{kind}]"

        return pattern.sub(repl, s)

    text = sub("CARD", _CARD, text, lambda m: _luhn(re.sub(r"\D", "", m.group(0))))
    text = sub("PH_MOBILE", _MOBILE, text)
    text = sub("EMAIL", _EMAIL, text)
    return text, found


fake_redact = load_pii_redactor() or _stand_in
