from typing import Any

from app.application.identity.ports import PasswordHasher, RoleDirectory, UserDirectory
from app.application.identity.user_dto import (
    Actor,
    CreateRoleCommand,
    CreateUserCommand,
    DeleteRoleCommand,
    DeleteUserCommand,
    UpdateOwnProfileCommand,
    UpdateRoleCommand,
    UpdateUserCommand,
)
from app.application.shared.ports import UnitOfWork
from app.domain.identity import rules
from app.domain.identity.errors import (
    CannotDeleteSelfError,
    DuplicateRoleError,
    EmailAlreadyRegisteredError,
    InvalidPermissionError,
    PrivilegeEscalationError,
    RoleInUseError,
    RoleNotFoundError,
    UserNotFoundError,
)


def _actor_rank(actor: Actor) -> int:
    return rules.rank(actor.role, actor.is_admin)


class _UserUseCase:
    def __init__(self, users: UserDirectory, passwords: PasswordHasher, uow: UnitOfWork):
        self.users = users
        self.passwords = passwords
        self.uow = uow

    async def _prepare_credentials(self, changes: dict[str, Any], user_id: int | None) -> dict[str, Any]:
        """Normaliza correo, valida unicidad y reemplaza `password` por su hash."""
        prepared = dict(changes)
        if prepared.get("email") is not None:
            prepared["email"] = rules.normalize_email(prepared["email"])
            if await self.users.email_taken(prepared["email"], exclude_user_id=user_id):
                raise EmailAlreadyRegisteredError()
        if "password" in prepared:
            password = prepared.pop("password")
            if password is not None:
                rules.validate_password(password)
                prepared["hashed_password"] = self.passwords.hash(password)
        return prepared


class CreateUser(_UserUseCase):
    async def execute(self, cmd: CreateUserCommand) -> int:
        try:
            rules.ensure_can_grant(_actor_rank(cmd.actor), cmd.role, cmd.is_admin)
            if cmd.role_id is not None and not await self.users.role_exists(cmd.actor.tenant_id, cmd.role_id):
                raise RoleNotFoundError()
            attributes = await self._prepare_credentials(
                {"email": cmd.email, "password": cmd.password}, user_id=None
            )
            attributes.update(
                first_name=cmd.first_name, last_name=cmd.last_name, is_admin=cmd.is_admin,
                role=cmd.role, role_id=cmd.role_id,
            )
            user_id = await self.users.create(cmd.actor.tenant_id, attributes)
            await self.uow.commit()
            return user_id
        except Exception:
            await self.uow.rollback()
            raise


class UpdateUser(_UserUseCase):
    async def execute(self, cmd: UpdateUserCommand) -> int:
        try:
            actor = cmd.actor
            target = await self.users.get(actor.tenant_id, cmd.user_id)
            if not target:
                raise UserNotFoundError()
            rules.ensure_can_manage(_actor_rank(actor), target.role, target.is_admin)

            if rules.PRIVILEGE_FIELDS & cmd.changes.keys():
                if target.id == actor.user_id:
                    raise PrivilegeEscalationError("No puede cambiar sus propios privilegios o estado")
                rules.ensure_can_grant(
                    _actor_rank(actor),
                    cmd.changes.get("role") or target.role,
                    bool(cmd.changes.get("is_admin", target.is_admin)),
                )
                role_id = cmd.changes.get("role_id")
                if role_id is not None and not await self.users.role_exists(actor.tenant_id, role_id):
                    raise RoleNotFoundError()

            changes = await self._prepare_credentials(cmd.changes, user_id=target.id)
            if changes:
                await self.users.update(actor.tenant_id, target.id, changes)
            await self.uow.commit()
            return target.id
        except Exception:
            await self.uow.rollback()
            raise


class UpdateOwnProfile(_UserUseCase):
    """Edición del propio perfil: solo campos de la lista blanca; los privilegios se ignoran."""

    async def execute(self, cmd: UpdateOwnProfileCommand) -> int:
        try:
            allowed = {k: v for k, v in cmd.changes.items() if k in rules.SELF_EDITABLE_FIELDS}
            changes = await self._prepare_credentials(allowed, user_id=cmd.actor.user_id)
            if changes:
                await self.users.update(cmd.actor.tenant_id, cmd.actor.user_id, changes)
            await self.uow.commit()
            return cmd.actor.user_id
        except Exception:
            await self.uow.rollback()
            raise


class DeleteUser:
    def __init__(self, users: UserDirectory, uow: UnitOfWork):
        self.users = users
        self.uow = uow

    async def execute(self, cmd: DeleteUserCommand) -> None:
        try:
            target = await self.users.get(cmd.actor.tenant_id, cmd.user_id)
            if not target:
                raise UserNotFoundError()
            if target.id == cmd.actor.user_id:
                raise CannotDeleteSelfError()
            rules.ensure_can_manage(_actor_rank(cmd.actor), target.role, target.is_admin)
            await self.users.delete(cmd.actor.tenant_id, target.id)
            await self.uow.commit()
        except Exception:
            await self.uow.rollback()
            raise


class _RoleUseCase:
    def __init__(self, roles: RoleDirectory, uow: UnitOfWork):
        self.roles = roles
        self.uow = uow

    async def _check_permissions(self, permission_ids) -> None:
        if permission_ids and await self.roles.missing_permissions(set(permission_ids)):
            raise InvalidPermissionError()


class CreateRole(_RoleUseCase):
    async def execute(self, cmd: CreateRoleCommand) -> int:
        try:
            name = cmd.name.strip()
            if await self.roles.name_taken(cmd.tenant_id, name):
                raise DuplicateRoleError()
            await self._check_permissions(cmd.permission_ids)
            role_id = await self.roles.create(cmd.tenant_id, name, cmd.description, cmd.permission_ids)
            await self.uow.commit()
            return role_id
        except Exception:
            await self.uow.rollback()
            raise


class UpdateRole(_RoleUseCase):
    async def execute(self, cmd: UpdateRoleCommand) -> int:
        try:
            if not await self.roles.get(cmd.tenant_id, cmd.role_id):
                raise RoleNotFoundError()
            changes = dict(cmd.changes)
            if changes.get("name") is not None:
                changes["name"] = changes["name"].strip()
                if await self.roles.name_taken(cmd.tenant_id, changes["name"], exclude_role_id=cmd.role_id):
                    raise DuplicateRoleError()
            await self._check_permissions(cmd.permission_ids)
            await self.roles.update(cmd.tenant_id, cmd.role_id, changes, cmd.permission_ids)
            await self.uow.commit()
            return cmd.role_id
        except Exception:
            await self.uow.rollback()
            raise


class DeleteRole(_RoleUseCase):
    async def execute(self, cmd: DeleteRoleCommand) -> None:
        try:
            role = await self.roles.get(cmd.tenant_id, cmd.role_id)
            if not role:
                raise RoleNotFoundError()
            if role.users_count:
                raise RoleInUseError()
            await self.roles.delete(cmd.tenant_id, cmd.role_id)
            await self.uow.commit()
        except Exception:
            await self.uow.rollback()
            raise
