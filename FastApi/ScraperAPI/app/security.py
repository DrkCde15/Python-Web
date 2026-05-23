from __future__ import annotations

from ipaddress import ip_address
import socket
from urllib.parse import urlparse

from fastapi import HTTPException

from app.config import get_settings


PRIVATE_HOSTS = {"localhost", "0.0.0.0"}


def validate_public_url(raw_url: str) -> None:
    settings = get_settings()
    parsed = urlparse(raw_url)

    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Somente URLs http e https sao aceitas.")

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="URL sem hostname valido.")

    if settings.allow_private_urls:
        return

    if hostname.lower() in PRIVATE_HOSTS:
        raise HTTPException(status_code=400, detail="URL privada bloqueada por seguranca.")

    try:
        resolved_ips = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise HTTPException(status_code=400, detail="Nao foi possivel resolver o hostname.") from exc

    for resolved in resolved_ips:
        address = resolved[4][0]
        ip = ip_address(address)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
            raise HTTPException(status_code=400, detail="URL privada bloqueada por seguranca.")
