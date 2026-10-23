"""Modelos ORM propios del módulo identity."""

from app.infrastructure.persistence.models.identity.role import Permission, Role, role_permissions
from app.infrastructure.persistence.models.identity.tenant import Tenant
from app.infrastructure.persistence.models.identity.user import User, UserRole

__all__ = ["Permission", "Role", "Tenant", "User", "UserRole", "role_permissions"]
