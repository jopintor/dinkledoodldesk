import base64
import re


def ticket_number(ticket_id: int) -> str:
    return f"DD-{ticket_id:06d}"


def parse_ticket_ref(ref: str) -> int | None:
    """Accepts '12' or 'DD-000012' and returns the numeric id."""
    match = re.fullmatch(r"(?:DD-)?(\d+)", ref.strip(), re.IGNORECASE)
    return int(match.group(1)) if match else None


def encode_cursor(last_id: int) -> str:
    return base64.urlsafe_b64encode(str(last_id).encode()).decode()


def decode_cursor(cursor: str) -> int | None:
    try:
        return int(base64.urlsafe_b64decode(cursor.encode()).decode())
    except (ValueError, UnicodeDecodeError):
        return None


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
