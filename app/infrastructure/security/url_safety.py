"""Validación anti-SSRF para URLs suministradas por usuarios (webhooks)."""

import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeUrlError(ValueError):
    """La URL apunta a un destino no permitido."""


def assert_public_http_url(url: str, *, allow_http: bool = False) -> None:
    parsed = urlparse(url)
    allowed = {"https", "http"} if allow_http else {"https"}
    if parsed.scheme not in allowed or not parsed.hostname:
        raise UnsafeUrlError("La URL debe usar https y tener un host válido")
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(parsed.hostname, parsed.port or 443)}
    except socket.gaierror as error:
        raise UnsafeUrlError("No se pudo resolver el host de la URL") from error
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise UnsafeUrlError("La URL apunta a una red privada o reservada")
