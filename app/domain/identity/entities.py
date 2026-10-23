from dataclasses import dataclass


@dataclass(frozen=True)
class Identity:
    """Identidad autenticable, independiente de ORM y HTTP."""

    id: int
    tenant_id: int
    email: str
    password_hash: str
    is_active: bool


@dataclass(frozen=True)
class RegisteredTenantOwner:
    user_id: int
    tenant_id: int
