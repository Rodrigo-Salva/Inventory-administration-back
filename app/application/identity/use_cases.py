from dataclasses import dataclass

from app.application.identity.ports import IdentityRepository, PasswordHasher
from app.domain.identity import rules
from app.domain.identity.entities import Identity, RegisteredTenantOwner
from app.domain.identity.errors import EmailAlreadyRegisteredError  # noqa: F401  (re-exportado)


@dataclass(frozen=True)
class RegisterTenantOwnerCommand:
    email: str
    password: str


class RegisterTenantOwner:
    def __init__(self, identities: IdentityRepository, passwords: PasswordHasher):
        self.identities = identities
        self.passwords = passwords

    async def execute(self, command: RegisterTenantOwnerCommand) -> RegisteredTenantOwner:
        email = rules.normalize_email(command.email)
        rules.validate_password(command.password)
        if await self.identities.find_by_email(email):
            raise EmailAlreadyRegisteredError()
        return await self.identities.create_tenant_owner(email, self.passwords.hash(command.password))


class AuthenticateUser:
    def __init__(self, identities: IdentityRepository, passwords: PasswordHasher):
        self.identities = identities
        self.passwords = passwords

    async def execute(self, email: str, password: str) -> Identity | None:
        identity = await self.identities.find_by_email(rules.normalize_email(email))
        if not identity or not identity.is_active:
            return None
        return identity if self.passwords.verify(password, identity.password_hash) else None
