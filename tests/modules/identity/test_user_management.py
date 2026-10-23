import pytest

from app.application.identity.user_dto import (
    Actor,
    CreateRoleCommand,
    CreateUserCommand,
    DeleteRoleCommand,
    DeleteUserCommand,
    RoleSnapshot,
    UpdateOwnProfileCommand,
    UpdateRoleCommand,
    UpdateUserCommand,
    UserSnapshot,
)
from app.application.identity.user_use_cases import (
    CreateRole,
    CreateUser,
    DeleteRole,
    DeleteUser,
    UpdateOwnProfile,
    UpdateRole,
    UpdateUser,
)
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
    WeakPasswordError,
)

OWNER = Actor(user_id=1, tenant_id=10, role="SELLER", is_admin=True)        # dueño del tenant
MANAGER = Actor(user_id=2, tenant_id=10, role="MANAGER", is_admin=False)
SELLER = Actor(user_id=3, tenant_id=10, role="SELLER", is_admin=False)
SUPER = Actor(user_id=9, tenant_id=10, role="SUPERADMIN", is_admin=True)


class FakeHasher:
    def hash(self, password):
        return f"hash:{password}"

    def verify(self, password, password_hash):
        return password_hash == f"hash:{password}"


class World:
    def __init__(self, users=(), taken_emails=(), roles=(7,), permissions=(1, 2), role_users=0):
        self.users = {u.id: u for u in users}
        self.taken, self.role_ids, self.perms = set(taken_emails), set(roles), set(permissions)
        self.role_users = role_users
        self.created = self.updated = self.deleted = None
        self.role_created = self.role_updated = self.role_deleted = None
        self.commits = self.rollbacks = 0

    # UserDirectory
    async def email_taken(self, email, exclude_user_id=None):
        return email in self.taken

    async def get(self, tenant_id, user_id):
        return self.users.get(user_id)

    async def role_exists(self, tenant_id, role_id):
        return role_id in self.role_ids

    async def create(self, tenant_id, attributes):
        self.created = attributes
        return 50

    async def update(self, tenant_id, user_id, attributes):
        self.updated = (user_id, attributes)

    async def delete(self, tenant_id, user_id):
        self.deleted = user_id

    # RoleDirectory (get/create/update/delete comparten nombre: se separan con prefijo vía adaptador)
    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


class RoleWorld(World):
    async def missing_permissions(self, ids):
        return set(ids) - self.perms

    async def name_taken(self, tenant_id, name, exclude_role_id=None):
        return name.lower() == "taken"

    async def get(self, tenant_id, role_id):
        return RoleSnapshot(role_id, self.role_users) if role_id in self.role_ids else None

    async def create(self, tenant_id, name, description, permission_ids):
        self.role_created = (name, permission_ids)
        return 70

    async def update(self, tenant_id, role_id, changes, permission_ids):
        self.role_updated = (changes, permission_ids)

    async def delete(self, tenant_id, role_id):
        self.role_deleted = role_id


def user(uid, role="SELLER", admin=False, active=True):
    return UserSnapshot(uid, role, admin, active)


def create_cmd(actor=OWNER, **kw):
    base = dict(email="  New@Example.com ", password="password1", role="SELLER")
    return CreateUserCommand(actor=actor, **{**base, **kw})


def test_rank_rules():
    assert rules.rank("SELLER", True) == 2 and rules.rank("MANAGER", False) == 1
    assert rules.rank("SUPERADMIN", False) == 3
    rules.ensure_can_grant(2, "ADMIN", False)
    with pytest.raises(PrivilegeEscalationError):
        rules.ensure_can_grant(2, "SUPERADMIN", False)
    with pytest.raises(PrivilegeEscalationError):
        rules.ensure_can_grant(1, "SELLER", True)


async def test_create_user_normalizes_email_and_hashes_password():
    w = World()
    assert await CreateUser(w, FakeHasher(), w).execute(create_cmd(role="MANAGER", role_id=7)) == 50
    assert w.created["email"] == "new@example.com" and w.created["hashed_password"] == "hash:password1"
    assert "password" not in w.created and w.commits == 1


async def test_create_user_blocks_privilege_escalation():
    w = World()
    uc = CreateUser(w, FakeHasher(), w)
    with pytest.raises(PrivilegeEscalationError):  # un admin de tenant no crea SUPERADMIN
        await uc.execute(create_cmd(actor=OWNER, role="SUPERADMIN"))
    with pytest.raises(PrivilegeEscalationError):  # un manager no crea admins
        await uc.execute(create_cmd(actor=MANAGER, is_admin=True))
    with pytest.raises(PrivilegeEscalationError):
        await uc.execute(create_cmd(actor=MANAGER, role="ADMIN"))
    assert w.created is None
    await CreateUser(World(), FakeHasher(), World()).execute(create_cmd(actor=SUPER, role="SUPERADMIN"))


