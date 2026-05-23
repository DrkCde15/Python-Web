from __future__ import annotations

from secrets import compare_digest

from fastapi import Header, HTTPException, status

from app.config import get_settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    settings = get_settings()

    if not settings.scraper_api_keys:
        return

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Informe a chave da API no header X-API-Key.",
        )

    for allowed_key in settings.scraper_api_keys:
        if compare_digest(x_api_key, allowed_key):
            return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Chave da API invalida.",
    )
