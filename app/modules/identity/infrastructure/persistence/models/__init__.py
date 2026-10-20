"""Modelos ORM propios del módulo identity."""

from app.modules.identity.infrastructure.persistence.models.role import Permission, Role, role_permissions
from app.modules.identity.infrastructure.persistence.models.tenant import Tenant
from app.modules.identity.infrastructure.persistence.models.user import User, UserRole

__all__ = ["Permission", "Role", "Tenant", "User", "UserRole", "role_permissions"]
