"""Regras de negocio do bot de WhatsApp usadas pela API."""

from __future__ import annotations
import os
import time
import unicodedata
from collections.abc import Callable
from datetime import datetime, timezone, tzinfo
from string import Formatter
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import pywhatkit
from contact_reader import ContactRow
from dotenv import load_dotenv

load_dotenv()

DEFAULT_BOT_NAME = "robot6"
DEFAULT_TIMEZONE = "America/Sao_Paulo"
DEFAULT_PYWHATKIT_WAIT_TIME = 15
DEFAULT_PYWHATKIT_CLOSE_TIME = 3
DEFAULT_WEB_SESSION_DIR = os.getenv("WHATSAPP_WEB_SESSION_DIR", "whatsapp_session")
DEFAULT_WEB_POLL_INTERVAL = 2.0
DEFAULT_COUNTRY_CODE = os.getenv("DEFAULT_COUNTRY_CODE", "+55")
DEFAULT_CONTACT_DELAY = float(os.getenv("CONTACT_SEND_DELAY", "5"))

BOT_NAME = os.getenv("BOT_NAME", DEFAULT_BOT_NAME)
BOT_TIMEZONE = os.getenv("BOT_TIMEZONE", DEFAULT_TIMEZONE)
DEFAULT_WAIT_TIME = int(os.getenv("PYWHATKIT_WAIT_TIME", DEFAULT_PYWHATKIT_WAIT_TIME))
DEFAULT_CLOSE_TIME = int(os.getenv("PYWHATKIT_CLOSE_TIME", DEFAULT_PYWHATKIT_CLOSE_TIME))
GREETING_REPLY = f"Ola! Eu sou o {BOT_NAME}. Envie 'menu' para ver as opcoes."
HUMAN_SUPPORT_REPLY = (
    "Certo, vou registrar que voce quer falar com um atendente. "
    "Alguem da equipe deve responder assim que possivel."
)


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_text.lower().split())

def is_enabled(value: str | None) -> bool:
    return normalize_text(value or "") in {"1", "true", "sim", "yes", "on"}

def get_timezone() -> tzinfo:
    try:
        return ZoneInfo(BOT_TIMEZONE)
    except ZoneInfoNotFoundError:
        return timezone.utc

def current_time() -> str:
    now = datetime.now(get_timezone())
    return now.strftime("%d/%m/%Y %H:%M")

def menu_message() -> str:
    return (
        f"Menu do {BOT_NAME}\n"
        "1 - Horario de atendimento\n"
        "2 - Falar com um atendente\n"
        "3 - Status do bot\n\n"
        "Voce tambem pode enviar: oi, ajuda, horario, atendente ou status."
    )

_EXACT_REPLIES: dict[str, str | Callable[[], str]] = {
    "oi": GREETING_REPLY,
    "ola": GREETING_REPLY,
    "bom dia": GREETING_REPLY,
    "boa tarde": GREETING_REPLY,
    "boa noite": GREETING_REPLY,
    "menu": menu_message,
    "ajuda": menu_message,
    "help": menu_message,
    "opcoes": menu_message,
    "opcao": menu_message,
    "1": "Nosso atendimento funciona de segunda a sexta, das 09h as 18h.",
    "horario": "Nosso atendimento funciona de segunda a sexta, das 09h as 18h.",
    "horarios": "Nosso atendimento funciona de segunda a sexta, das 09h as 18h.",
    "atendimento": "Nosso atendimento funciona de segunda a sexta, das 09h as 18h.",
    "2": HUMAN_SUPPORT_REPLY,
    "humano": HUMAN_SUPPORT_REPLY,
    "atendente": HUMAN_SUPPORT_REPLY,
    "falar com atendente": HUMAN_SUPPORT_REPLY,
    "suporte": HUMAN_SUPPORT_REPLY,
    "3": lambda: f"{BOT_NAME} esta online. Hora do servidor: {current_time()}.",
    "status": lambda: f"{BOT_NAME} esta online. Hora do servidor: {current_time()}.",
    "online": lambda: f"{BOT_NAME} esta online. Hora do servidor: {current_time()}.",
}

_FALLBACK = (
    'Recebi sua mensagem: "{message}".\n\n'
    "Ainda estou aprendendo a responder esse assunto. "
    "Envie 'menu' para ver as opcoes disponiveis."
)

def build_reply(message: str) -> str:
    if not message or not message.strip():
        return "Recebi sua mensagem, mas ela veio sem texto. Pode enviar novamente?"

    handler = _EXACT_REPLIES.get(normalize_text(message))
    if handler is None:
        return _FALLBACK.format(message=message.strip())

    return handler() if callable(handler) else handler

def validate_phone(phone_number: str) -> str:
    clean_phone_number = phone_number.strip()
    digits = clean_phone_number[1:] if clean_phone_number.startswith("+") else clean_phone_number

    if not clean_phone_number.startswith("+") or not digits.isdigit():
        raise ValueError("Use o numero em formato internacional, exemplo: +5511999999999")

    return clean_phone_number

def send_whatsapp_message(
    phone_number: str,
    message: str,
    wait_time: int = DEFAULT_WAIT_TIME,
    close_tab: bool | None = None,
    close_time: int = DEFAULT_CLOSE_TIME,
) -> None:
    should_close_tab = close_tab

    if should_close_tab is None:
        should_close_tab = is_enabled(os.getenv("PYWHATKIT_CLOSE_TAB"))

    pywhatkit.sendwhatmsg_instantly(
        validate_phone(phone_number),
        message,
        wait_time,
        should_close_tab,
        close_time,
    )

def format_contact_phone(phone_number: str, default_country_code: str) -> str:
    if not phone_number.strip():
        raise ValueError("telefone vazio.")

    country_digits = digits_only(default_country_code)
    if not country_digits:
        raise ValueError("DDI padrao invalido.")

    return format_phone_with_country_code(phone_number, country_digits)

def format_phone_with_country_code(phone_number: str, country_digits: str) -> str:
    if phone_number.strip().startswith("+"):
        return validate_phone(f"+{digits_only(phone_number)}")

    phone_digits = digits_only(phone_number)
    if not phone_digits:
        raise ValueError("telefone sem digitos.")

    if phone_digits.startswith(country_digits):
        return validate_phone(f"+{phone_digits}")

    return validate_phone(f"+{country_digits}{phone_digits}")

def digits_only(value: str) -> str:
    return "".join(character for character in value if character.isdigit())

def render_contact_template(template: str, contact: ContactRow) -> str:
    fields = contact_template_fields(contact)
    validate_template_fields(template, fields)
    return template.format_map(fields)

def contact_template_fields(contact: ContactRow) -> dict[str, str]:
    fields = {
        template_field_name(header): value
        for header, value in contact.values.items()
        if template_field_name(header)
    }
    fields.update(
        {
            "linha": str(contact.row_number),
            "nome": contact.name,
            "telefone": contact.phone_number,
        }
    )
    return fields

def validate_template_fields(template: str, fields: dict[str, str]) -> None:
    for _, field_name, _, _ in Formatter().parse(template):
        validate_template_field(field_name, fields)

def validate_template_field(field_name: str | None, fields: dict[str, str]) -> None:
    if not field_name:
        return
    root_field = field_name.split(".", 1)[0].split("[", 1)[0]
    if root_field not in fields:
        raise ValueError(f"campo {{{root_field}}} nao existe na planilha.")

def template_field_name(value: str) -> str:
    text = normalize_text(value)
    return text.replace(" ", "_")

def wait_between_contacts(delay_seconds: float) -> None:
    if delay_seconds > 0:
        time.sleep(delay_seconds)