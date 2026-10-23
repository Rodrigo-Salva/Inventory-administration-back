"""Errores de dominio: independientes de HTTP y de cualquier framework."""


class DomainError(Exception):
    """Se violó una regla de negocio (la capa HTTP la traduce a 400)."""


class NotFoundError(DomainError):
    """El recurso solicitado no existe para el tenant (404)."""


class ConflictError(DomainError):
    """El recurso ya existe o choca con otro (409)."""


class ForbiddenError(DomainError):
    """El actor no tiene autoridad para esta operación (403)."""
