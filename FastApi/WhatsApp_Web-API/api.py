"""API FastAPI para controlar o bot de WhatsApp."""

from __future__ import annotations
from fastapi import FastAPI, HTTPException, status
from api_models import (
    ApiInfoResponse,
    ContactBatchRequest,
    ContactBatchResponse,
    HealthResponse,
    ReplyRequest,
    ReplyResponse,
    SendMessageRequest,
    SendMessageResponse,
    WebBotLogsResponse,
    WebBotStartRequest,
    WebBotStatusResponse,
)
from api_services import (
    BotAlreadyRunningError,
    BotNotRunningError,
    WhatsAppWebTaskManager,
    build_outgoing_message,
    preview_contact_messages,
    send_contact_messages,
)
from contact_reader import ContactSheetError
from main import build_reply

API_ENDPOINTS = [
    "GET /",
    "GET /health",
    "POST /messages/reply",
    "POST /messages/send",
    "POST /contacts/preview",
    "POST /contacts/send",
    "POST /web-bot/start",
    "POST /web-bot/stop",
    "GET /web-bot/status",
    "GET /web-bot/logs",
]

app = FastAPI(
    title="WhatsApp Web API",
    description="API HTTP para gerar respostas e controlar o bot de WhatsApp Web.",
    version="1.0.0",
)
web_bot_manager = WhatsAppWebTaskManager()

@app.get("/", response_model=ApiInfoResponse)
def read_api_info() -> ApiInfoResponse:
    return ApiInfoResponse(
        name="WhatsApp Web API",
        version=app.version,
        endpoints=API_ENDPOINTS,
    )

@app.get("/health", response_model=HealthResponse)
def read_health() -> HealthResponse:
    return HealthResponse(status="ok")

@app.post("/messages/reply", response_model=ReplyResponse)
def create_reply(request: ReplyRequest) -> ReplyResponse:
    return ReplyResponse(reply=build_reply(request.message))

@app.post("/messages/send", response_model=SendMessageResponse)
def send_message(request: SendMessageRequest) -> SendMessageResponse:
    try:
        outgoing_message = build_outgoing_message(request)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
    except Exception as exc:
        raise server_error(f"Falha ao enviar mensagem: {exc}") from exc

    return SendMessageResponse(
        phone_number=outgoing_message.phone_number,
        message=outgoing_message.message,
        sent=outgoing_message.sent,
    )

@app.post("/contacts/preview", response_model=ContactBatchResponse)
def preview_contacts(request: ContactBatchRequest) -> ContactBatchResponse:
    try:
        return preview_contact_messages(request)
    except (ContactSheetError, ValueError) as exc:
        raise bad_request(str(exc)) from exc

@app.post("/contacts/send", response_model=ContactBatchResponse)
def send_contacts(request: ContactBatchRequest) -> ContactBatchResponse:
    try:
        return send_contact_messages(request)
    except (ContactSheetError, ValueError) as exc:
        raise bad_request(str(exc)) from exc

@app.post("/web-bot/start", response_model=WebBotStatusResponse)
def start_web_bot(request: WebBotStartRequest) -> WebBotStatusResponse:
    try:
        bot_status = web_bot_manager.start(request)
    except BotAlreadyRunningError as exc:
        raise conflict(str(exc)) from exc
    return WebBotStatusResponse(**bot_status.__dict__)

@app.post("/web-bot/stop", response_model=WebBotStatusResponse)
def stop_web_bot() -> WebBotStatusResponse:
    try:
        bot_status = web_bot_manager.stop()
    except BotNotRunningError as exc:
        raise conflict(str(exc)) from exc
    return WebBotStatusResponse(**bot_status.__dict__)

@app.get("/web-bot/status", response_model=WebBotStatusResponse)
def read_web_bot_status() -> WebBotStatusResponse:
    bot_status = web_bot_manager.status()
    return WebBotStatusResponse(**bot_status.__dict__)

@app.get("/web-bot/logs", response_model=WebBotLogsResponse)
def read_web_bot_logs() -> WebBotLogsResponse:
    return WebBotLogsResponse(logs=web_bot_manager.log.recent())

def bad_request(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=message,
    )

def conflict(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=message,
    )

def server_error(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=message,
    )