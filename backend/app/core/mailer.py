"""Sends plain-text email through SMTP. In development this is Mailpit (a fake inbox).

These functions are called from FastAPI BackgroundTasks, AFTER the HTTP response,
so a slow mail server cannot reveal whether an account exists."""
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.mail_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, int(settings.smtp_port), timeout=10) as smtp:
            smtp.send_message(msg)
    except Exception as exc:  # never crash a request because mail failed; never log the link
        logger.error("email_send_failed type=%s", type(exc).__name__)


def _link(path: str, token: str) -> str:
    # The token sits after "#": browsers do not send it to servers or in Referer headers.
    return f"{settings.frontend_origin}{path}#token={token}"


def send_reset_email(to: str, token: str) -> None:
    send_email(
        to,
        "Reset your SecureSearch AI password",
        "We received a request to reset your password.\n\n"
        f"Open this link within {settings.reset_token_minutes} minutes:\n"
        f"{_link('/reset-password', token)}\n\n"
        "If you did not ask for this, ignore this email. Your password stays the same.\n",
    )


def send_invite_email(to: str, full_name: str, token: str) -> None:
    send_email(
        to,
        "You have been invited to SecureSearch AI",
        f"Hello {full_name},\n\n"
        "An administrator created an account for you. Set your password within "
        f"{settings.invite_token_hours} hours:\n"
        f"{_link('/reset-password', token)}\n",
    )
