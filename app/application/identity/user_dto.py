from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Actor:
    """Quién ejecuta la operación (se arma desde el usuario autenticado)."""

    user_id: int
    tenant_id: int
    role: str
    is_admin: bool


@dataclass(frozen=True)
class UserSnapshot:
    id: int
    role: str
    is_admin: bool
    is_active: bool


@dataclass(frozen=True)
class CreateUserCommand:
    actor: Actor
    email: str
    password: str
    first_name: str | None = None
    last_name: str | None = None
    is_admin: bool = False
    role: str = "SELLER"
    role_id: int | None = None


@dataclass(frozen=True)
class UpdateUserCommand:
    actor: Actor
    user_id: int
    changes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class UpdateOwnProfileCommand:
    actor: Actor
    changes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DeleteUserCommand:
    actor: Actor
    user_id: int


@dataclass(frozen=True)
class RoleSnapshot:
    id: int
    users_count: int


@dataclass(frozen=True)
class CreateRoleCommand:
    tenant_id: int
    name: str
    description: str | None = None
    permission_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class UpdateRoleCommand:
    tenant_id: int
    role_id: int
    changes: dict[str, Any] = field(default_factory=dict)
    permission_ids: tuple[int, ...] | None = None


@dataclass(frozen=True)
class DeleteRoleCommand:
    tenant_id: int
    role_id: int
