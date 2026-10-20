from typing import Protocol

from app.modules.identity.domain.entities import Identity, RegisteredTenantOwner


class IdentityRepository(Protocol):
    async def find_by_email(self, email: str) -> Identity | None: ...

    async def create_tenant_owner(
        self, email: str, password_hash: str
    ) -> RegisteredTenantOwner: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...
