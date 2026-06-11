"""Servicos usados pelos endpoints FastAPI."""

from __future__ import annotations
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Event, Lock, Thread
from api_models import (
    ContactBatchRequest,
    ContactBatchResponse,
    ContactMessageResult,
    SendMessageRequest,
    WebBotStartRequest,
)
from contact_reader import ContactRow, load_contact_rows
from main import (
    build_reply,
    format_contact_phone,
    render_contact_template,
    send_whatsapp_message,
    validate_phone,
    wait_between_contacts,
)
from reader_msg import WhatsAppWebOptions, run_whatsapp_web_bot

class BotAlreadyRunningError(RuntimeError):
    """Indica tentativa de iniciar um bot ja ativo."""

class BotNotRunningError(RuntimeError):
    """Indica tentativa de parar um bot inativo."""

@dataclass(frozen=True)
class OutgoingMessage:
    phone_number: str
    message: str
    sent: bool

@dataclass(frozen=True)
class WebBotStatus:
    running: bool
    task_name: str
    started_at: datetime | None
    stopped_at: datetime | None
    logs: list[str]

class TaskLog:
    def __init__(self, max_entries: int = 200) -> None:
        self.entries: deque[str] = deque(maxlen=max_entries)
        self.lock = Lock()

    def append(self, message: str) -> None:
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        entry = f"{timestamp} {message}".strip()

        with self.lock:
            self.entries.append(entry)

    def recent(self, limit: int = 100) -> list[str]:
        with self.lock:
            entries = list(self.entries)

        return entries[-limit:]

class WhatsAppWebTaskManager:
    def __init__(self) -> None:
        self.log = TaskLog()
        self.lock = Lock()
        self.thread: Thread | None = None
        self.stop_event: Event | None = None
        self.task_name = ""
        self.started_at: datetime | None = None
        self.stopped_at: datetime | None = None

    def start(self, request: WebBotStartRequest) -> WebBotStatus:
        with self.lock:
            if self.is_running_locked():
                raise BotAlreadyRunningError("O bot do WhatsApp Web ja esta em execucao.")

            self.prepare_task()
            self.thread = Thread(target=self.run_task, args=(request,), daemon=True)
            self.thread.start()

        return self.status()

    def stop(self) -> WebBotStatus:
        with self.lock:
            if not self.is_running_locked() or self.stop_event is None:
                raise BotNotRunningError("O bot do WhatsApp Web nao esta em execucao.")

            self.stop_event.set()

        self.log.append("Parada solicitada.")
        return self.status()

    def status(self) -> WebBotStatus:
        with self.lock:
            running = self.is_running_locked()
            return WebBotStatus(
                running=running,
                task_name=self.task_name,
                started_at=self.started_at,
                stopped_at=self.stopped_at,
                logs=self.log.recent(),
            )

    def prepare_task(self) -> None:
        self.stop_event = Event()
        self.task_name = "WhatsApp Web"
        self.started_at = datetime.now(timezone.utc)
        self.stopped_at = None
        self.log.append("Iniciando bot do WhatsApp Web.")

    def run_task(self, request: WebBotStartRequest) -> None:
        try:
            self.run_whatsapp_web(request)
        except SystemExit as exc:
            self.log.append(f"Bot encerrado: {exc}")
        except Exception as exc:
            self.log.append(f"Erro no bot: {exc}")
        finally:
            self.finish_task()

    def run_whatsapp_web(self, request: WebBotStartRequest) -> None:
        options = self.build_web_options(request)
        fixed_reply = request.fixed_reply.strip()

        def reply_to(incoming_message: str) -> str:
            return fixed_reply or build_reply(incoming_message)

        run_whatsapp_web_bot(reply_to, options)

    def build_web_options(self, request: WebBotStartRequest) -> WhatsAppWebOptions:
        return WhatsAppWebOptions(
            session_dir=request.session_dir,
            poll_interval_ms=int(request.poll_interval * 1000),
            print_only=request.print_only,
            stop_event=self.stop_event,
            log_message=self.log.append,
        )

    def finish_task(self) -> None:
        self.log.append("Bot do WhatsApp Web encerrado.")

        with self.lock:
            self.thread = None
            self.stop_event = None
            self.stopped_at = datetime.now(timezone.utc)

    def is_running_locked(self) -> bool:
        return bool(self.thread and self.thread.is_alive())

