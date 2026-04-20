"""Feishu (Lark) outbound messaging channel.

Uses Feishu's in-house app model (app_id + app_secret) to obtain a
``tenant_access_token`` (cached for ~5 minutes) and then posts text /
interactive-card messages via the Open Platform APIs.

Callback handling supports:
- ``url_verification`` (echo back the ``challenge`` string).
- ``card.action.trigger`` / legacy ``action`` payloads (Approve / Reject).
- Signature verification via the optional ``encrypt_key`` /
  ``verification_token`` (Feishu's Event Subscription signing scheme).
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

import httpx

from .base import BaseChannel, ChannelSendResult

logger = logging.getLogger(__name__)

# Feishu / Lark endpoints.  Feishu uses open.feishu.cn; Lark uses
# open.larksuite.com — both are API-compatible.  Override via config key
# ``base_url`` if needed.
DEFAULT_BASE_URL = "https://open.feishu.cn"

TOKEN_CACHE_TTL_SECONDS = 300  # 5 minutes; actual token lives for 2 hours.


class FeishuChannel(BaseChannel):
    """Feishu / Lark channel.

    Expected ``config`` shape::

        {
            "app_id": "cli_xxx",
            "app_secret": "xxx",
            "chat_id": "oc_xxx",            # default target chat (group)
            "verification_token": "...",    # optional
            "encrypt_key": "...",           # optional (enables AES+sign)
            "base_url": "https://...",      # optional, defaults to Feishu
        }
    """

    type = "feishu"

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    # ---- Internal helpers ---------------------------------------------------

    def _base_url(self) -> str:
        return str(self.config.get("base_url") or DEFAULT_BASE_URL).rstrip("/")

    async def _fetch_tenant_access_token(
        self, client: httpx.AsyncClient | None = None
    ) -> str:
        """Return a cached ``tenant_access_token``, refetching if stale."""
        now = time.time()
        if self._token and now < self._token_expires_at:
            return self._token

        app_id = str(self.config.get("app_id", "")).strip()
        app_secret = str(self.config.get("app_secret", "")).strip()
        if not app_id or not app_secret:
            raise RuntimeError(
                "Feishu channel is missing app_id or app_secret in config"
            )

        url = f"{self._base_url()}/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": app_id, "app_secret": app_secret}

        own_client = client is None
        if client is None:
            client = httpx.AsyncClient(timeout=15)
        try:
            resp = await client.post(url, json=payload)
            data = resp.json()
        finally:
            if own_client:
                await client.aclose()

        if not isinstance(data, dict) or data.get("code") != 0:
            raise RuntimeError(
                f"Failed to obtain tenant_access_token: {data!r}"
            )
        token = data.get("tenant_access_token")
        if not isinstance(token, str) or not token:
            raise RuntimeError("tenant_access_token missing from response")

        self._token = token
        self._token_expires_at = now + TOKEN_CACHE_TTL_SECONDS
        return token

    # ---- Public API: discovery ---------------------------------------------

    async def list_chats(
        self,
        *,
        page_size: int = 100,
        client: httpx.AsyncClient | None = None,
    ) -> list[dict[str, Any]]:
        """List the groups (chats) the configured app/bot is a member of.

        Calls Feishu's ``GET /open-apis/im/v1/chats`` endpoint. The bot's app
        must have the ``im:chat:readonly`` or ``im:chat`` scope, and the bot
        must have already been added to the group(s).

        Returns the raw ``items`` array from the response — each item is a
        dict with keys like ``chat_id``, ``name``, ``avatar``, ``description``,
        ``external``, ``tenant_key``, etc.

        Raises ``RuntimeError`` with a human-readable message on any API
        failure (bad credentials, network error, non-zero Feishu code).
        """
        own_client = client is None
        if client is None:
            client = httpx.AsyncClient(timeout=15)
        try:
            token = await self._fetch_tenant_access_token(client=client)
            url = f"{self._base_url()}/open-apis/im/v1/chats"
            resp = await client.get(
                url,
                params={"page_size": page_size},
                headers={"Authorization": f"Bearer {token}"},
            )
            data = resp.json()
        finally:
            if own_client:
                await client.aclose()

        if not isinstance(data, dict) or data.get("code") != 0:
            msg: str | None = None
            if isinstance(data, dict):
                raw_msg = data.get("msg")
                if isinstance(raw_msg, str):
                    msg = raw_msg
            raise RuntimeError(
                f"Feishu list_chats failed: {msg or data!r}"
            )

        payload = data.get("data")
        if not isinstance(payload, dict):
            return []
        items = payload.get("items")
        if not isinstance(items, list):
            return []
        return [item for item in items if isinstance(item, dict)]

    # ---- Public API: send ---------------------------------------------------

    async def send_message(self, payload: dict[str, Any]) -> ChannelSendResult:
        """Send a Feishu message.

        ``payload`` must contain ``chat_id`` (or fall back to the
        channel's default ``chat_id``) and either:
        - ``msg_type`` + ``content``, or
        - ``msg_type="interactive"`` + ``card``.
        """
        chat_id = payload.get("chat_id") or self.config.get("chat_id")
        if not chat_id:
            return ChannelSendResult(
                ok=False, error="chat_id is required to send a Feishu message"
            )

        msg_type = str(payload.get("msg_type") or "text")
        if msg_type == "interactive":
            content = payload.get("card")
            if not isinstance(content, dict):
                return ChannelSendResult(
                    ok=False,
                    error="interactive message requires a 'card' dict",
                )
            content_json = json.dumps(content, ensure_ascii=False)
        else:
            raw_content = payload.get("content")
            if isinstance(raw_content, dict):
                content_json = json.dumps(raw_content, ensure_ascii=False)
            elif isinstance(raw_content, str):
                # Feishu expects a JSON string even for plain text msgs.
                content_json = json.dumps(
                    {"text": raw_content}, ensure_ascii=False
                )
            else:
                return ChannelSendResult(
                    ok=False,
                    error="content must be a string or dict",
                )

        body = {
            "receive_id": chat_id,
            "msg_type": msg_type,
            "content": content_json,
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                token = await self._fetch_tenant_access_token(client=client)
                resp = await client.post(
                    f"{self._base_url()}/open-apis/im/v1/messages",
                    params={"receive_id_type": "chat_id"},
                    headers={"Authorization": f"Bearer {token}"},
                    json=body,
                )
                data = resp.json()
        except Exception as exc:  # pragma: no cover - network edge cases
            logger.exception("Feishu send_message failed")
            return ChannelSendResult(ok=False, error=f"{type(exc).__name__}: {exc}")

        if isinstance(data, dict) and data.get("code") == 0:
            return ChannelSendResult(ok=True, raw=data)
        return ChannelSendResult(
            ok=False,
            error=f"Feishu API error: {data}",
            raw=data if isinstance(data, dict) else {},
        )

    async def send_text(self, chat_id: str, text: str) -> ChannelSendResult:
        """Convenience wrapper — send a plain-text message."""
        return await self.send_message(
            {
                "chat_id": chat_id,
                "msg_type": "text",
                "content": {"text": text},
            }
        )

    async def send_interactive_card(
        self, chat_id: str, card_spec: dict[str, Any]
    ) -> ChannelSendResult:
        """Convenience wrapper — send an interactive card."""
        return await self.send_message(
            {
                "chat_id": chat_id,
                "msg_type": "interactive",
                "card": card_spec,
            }
        )

    # ---- Public API: callbacks ---------------------------------------------

    async def verify_signature(
        self,
        body: bytes,
        headers: dict[str, str],
    ) -> bool:
        """Verify a Feishu callback signature.

        Feishu's Event Subscription v2 signs the payload with the
        ``encrypt_key`` using the scheme::

            signature = sha256(timestamp + nonce + encrypt_key + body)

        If ``encrypt_key`` is not configured, no signature is verified
        (returns ``True``) — this is safe only when the callback URL is
        secret / unguessable.  Recommended for production: always set
        ``encrypt_key``.

        Header names are matched case-insensitively.
        """
        encrypt_key = str(self.config.get("encrypt_key") or "").strip()
        if not encrypt_key:
            # No key configured — nothing to verify.
            return True

        lower_headers = {k.lower(): v for k, v in headers.items()}
        timestamp = lower_headers.get("x-lark-request-timestamp")
        nonce = lower_headers.get("x-lark-request-nonce")
        provided = lower_headers.get("x-lark-signature")
        if not timestamp or not nonce or not provided:
            return False

        m = hashlib.sha256()
        m.update(timestamp.encode("utf-8"))
        m.update(nonce.encode("utf-8"))
        m.update(encrypt_key.encode("utf-8"))
        m.update(body)
        expected = m.hexdigest()
        return _constant_time_eq(expected, provided)

    async def handle_callback(
        self,
        body: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        """Process a Feishu callback (url_verification or card action).

        For URL verification handshake::

            body = {"type": "url_verification", "challenge": "xxx"}
            -> {"response": {"challenge": "xxx"}, "event": {...}}

        For card interactions (Approve/Reject button click)::

            body = {"action": {"value": {"confirmation_id": "x",
                                          "decision": "approve"}},
                    "open_id": "ou_xxx", ...}
            -> {"response": {}, "event": {...}}
        """
        # 1. URL verification handshake (Feishu sends this once to prove
        #    the callback URL is reachable and owned by the app).
        if body.get("type") == "url_verification":
            challenge = str(body.get("challenge", ""))
            return {
                "response": {"challenge": challenge},
                "event": {
                    "kind": "url_verification",
                    "action": None,
                    "confirmation_id": None,
                    "open_id": None,
                },
            }

        # 2. Card action — either the new schema ("schema=2.0", nested
        #    under "event.action") or the legacy schema (flat "action.value").
        action_value: dict[str, Any] | None = None
        open_id: str | None = None

        # Legacy schema.
        if isinstance(body.get("action"), dict):
            legacy_action = body["action"]
            raw_value = legacy_action.get("value")
            if isinstance(raw_value, dict):
                action_value = raw_value
            elif isinstance(raw_value, str):
                try:
                    parsed = json.loads(raw_value)
                    if isinstance(parsed, dict):
                        action_value = parsed
                except json.JSONDecodeError:
                    pass
            open_id = body.get("open_id") or body.get("operator_id")

        # New schema (event.action.value).
        event_obj = body.get("event") if isinstance(body.get("event"), dict) else None
        if action_value is None and isinstance(event_obj, dict):
            nested_action = event_obj.get("action")
            if isinstance(nested_action, dict):
                raw_value = nested_action.get("value")
                if isinstance(raw_value, dict):
                    action_value = raw_value
            operator = event_obj.get("operator")
            if isinstance(operator, dict):
                open_id = operator.get("open_id") or operator.get("union_id")

        if action_value is None:
            return {
                "response": {},
                "event": {
                    "kind": "unknown",
                    "action": None,
                    "confirmation_id": None,
                    "open_id": open_id,
                },
            }

        decision_raw = action_value.get("decision") or action_value.get("action")
        decision = str(decision_raw).lower() if decision_raw else None
        if decision in ("approve", "approved", "yes"):
            decision = "approve"
        elif decision in ("reject", "rejected", "no", "deny"):
            decision = "reject"
        else:
            decision = None

        confirmation_id = action_value.get("confirmation_id")

        return {
            "response": {},
            "event": {
                "kind": "card_action",
                "action": decision,
                "confirmation_id": (
                    str(confirmation_id) if confirmation_id else None
                ),
                "open_id": open_id,
            },
        }


def build_confirmation_card(
    *,
    confirmation_id: str,
    title: str,
    summary: str,
    tool_name: str,
    tool_args_preview: str,
    approve_text: str = "Approve",
    reject_text: str = "Reject",
) -> dict[str, Any]:
    """Build a Feishu interactive card spec for a confirmation gate.

    The card has two buttons whose ``value`` payloads carry the
    ``confirmation_id`` back to our callback endpoint so we can look up
    and update the pending request.
    """
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": title[:100]},
            "template": "orange",
        },
        "elements": [
            {
                "tag": "markdown",
                "content": summary[:2000],
            },
            {
                "tag": "div",
                "fields": [
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"**Tool**\n{tool_name}",
                        },
                    },
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"**Request ID**\n`{confirmation_id}`",
                        },
                    },
                ],
            },
            {
                "tag": "hr",
            },
            {
                "tag": "markdown",
                "content": f"**Arguments**\n```\n{tool_args_preview[:800]}\n```",
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": approve_text},
                        "type": "primary",
                        "value": {
                            "confirmation_id": confirmation_id,
                            "decision": "approve",
                        },
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": reject_text},
                        "type": "danger",
                        "value": {
                            "confirmation_id": confirmation_id,
                            "decision": "reject",
                        },
                    },
                ],
            },
        ],
    }


def _constant_time_eq(a: str, b: str) -> bool:
    """Constant-time string comparison (prevents timing attacks)."""
    if len(a) != len(b):
        # Still run the loop to equalize time spent.
        a_b = a.encode("utf-8")
        b_b = b.encode("utf-8")
        # Pad shorter to longer.
        mx = max(len(a_b), len(b_b))
        a_b = a_b.ljust(mx, b"\x00")
        b_b = b_b.ljust(mx, b"\x00")
        result = 1
        for x, y in zip(a_b, b_b):
            result |= x ^ y
        return False
    result = 0
    for x, y in zip(a.encode("utf-8"), b.encode("utf-8")):
        result |= x ^ y
    return result == 0


__all__ = [
    "FeishuChannel",
    "build_confirmation_card",
    "DEFAULT_BASE_URL",
    "TOKEN_CACHE_TTL_SECONDS",
]
