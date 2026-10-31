"""Telegram delivery of digests and alerts (FR-9, ADR-0025); email deferred."""

from ripple.notify.contracts import (
    AlertKind,
    DeliveryLog,
    MessageReceipt,
    Thresholds,
    Transport,
    UserDirectory,
)
from ripple.notify.digest import DigestService
from ripple.notify.render import Alert, alerts_for, render_alert, render_digest
from ripple.notify.telegram import TelegramTransport

__all__ = [
    "Alert",
    "AlertKind",
    "DeliveryLog",
    "DigestService",
    "MessageReceipt",
    "TelegramTransport",
    "Thresholds",
    "Transport",
    "UserDirectory",
    "alerts_for",
    "render_alert",
    "render_digest",
]
