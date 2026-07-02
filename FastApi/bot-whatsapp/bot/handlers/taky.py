import structlog
from httpx import AsyncClient
from database import get_config

logger = structlog.get_logger()

async def create_task(titulo: str, descricao: str, telefone: str) -> int | None:
    api_url = get_config('taky_api_url', '')
    if not api_url:
        logger.warning('taky_not_configured')
        return None

    token = await _get_taky_token()
    if not token:
        return None

    project_id = get_config('taky_default_project_id', '')
    user_id = get_config('taky_default_user_id', '')

    try:
        async with AsyncClient() as client:
            payload = {
                'project_id': int(project_id) if project_id else None,
                'title': titulo,
                'description': f'Cliente: {telefone}\n\n{descricao}',
                'user_id': int(user_id) if user_id else None,
            }
            payload = {k: v for k, v in payload.items() if v is not None}

            resp = await client.post(
                f'{api_url.rstrip("/")}/tasks',
                json=payload,
                headers={'Authorization': f'Bearer {token}'},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            task_id = data.get('id')
            logger.info('taky_task_created', task_id=task_id, telefone=telefone)
            return task_id
    except Exception as e:
        logger.error('taky_create_failed', error=str(e), telefone=telefone)
        return None


async def _get_taky_token() -> str | None:
    email = get_config('taky_email', '')
    password = get_config('taky_password', '')
    api_url = get_config('taky_api_url', '')
    if not email or not password or not api_url:
        return None
    try:
        async with AsyncClient() as client:
            resp = await client.post(
                f'{api_url.rstrip("/")}/auth/token',
                data={'username': email, 'password': password},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get('access_token')
    except Exception as e:
        logger.error('taky_auth_failed', error=str(e))
        return None
