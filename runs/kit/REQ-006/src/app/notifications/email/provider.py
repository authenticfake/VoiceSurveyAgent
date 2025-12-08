from __future__ import annotations

import smtplib
import ssl
import uuid
from email.message import EmailMessage
from typing import Protocol

from .models import EmailSendRequest, EmailSendResult


class EmailProvider(Protocol):
    """Minimal provider contract used by the worker."""

    def send_email(self, request: EmailSendRequest) -> EmailSendResult:  # pragma: no cover - interface
        ...


class SMTPEmailProvider:
    """TLS-enabled SMTP email provider."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
        sender: str | None = None,
        use_tls: bool = True,
        timeout: int = 10,
    ):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._sender = sender
        self._use_tls = use_tls
        self._timeout = timeout
        self._ssl_context = ssl.create_default_context()

    def send_email(self, request: EmailSendRequest) -> EmailSendResult:
        msg = EmailMessage()
        msg["Subject"] = request.subject
        msg["To"] = request.to
        msg["From"] = self._sender or self._username
        if request.reply_to:
            msg["Reply-To"] = request.reply_to
        msg.set_content(request.text_body or " ")
        if request.html_body:
            msg.add_alternative(request.html_body, subtype="html")

        with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as client:
            if self._use_tls:
                client.starttls(context=self._ssl_context)
            if self._username and self._password:
                client.login(self._username, self._password)
            client.send_message(msg)

        message_id = msg.get("Message-ID") or f"msg-{uuid.uuid4()}"
        return EmailSendResult(message_id=message_id, provider="smtp")