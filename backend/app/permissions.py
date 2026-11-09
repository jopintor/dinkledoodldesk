ROLE_PERMISSIONS: dict[str, set[str]] = {
    "member": {"ticket:create", "ticket:read-own", "chat:use"},
    "staff": {"ticket:create", "ticket:read-own", "chat:use", "status:read"},
    "agent": {"ticket:read-any", "ticket:update", "chat:use", "status:read", "kb:search"},
    "admin": {"*"},  # everything
}


def has_permission(role_name: str, permission: str) -> bool:
    perms = ROLE_PERMISSIONS.get(role_name, set())
    return "*" in perms or permission in perms