def build_outgoing_message(request: SendMessageRequest) -> OutgoingMessage:
    phone_number = validate_phone(request.phone_number)
    message = resolve_outgoing_message(request.message, request.incoming_message)

    if not request.print_only:
        send_whatsapp_message(
            phone_number,
            message,
            request.wait_time,
            request.close_tab,
            request.close_time,
        )
    return OutgoingMessage(
        phone_number=phone_number,
        message=message,
        sent=not request.print_only,
    )

def resolve_outgoing_message(message: str, incoming_message: str) -> str:
    if message.strip():
        return message
    if incoming_message.strip():
        return build_reply(incoming_message)
    raise ValueError("Informe message ou incoming_message.")

def preview_contact_messages(request: ContactBatchRequest) -> ContactBatchResponse:
    contacts = load_selected_contacts(request)
    results = [
        build_contact_result(contact, request, "preview")
        for contact in contacts
    ]
    return build_contact_response(results)

def send_contact_messages(request: ContactBatchRequest) -> ContactBatchResponse:
    contacts = load_selected_contacts(request)
    results = []

    for contact in contacts:
        results.append(send_contact_message(contact, request))

    return build_contact_response(results)

def load_selected_contacts(request: ContactBatchRequest) -> list[ContactRow]:
    contacts = load_contact_rows(
        request.contacts_path,
        request.phone_column,
        request.name_column,
        request.message_column,
    )

    if request.limit <= 0:
        return contacts
    return contacts[:request.limit]

def send_contact_message(
    contact: ContactRow,
    request: ContactBatchRequest,
) -> ContactMessageResult:
    result = build_contact_result(contact, request, success_status(request))
    if result.status in {"skipped", "preview"}:
        return result
    try:
        send_whatsapp_message(
            result.phone_number,
            result.message,
            request.wait_time,
            request.close_tab,
            request.close_time,
        )
        wait_between_contacts(request.contact_delay)
    except Exception as exc:
        return change_contact_status(result, "failed", str(exc))
    return result

def success_status(request: ContactBatchRequest) -> str:
    return "preview" if request.print_only else "sent"

def build_contact_result(
    contact: ContactRow,
    request: ContactBatchRequest,
    status: str,
) -> ContactMessageResult:
    try:
        phone_number = format_contact_phone(contact.phone_number, request.default_country_code)
        message = resolve_contact_message(contact, request)
    except ValueError as exc:
        return skipped_contact_result(contact, str(exc))

    return ContactMessageResult(
        row_number=contact.row_number,
        name=contact.name,
        phone_number=phone_number,
        message=message,
        status=status,
    )

def skipped_contact_result(contact: ContactRow, error: str) -> ContactMessageResult:
    return ContactMessageResult(
        row_number=contact.row_number,
        name=contact.name,
        phone_number=contact.phone_number,
        message="",
        status="skipped",
        error=error,
    )

def resolve_contact_message(contact: ContactRow, request: ContactBatchRequest) -> str:
    template = request.message_template or contact.message

    if template:
        return render_contact_template(template, contact)

    if request.incoming_message:
        return build_reply(request.incoming_message)

    raise ValueError("sem mensagem; informe message_template ou uma coluna mensagem.")

def change_contact_status(
    result: ContactMessageResult,
    status: str,
    error: str,
) -> ContactMessageResult:
    return ContactMessageResult(
        row_number=result.row_number,
        name=result.name,
        phone_number=result.phone_number,
        message=result.message,
        status=status,
        error=error,
    )

def build_contact_response(results: list[ContactMessageResult]) -> ContactBatchResponse:
    counts = Counter(result.status for result in results)

    return ContactBatchResponse(
        total=len(results),
        preview=counts["preview"],
        sent=counts["sent"],
        skipped=counts["skipped"],
        failed=counts["failed"],
        results=results,
    )