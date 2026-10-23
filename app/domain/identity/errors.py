from app.domain.shared.errors import ConflictError, DomainError, ForbiddenError, NotFoundError


class EmailAlreadyRegisteredError(DomainError):
    def __init__(self):
        super().__init__("Email already registered")


class UserNotFoundError(NotFoundError):
    def __init__(self):
        super().__init__("User not found")


class RoleNotFoundError(NotFoundError):
    def __init__(self):
        super().__init__("Role not found")


class WeakPasswordError(DomainError):
    def __init__(self):
        super().__init__("La contraseña debe tener entre 8 y 128 caracteres")


class PrivilegeEscalationError(ForbiddenError):
    def __init__(self, detail: str = "No puede asignar privilegios superiores a los suyos"):
        super().__init__(detail)


class CannotDeleteSelfError(DomainError):
    def __init__(self):
        super().__init__("Cannot delete yourself")


class UserInUseError(ConflictError):
    def __init__(self):
        super().__init__("El usuario tiene registros asociados; desactívelo en lugar de eliminarlo")


class RoleInUseError(ConflictError):
    def __init__(self):
        super().__init__("El rol está asignado a usuarios; reasígnelos antes de eliminarlo")


class DuplicateRoleError(ConflictError):
    def __init__(self):
        super().__init__("Ya existe un rol con ese nombre")


class InvalidPermissionError(DomainError):
    def __init__(self):
        super().__init__("Algún permiso indicado no existe")
