import pytest

from app.modules.identity.application.use_cases import (
    AuthenticateUser,
    EmailAlreadyRegisteredError,
    RegisterTenantOwner,
    RegisterTenantOwnerCommand,
)
from app.modules.identity.domain.entities import Identity, RegisteredTenantOwner


class FakeIdentityRepository:
    def __init__(self, identity: Identity | None = None):
        self.identity = identity
        self.created: tuple[str, str] | None = None

    async def find_by_email(self, _email: str) -> Identity | None:
        return self.identity

    async def create_tenant_owner(self, email: str, password_hash: str) -> RegisteredTenantOwner:
        self.created = (email, password_hash)
        return RegisteredTenantOwner(user_id=1, tenant_id=10)


class FakePasswordHasher:
    def hash(self, password: str) -> str:
        return f"hash:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == f"hash:{password}"


@pytest.mark.asyncio
async def test_register_owner_uses_ports_without_infrastructure():
    repository = FakeIdentityRepository()
    use_case = RegisterTenantOwner(repository, FakePasswordHasher())

    owner = await use_case.execute(RegisterTenantOwnerCommand("owner@example.com", "secret"))

    assert owner == RegisteredTenantOwner(user_id=1, tenant_id=10)
    assert repository.created == ("owner@example.com", "hash:secret")


@pytest.mark.asyncio
async def test_register_owner_rejects_duplicate_email():
    repository = FakeIdentityRepository(
        Identity(1, 10, "owner@example.com", "hash:secret", True)
    )

    with pytest.raises(EmailAlreadyRegisteredError):
        await RegisterTenantOwner(repository, FakePasswordHasher()).execute(
            RegisterTenantOwnerCommand("owner@example.com", "secret")
        )


@pytest.mark.asyncio
async def test_authenticate_returns_only_active_valid_identity():
    identity = Identity(1, 10, "owner@example.com", "hash:secret", True)
    use_case = AuthenticateUser(FakeIdentityRepository(identity), FakePasswordHasher())

    assert await use_case.execute("owner@example.com", "secret") == identity
    assert await use_case.execute("owner@example.com", "invalid") is None
