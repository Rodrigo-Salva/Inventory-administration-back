"""Reglas puras de identidad: jerarquía de privilegios, correo y contraseña."""

from app.domain.identity.errors import PrivilegeEscalationError, WeakPasswordError

ROLE_RANK = {"SELLER": 0, "MANAGER": 1, "ADMIN": 2, "SUPERADMIN": 3}
ADMIN_RANK = ROLE_RANK["ADMIN"]

# Campos que cualquier usuario puede editar de su propio perfil
SELF_EDITABLE_FIELDS = frozenset({"first_name", "last_name", "phone", "avatar_url", "email", "password"})
# Campos que cambian la autoridad de una cuenta
PRIVILEGE_FIELDS = frozenset({"is_admin", "is_active", "role", "role_id"})


def rank(role: str, is_admin: bool) -> int:
    """Nivel de autoridad: un dueño de tenant (is_admin) equivale a ADMIN."""
    return max(ROLE_RANK.get(role, 0), ADMIN_RANK if is_admin else 0)


def ensure_can_grant(actor_rank: int, role: str, is_admin: bool) -> None:
    """Nadie puede otorgar un rol o la bandera de admin por encima de su propio nivel."""
    if rank(role, is_admin) > actor_rank:
        raise PrivilegeEscalationError()


def ensure_can_manage(actor_rank: int, target_role: str, target_is_admin: bool) -> None:
    """Nadie puede modificar ni eliminar cuentas de mayor nivel que el suyo."""
    if rank(target_role, target_is_admin) > actor_rank:
        raise PrivilegeEscalationError("No puede modificar una cuenta de mayor nivel que la suya")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_password(password: str) -> None:
    if not 8 <= len(password) <= 128:
        raise WeakPasswordError()
