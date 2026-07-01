# Schemas Pydantic para validação automática de todas as requisições HTTP
from pydantic import BaseModel, Field


class WebhookPayload(BaseModel):
    # Mensagem recebida do gateway. O alias 'from' mapeia o campo JSON "from" para "from_".
    from_: str = Field(..., alias='from', min_length=1)
    text: str = ''
    type: str = 'text'
    image: str | None = None  # base64 da imagem (presente se type == 'image')
    audio: str | None = None  # base64 do áudio (presente se type == 'audio')
    mimetype: str | None = None  # MIME type do áudio (ex: audio/ogg)
    timestamp: int | None = None
    msgId: str | None = None


class SendMessageRequest(BaseModel):
    # Envio manual de mensagem pelo dashboard. Valida formato do JID.
    to: str = Field(..., min_length=5, pattern=r'^\d+@s\.whatsapp\.net$')
    text: str = Field(..., min_length=1)


class SetupRequest(BaseModel):
    # Configuração inicial do admin. Senha com mínimo de 4 caracteres.
    password: str = Field(..., min_length=4)
    groq_api_key: str | None = None
    groq_model: str | None = None
    groq_base_url: str | None = None


class LoginRequest(BaseModel):
    password: str = Field(..., min_length=1)


class WhitelistUpdate(BaseModel):
    # Lista de números autorizados e flag para ativar/desativar a whitelist.
    numbers: list[str] = []
    enabled: bool | None = None


class SettingsUpdate(BaseModel):
    groq_api_key: str | None = None
    groq_model: str | None = None
    groq_base_url: str | None = None
    group_enabled: str | None = None


class AgendamentoUpdate(BaseModel):
    status: str | None = None
    observacao: str | None = None


class ClienteNomeUpdate(BaseModel):
    nome: str = Field(..., min_length=1)
