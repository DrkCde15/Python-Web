# Integração com a API Groq (compatível com OpenAI) para respostas inteligentes
from openai import AsyncOpenAI
from database import get_config, get_cache_response, set_cache_response

_client = None
_cached_key = ''
_cached_url = ''

FALLBACK_MODELS = [
    'openai/gpt-oss-120b',
    'gemma2-9b-it',
    'llama-3.3-70b-versatile',
    'mixtral-8x7b-32768',
]

FRIENDLY_ERROR = (
    "Desculpe, o atendimento por IA está temporariamente sobrecarregado. "
    "Tente novamente em alguns minutos ou digite *0* para falar com um atendente."
)


async def _get_client():
    global _client, _cached_key, _cached_url
    key = get_config('groq_api_key', '')
    url = get_config('groq_base_url', 'https://api.groq.com/openai/v1')
    if key != _cached_key or url != _cached_url:
        _client = AsyncOpenAI(api_key=key, base_url=url) if key else None
        _cached_key = key
        _cached_url = url
    return _client


async def get_model() -> str:
    return get_config('groq_model', 'grok-2-1212')


async def is_configured() -> bool:
    return bool(get_config('groq_api_key', ''))


def _normalize(text: str) -> str:
    return text.strip().lower()


SYSTEM_PROMPT = """Você é um assistente de atendimento ao cliente de uma empresa.

Regras:
- Seja educado, profissional e objetivo.
- Responda em português brasileiro.
- Se o cliente perguntar algo fora do escopo, diga educadamente que não pode responder e sugira falar com um atendente.
- Se não souber responder, direcione para um atendente humano.
- Mantenha respostas curtas (máximo 3 parágrafos)."""


async def ask_ai(message: str, history: list = None) -> str:
    # Verifica cache primeiro (apenas para mensagens sem histórico)
    if not history:
        cached = get_cache_response(message)
        if cached:
            return cached

    client = await _get_client()
    if not client:
        return FRIENDLY_ERROR

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        for h in history[-10:]:
            messages.append({"role": "user", "content": h.get("user", "")})
            if h.get("assistant"):
                messages.append({"role": "assistant", "content": h["assistant"]})

    messages.append({"role": "user", "content": message})

    models_to_try = [await get_model()] + [m for m in FALLBACK_MODELS if m != await get_model()]
    last_error = None

    for model in models_to_try:
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=300,
                temperature=0.7,
            )
            reply = response.choices[0].message.content.strip()
            # Cacheia respostas de perguntas sem histórico
            if not history:
                set_cache_response(message, reply, model=model)
            return reply
        except Exception as e:
            last_error = e
            # Se for erro de autenticação (401), não adianta tentar outro modelo
            if hasattr(e, 'status_code') and e.status_code == 401:
                break
            continue

    # Todas as tentativas falharam
    return FRIENDLY_ERROR
