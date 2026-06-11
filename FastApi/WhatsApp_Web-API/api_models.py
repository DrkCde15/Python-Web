"""Modelos de entrada e saida da API HTTP."""

from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field
from main import (
    DEFAULT_CLOSE_TIME,
    DEFAULT_CONTACT_DELAY,
    DEFAULT_COUNTRY_CODE,
    DEFAULT_WAIT_TIME,
    DEFAULT_WEB_POLL_INTERVAL,
    DEFAULT_WEB_SESSION_DIR,
)

class ApiInfoResponse(BaseModel):
    name: str
    version: str
    endpoints: list[str]

class HealthResponse(BaseModel):
    status: str

class ReplyRequest(BaseModel):
    message: str = Field(..., min_length=1)

class ReplyResponse(BaseModel):
    reply: str

class SendMessageRequest(BaseModel):
    phone_number: str = Field(..., min_length=1)
    message: str = ""
    incoming_message: str = ""
    wait_time: int = Field(DEFAULT_WAIT_TIME, ge=1)
    close_tab: bool | None = None
    close_time: int = Field(DEFAULT_CLOSE_TIME, ge=0)
    print_only: bool = False

class SendMessageResponse(BaseModel):
    phone_number: str
    message: str
    sent: bool

class ContactBatchRequest(BaseModel):
    contacts_path: str = Field(..., min_length=1)
    message_template: str = ""
    incoming_message: str = ""
    phone_column: str = ""
    name_column: str = ""
    message_column: str = ""
    default_country_code: str = DEFAULT_COUNTRY_CODE
    limit: int = Field(0, ge=0)
    contact_delay: float = Field(DEFAULT_CONTACT_DELAY, ge=0)
    wait_time: int = Field(DEFAULT_WAIT_TIME, ge=1)
    close_tab: bool | None = None
    close_time: int = Field(DEFAULT_CLOSE_TIME, ge=0)
    print_only: bool = False

ContactMessageStatus = Literal["preview", "sent", "skipped", "failed"]

class ContactMessageResult(BaseModel):
    row_number: int
    name: str
    phone_number: str
    message: str
    status: ContactMessageStatus
    error: str = ""

class ContactBatchResponse(BaseModel):
    total: int
    preview: int
    sent: int
    skipped: int
    failed: int
    results: list[ContactMessageResult]

class WebBotStartRequest(BaseModel):
    session_dir: str = Field(DEFAULT_WEB_SESSION_DIR, min_length=1)
    poll_interval: float = Field(DEFAULT_WEB_POLL_INTERVAL, gt=0)
    fixed_reply: str = ""
    print_only: bool = False

class WebBotStatusResponse(BaseModel):
    running: bool
    task_name: str
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    logs: list[str]

class WebBotLogsResponse(BaseModel):
    logs: list[str]