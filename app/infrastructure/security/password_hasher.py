from app.infrastructure.security.auth import get_password_hash, verify_password


class PasslibPasswordHasher:
    def hash(self, password: str) -> str:
        return get_password_hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        return verify_password(password, password_hash)
