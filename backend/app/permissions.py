ROLE_PERMISSIONS: dict[str, set[str]] = {
    "member": {"ticket:create", "ticket:read-own", "chat:use", "status:read"},
    "staff": {"ticket:create", "ticket:read-own", "chat:use", "status:read"},
    "agent": {
        "ticket:create",
        "ticket:read-own",
        "ticket:read-any",
        "ticket:update",
        "chat:use",
        "status:read",
    },
    "admin": {"*"},  # everything, including status:update
}


def has_permission(role_name: str, permission: str) -> bool:
    perms = ROLE_PERMISSIONS.get(role_name, set())
    return "*" in perms or permission in perms
