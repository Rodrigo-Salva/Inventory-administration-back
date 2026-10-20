from dataclasses import dataclass

from app.modules.identity.application.ports import IdentityRepository, PasswordHasher
from app.modules.identity.domain.entities import Identity, RegisteredTenantOwner


class EmailAlreadyRegisteredError(Exception):
    """El correo ya pertenece a un usuario existente."""


@dataclass(frozen=True)
class RegisterTenantOwnerCommand:
    email: str
    password: str


class RegisterTenantOwner:
    def __init__(self, identities: IdentityRepository, passwords: PasswordHasher):
        self.identities = identities
        self.passwords = passwords

    async def execute(self, command: RegisterTenantOwnerCommand) -> RegisteredTenantOwner:
        if await self.identities.find_by_email(command.email):
            raise EmailAlreadyRegisteredError
        return await self.identities.create_tenant_owner(
            command.email, self.passwords.hash(command.password)
        )


class AuthenticateUser:
    def __init__(self, identities: IdentityRepository, passwords: PasswordHasher):
        self.identities = identities
        self.passwords = passwords

    async def execute(self, email: str, password: str) -> Identity | None:
        identity = await self.identities.find_by_email(email)
        if not identity or not identity.is_active:
            return None
        return identity if self.passwords.verify(password, identity.password_hash) else None
