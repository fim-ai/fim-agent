"""Adapter that converts ConnectorActions into FIM Agent tools."""

from __future__ import annotations

import base64
import json
import logging
import re
from typing import Any

import httpx

from fim_agent.core.tool.base import BaseTool

logger = logging.getLogger(__name__)


class ConnectorToolAdapter(BaseTool):
    """Wraps a single ConnectorAction as a BaseTool.

    Tool names use format: ``{connector_name}__{action_name}``
    Category: ``"connector"``
    """

    def __init__(
        self,
        connector_name: str,
        connector_base_url: str,
        connector_auth_type: str,
        connector_auth_config: dict[str, Any] | None,
        action_name: str,
        action_description: str,
        action_method: str,
        action_path: str,
        action_parameters_schema: dict[str, Any] | None,
        action_request_body_template: dict[str, Any] | None,
        action_response_extract: str | None,
        action_requires_confirmation: bool,
        auth_credentials: dict[str, str] | None = None,
    ) -> None:
        safe_connector = re.sub(r"[^a-zA-Z0-9]", "_", connector_name.lower()).strip("_")
        safe_action = re.sub(r"[^a-zA-Z0-9]", "_", action_name.lower()).strip("_")
        self._name = f"{safe_connector}__{safe_action}"
        self._description = action_description or f"{action_method} {action_path}"
        self._method = action_method.upper()
        self._base_url = connector_base_url.rstrip("/")
        self._path = action_path
        self._parameters_schema_val = action_parameters_schema or {
            "type": "object",
            "properties": {},
            "required": [],
        }
        self._request_body_template = action_request_body_template
        self._response_extract = action_response_extract
        self._requires_confirmation = action_requires_confirmation
        self._auth_type = connector_auth_type
        self._auth_config = connector_auth_config or {}
        self._auth_credentials = auth_credentials or {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def category(self) -> str:
        return "connector"

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return self._parameters_schema_val

    async def run(self, **kwargs: Any) -> str:
        """Execute the HTTP request to the target system."""
        # 1. Build URL with path parameters
        path = self._path
        path_params = re.findall(r"\{(\w+)\}", path)
        for param in path_params:
            if param in kwargs:
                path = path.replace(f"{{{param}}}", str(kwargs.pop(param)))

        url = f"{self._base_url}{path}"

        # 2. Build headers with auth
        headers: dict[str, str] = {"Accept": "application/json"}
        self._inject_auth(headers)

        # 3. Build request
        query_params: dict[str, Any] = {}
        body: Any = None

        if self._method in ("GET", "DELETE"):
            query_params = {k: v for k, v in kwargs.items() if v is not None}
        else:
            if self._request_body_template:
                body = self._render_template(self._request_body_template, kwargs)
            else:
                body = kwargs if kwargs else None
            headers["Content-Type"] = "application/json"

        # 4. Execute request
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.request(
                    method=self._method,
                    url=url,
                    headers=headers,
                    params=query_params if query_params else None,
                    json=body,
                )

                content = resp.text
                if resp.status_code >= 400:
                    return f"[HTTP {resp.status_code}] {content[:2000]}"

                # Apply response extract (jmespath) if configured
                if (
                    self._response_extract
                    and resp.headers.get("content-type", "").startswith("application/json")
                ):
                    try:
                        import jmespath  # type: ignore[import-untyped]

                        data = resp.json()
                        extracted = jmespath.search(self._response_extract, data)
                        if extracted is not None:
                            if isinstance(extracted, str):
                                return extracted
                            return json.dumps(extracted, ensure_ascii=False, indent=2)
                    except ImportError:
                        logger.debug(
                            "jmespath not installed — skipping response_extract"
                        )
                    except Exception:
                        pass  # Fall through to raw response

                # Truncate long responses
                max_chars = 20_000
                if len(content) > max_chars:
                    content = content[:max_chars] + f"\n\n[Truncated -- {len(content)} chars total]"
                return content

        except httpx.TimeoutException:
            return "[Timeout] Request exceeded 30 seconds."
        except httpx.RequestError as exc:
            return f"[Error] {type(exc).__name__}: {exc}"

    def _inject_auth(self, headers: dict[str, str]) -> None:
        """Inject authentication into request headers."""
        creds = self._auth_credentials

        if self._auth_type == "bearer":
            token = creds.get("token", "")
            if token:
                prefix = self._auth_config.get("token_prefix", "Bearer")
                headers["Authorization"] = f"{prefix} {token}"
        elif self._auth_type == "api_key":
            header_name = self._auth_config.get("header_name", "X-API-Key")
            key = creds.get("api_key", "")
            if key:
                headers[header_name] = key
        elif self._auth_type == "basic":
            username = creds.get("username", "")
            password = creds.get("password", "")
            encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"

    @staticmethod
    def _render_template(template: dict, params: dict) -> dict:
        """Replace ``{{param}}`` placeholders in body template with actual values."""
        raw = json.dumps(template)
        for key, value in params.items():
            placeholder = f"{{{{{key}}}}}"
            if isinstance(value, str):
                raw = raw.replace(f'"{placeholder}"', json.dumps(value))
                raw = raw.replace(placeholder, value)
            else:
                raw = raw.replace(f'"{placeholder}"', json.dumps(value))
        return json.loads(raw)