async def test_create_user_validations():
    uc = lambda w: CreateUser(w, FakeHasher(), w)
    w = World(taken_emails={"new@example.com"})
    with pytest.raises(EmailAlreadyRegisteredError):
        await uc(w).execute(create_cmd())
    with pytest.raises(WeakPasswordError):
        await uc(World()).execute(create_cmd(password="short"))
    with pytest.raises(RoleNotFoundError):  # rol de otro tenant
        await uc(World()).execute(create_cmd(role_id=999))


async def test_update_user_cannot_escalate_or_touch_higher_accounts():
    w = World(users=[user(5), user(6, "ADMIN"), user(7, "SUPERADMIN")])
    uc = UpdateUser(w, FakeHasher(), w)
    with pytest.raises(PrivilegeEscalationError):
        await uc.execute(UpdateUserCommand(MANAGER, 5, {"role": "ADMIN"}))
    with pytest.raises(PrivilegeEscalationError):
        await uc.execute(UpdateUserCommand(MANAGER, 5, {"is_admin": True}))
    with pytest.raises(PrivilegeEscalationError):  # manager no edita a un admin
        await uc.execute(UpdateUserCommand(MANAGER, 6, {"first_name": "x"}))
    with pytest.raises(PrivilegeEscalationError):  # admin no edita a un SUPERADMIN
        await uc.execute(UpdateUserCommand(OWNER, 7, {"first_name": "x"}))
    assert w.updated is None

    await uc.execute(UpdateUserCommand(OWNER, 5, {"role": "MANAGER", "first_name": "Ana"}))
    assert w.updated == (5, {"role": "MANAGER", "first_name": "Ana"})


async def test_update_user_blocks_self_privilege_changes_and_checks_role_tenant():
    w = World(users=[user(1, "SELLER", True), user(5)])
    uc = UpdateUser(w, FakeHasher(), w)
    with pytest.raises(PrivilegeEscalationError):
        await uc.execute(UpdateUserCommand(OWNER, 1, {"is_active": False}))
    with pytest.raises(RoleNotFoundError):
        await uc.execute(UpdateUserCommand(OWNER, 5, {"role_id": 999}))
    with pytest.raises(UserNotFoundError):
        await uc.execute(UpdateUserCommand(OWNER, 404, {"first_name": "x"}))
    await uc.execute(UpdateUserCommand(OWNER, 1, {"first_name": "Yo"}))  # campos normales de uno mismo: ok
    assert w.updated == (1, {"first_name": "Yo"})


async def test_update_user_password_is_hashed_and_email_unique():
    w = World(users=[user(5)], taken_emails={"dup@example.com"})
    uc = UpdateUser(w, FakeHasher(), w)
    await uc.execute(UpdateUserCommand(OWNER, 5, {"password": "newpassword"}))
    assert w.updated[1] == {"hashed_password": "hash:newpassword"}
    with pytest.raises(EmailAlreadyRegisteredError):
        await uc.execute(UpdateUserCommand(OWNER, 5, {"email": "DUP@example.com"}))


async def test_own_profile_ignores_privilege_fields():
    """Regresión: PATCH /users/me permitía enviar role=SUPERADMIN y escalar privilegios."""
    w = World()
    changes = {"first_name": "Eve", "role": "SUPERADMIN", "role_id": 7, "is_admin": True, "is_active": True}
    await UpdateOwnProfile(w, FakeHasher(), w).execute(UpdateOwnProfileCommand(SELLER, changes))
    assert w.updated == (3, {"first_name": "Eve"})


async def test_delete_user_rules():
    w = World(users=[user(3), user(5), user(6, "ADMIN")])
    uc = DeleteUser(w, w)
    with pytest.raises(CannotDeleteSelfError):
        await uc.execute(DeleteUserCommand(SELLER, 3))
    with pytest.raises(PrivilegeEscalationError):
        await uc.execute(DeleteUserCommand(MANAGER, 6))
    with pytest.raises(UserNotFoundError):
        await uc.execute(DeleteUserCommand(OWNER, 404))
    await uc.execute(DeleteUserCommand(OWNER, 5))
    assert w.deleted == 5


async def test_role_use_cases():
    w = RoleWorld()
    assert await CreateRole(w, w).execute(CreateRoleCommand(10, " Cajero ", None, (1, 2))) == 70
    assert w.role_created == ("Cajero", (1, 2))
    with pytest.raises(DuplicateRoleError):
        await CreateRole(w, w).execute(CreateRoleCommand(10, "Taken"))
    with pytest.raises(InvalidPermissionError):
        await CreateRole(w, w).execute(CreateRoleCommand(10, "Otro", None, (1, 99)))

    await UpdateRole(w, w).execute(UpdateRoleCommand(10, 7, {"name": " Nuevo "}, (1,)))
    assert w.role_updated == ({"name": "Nuevo"}, (1,))
    with pytest.raises(RoleNotFoundError):
        await UpdateRole(w, w).execute(UpdateRoleCommand(10, 404, {}))


async def test_delete_role_blocked_when_in_use():
    w = RoleWorld(role_users=2)
    with pytest.raises(RoleInUseError):
        await DeleteRole(w, w).execute(DeleteRoleCommand(10, 7))
    w = RoleWorld()
    await DeleteRole(w, w).execute(DeleteRoleCommand(10, 7))
    assert w.role_deleted == 7
