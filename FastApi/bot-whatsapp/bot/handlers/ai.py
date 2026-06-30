from openai import AsyncOpenAI
from database import get_config

_client = None
_cached_key = ''
_cached_url = ''


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


SYSTEM_PROMPT = """Você é um assistente de atendimento ao cliente de uma empresa.

Regras:
- Seja educado, profissional e objetivo.
- Responda em português brasileiro.
- Se o cliente perguntar algo fora do escopo, diga educadamente que não pode responder e sugira falar com um atendente.
- Se não souber responder, direcione para um atendente humano.
- Mantenha respostas curtas (máximo 3 parágrafos)."""


async def ask_ai(message: str, history: list = None) -> str:
    client = await _get_client()
    model = await get_model()

    if not client:
        return "Desculpe, o atendimento por IA está temporariamente indisponível. Digite *0* para falar com um atendente."

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        for h in history[-10:]:
            messages.append({"role": "user", "content": h.get("user", "")})
            if h.get("assistant"):
                messages.append({"role": "assistant", "content": h["assistant"]})

    messages.append({"role": "user", "content": message})

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=300,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Desculpe, ocorreu um erro ao processar sua mensagem. Digite *0* para falar com um atendente. (Erro: {str(e)})"
