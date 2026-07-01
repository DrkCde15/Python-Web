# Integração com a API Groq (compatível com OpenAI) para respostas inteligentes
import base64
import asyncio
import tempfile
import os
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

VISION_MODELS = [
    'llama-3.2-11b-vision-preview',
    'llava-v1.5-7b',
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


def is_configured() -> bool:
    return bool(get_config('groq_api_key', ''))


def _normalize(text: str) -> str:
    return text.strip().lower()


SYSTEM_PROMPT = """Você é um assistente de atendimento ao cliente de uma empresa.

REGRAS GERAIS:
- Seja educado, profissional e objetivo.
- Responda em português brasileiro.
- Mantenha respostas curtas (máximo 3 parágrafos).
- Use formatação WhatsApp (*negrito* para ênfase).
- Se o cliente perguntar algo fora do escopo, diga educadamente que não pode responder e sugira falar com um atendente (opção 4 do menu).

INFORMAÇÕES DA EMPRESA:
- Horários: Seg-Sex 8h-18h | Sáb 8h-15h
- Pagamentos: Cartão, PIX, Boleto
- Prazo de entrega: Até 3 dias úteis
- Suporte: suporte@exemplo.com
- Telefone urgência: (11) 99999-8888

MENU PRINCIPAL (quando aplicável, lembre o cliente das opções):
1️⃣ Informações
2️⃣ Agendar horário
3️⃣ Falar com o Bot 🤖
4️⃣ Falar com atendente
5️⃣ Sair

EXEMPLOS DE ATENDIMENTO:

Cliente: "quanto custa o corte de cabelo?"
Resposta: "O valor do corte de cabelo é R$ 45,00 (masculino) ou R$ 65,00 (feminino). 💇
Deseja agendar um horário? Digite *2* para agendar ou *0* para voltar ao menu."

Cliente: "quero agendar um horário para amanhã"
Resposta: "Ótimo! Para agendar, preciso de algumas informações:
1️⃣ Qual *serviço* você deseja?
2️⃣ Qual *data e horário* prefere?

Pode me informar o serviço primeiro?"

Cliente: "meu nome é João"
Resposta: "Prazer, João! 😊 Agora me diga qual *serviço* você deseja."

Cliente: "serviço de barba"
Resposta: "Perfeito! E para qual *data e horário* você gostaria de agendar? (ex: 15/07 14:30)"

Cliente: "vocês vendem celular?"
Resposta: "Desculpe, não trabalhamos com venda de celulares. 📱
Posso ajudar com informações sobre nossos serviços ou agendar um horário para você.
Digite *0* para voltar ao menu principal ou me diga o que precisa."

Cliente: "obrigado"
Resposta: "Por nada! 😊 Estamos à disposição. Digite *0* para voltar ao menu principal ou *Olá* quando precisar de algo."

Cliente: "qual o prazo de entrega?"
Resposta: "Nosso prazo de entrega é de até *3 dias úteis*. 📦
Aceitamos pagamento via Cartão, PIX ou Boleto.
Mais alguma dúvida? Digite *0* para voltar ao menu."

QUANDO O CLIENTE PARECER CONFUSO:
- Seja paciente e ofereça ajuda
- Explique que ele pode digitar *0* ou *menu* a qualquer momento para voltar ao menu principal
- Pergunte se prefere falar com um atendente humano"""


_whisper_model = None
_whisper_model_lock = asyncio.Lock()


def _get_whisper_model():
    # Singleton do modelo faster-whisper (carregado uma vez em memória)
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        model_size = get_config('whisper_model', 'base')
        try:
            _whisper_model = WhisperModel(model_size, device='cpu', compute_type='int8')
        except Exception:
            _whisper_model = WhisperModel('tiny', device='cpu', compute_type='int8')
    return _whisper_model


def _transcribe_sync(audio_bytes: bytes, ext: str) -> str | None:
    # Executa transcrição síncrona (bloqueante) em thread separada
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name

        model = _get_whisper_model()
        segments, _ = model.transcribe(tmp_path, language='pt', beam_size=5)
        return ''.join(segment.text for segment in segments).strip()
    except Exception as e:
        logger.error('transcription_failed', error=str(e))
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


async def transcribe_audio(audio_base64: str, mimetype: str = 'audio/ogg') -> str | None:
    # Transcreve áudio usando faster-whisper (roda em thread separada pra não travar o event loop)
    ext = mimetype.split('/')[-1]
    ext = ext.replace('x-wav', 'wav').replace('x-m4a', 'm4a').replace('x-ms-wma', 'wma')

    try:
        audio_bytes = base64.b64decode(audio_base64)
    except Exception as e:
        logger.error('base64_decode_failed', error=str(e))
        return None

    async with _whisper_model_lock:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _transcribe_sync, audio_bytes, ext)


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


async def ask_ai_with_image(message: str, image_base64: str) -> str:
    # Envia imagem + texto para um modelo vision da Groq
    client = await _get_client()
    if not client:
        return FRIENDLY_ERROR

    prompt = message.strip() or 'Descreva esta imagem e responda o cliente adequadamente.'

    content = [
        {'type': 'text', 'text': prompt},
        {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{image_base64}'}},
    ]

    messages = [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': content},
    ]

    models_to_try = VISION_MODELS[:]
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
            return reply
        except Exception as e:
            last_error = e
            if hasattr(e, 'status_code') and e.status_code == 401:
                break
            continue

    return FRIENDLY_ERROR
