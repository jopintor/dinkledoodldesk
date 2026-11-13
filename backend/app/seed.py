from sqlalchemy import select

from app.db import SessionLocal
from app.models import Club, Role, ServiceStatus, User
from app.security import hash_password

ROLES = ["member", "staff", "agent", "admin"]

CLUBS = [
    ("DAS", "Dasmariñas"),
    ("IMS", "Imus"),
    ("BAC", "Bacoor"),
    ("GTR", "General Trias"),
    ("TAG", "Tagaytay"),
]

# (email, full name, password, role)
USERS = [
    ("member@picklehub.example", "Demo Member", "member123!", "member"),
    ("staff@picklehub.example", "Demo Staff", "staff123!", "staff"),
    ("agent@picklehub.example", "Demo Agent", "agent123!", "agent"),
    ("admin1@picklehub.example", "Demo Admin One", "admin123!", "admin"),
    ("admin2@picklehub.example", "Demo Admin Two", "admin456!", "admin"),
]

# Directory account used by the reset_password tool (email -> directory username).
DIRECTORY_USERNAMES = {"staff@picklehub.example": "demo.staff"}

# TODO: replace with the services listed in
# knowledge-base/kb-025-service-status-page-guide.md
SERVICES = [
    "Court booking",
    "Online payments",
    "Member app",
]


def get_or_create(session, model, defaults=None, **lookup):
    obj = session.scalar(select(model).filter_by(**lookup))
    if obj is None:
        obj = model(**lookup, **(defaults or {}))
        session.add(obj)
        session.flush()
    return obj


def main():
    with SessionLocal() as session:
        roles = {name: get_or_create(session, Role, name=name) for name in ROLES}

        clubs = {}
        for code, name in CLUBS:
            clubs[code] = get_or_create(session, Club, code=code, defaults={"name": name})

        for email, full_name, password, role in USERS:
            user = get_or_create(
                session,
                User,
                email=email,
                defaults={
                    "full_name": full_name,
                    "password_hash": hash_password(password),
                    "role_id": roles[role].id,
                    "club_id": clubs["DAS"].id,
                },
            )
            # Upgrade any old (non-argon2) hash from the earlier seed.
            if not user.password_hash.startswith("$argon2"):
                user.password_hash = hash_password(password)

            username = DIRECTORY_USERNAMES.get(email)
            if username:
                user.directory_username = username

        for service in SERVICES:
            get_or_create(
                session,
                ServiceStatus,
                service_name=service,
                defaults={"status": "operational"},
            )

        session.commit()
    print("Seed complete.")


if __name__ == "__main__":
    main()
