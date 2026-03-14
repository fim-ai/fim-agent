"""Message push notification system.

Supports Email, Slack, Lark (Feishu), and WeCom (Enterprise WeChat)
providers.  Providers are auto-discovered from environment variables.
"""

from .base import NotificationMessage, NotificationProvider
from .registry import (
    NotificationRegistry,
    get_notification_registry,
    reset_notification_registry,
)

__all__ = [
    "NotificationMessage",
    "NotificationProvider",
    "NotificationRegistry",
    "get_notification_registry",
    "reset_notification_registry",
]
