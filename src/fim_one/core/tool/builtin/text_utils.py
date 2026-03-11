"""Built-in tool for common text transformation utilities."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import re
import uuid
from typing import Any
from urllib.parse import quote, unquote

from ..base import BaseTool


class TextUtilsTool(BaseTool):
    """Common text transformation operations — encoding, hashing, regex, and more."""

    @property
    def name(self) -> str:
        return "text_utils"

    @property
    def display_name(self) -> str:
        return "Text Utilities"

    @property
    def category(self) -> str:
        return "general"

    @property
    def description(self) -> str:
        return (
            "Common text transformation utilities. "
            "Supported operations: "
            '"base64_encode" — encode text to Base64; '
            '"base64_decode" — decode Base64 to text; '
            '"hex_encode" — encode text to hex; '
            '"hex_decode" — decode hex to text; '
            '"md5" — compute MD5 hash; '
            '"sha1" — compute SHA-1 hash; '
            '"sha256" — compute SHA-256 hash; '
            '"uuid" — generate a random UUID v4 (no text input needed); '
            '"regex_match" — find all regex matches (requires pattern); '
            '"regex_replace" — replace regex pattern (requires pattern and replacement); '
            '"url_encode" — percent-encode a URL component; '
            '"url_decode" — decode a percent-encoded string; '
            '"word_count" — count words; '
            '"char_count" — count characters; '
            '"truncate" — truncate to max_length chars (requires max_length); '
            '"to_upper" / "to_lower" / "title_case" / "strip" — case and whitespace; '
            '"slugify" — convert to URL-safe slug. '
            "All operations require the 'text' parameter except 'uuid'."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": [
                        "base64_encode", "base64_decode",
                        "hex_encode", "hex_decode",
                        "md5", "sha1", "sha256",
                        "uuid",
                        "regex_match", "regex_replace",
                        "url_encode", "url_decode",
                        "word_count", "char_count",
                        "truncate",
                        "to_upper", "to_lower", "title_case", "strip",
                        "slugify",
                    ],
                    "description": "The text operation to perform.",
                },
                "text": {
                    "type": "string",
                    "description": "Input text. Not required for 'uuid'.",
                },
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern. Required for regex_match and regex_replace.",
                },
                "replacement": {
                    "type": "string",
                    "description": "Replacement string. Required for regex_replace.",
                },
                "max_length": {
                    "type": "integer",
                    "description": "Max character count. Required for truncate.",
                },
            },
            "required": ["operation"],
        }

    async def run(self, **kwargs: Any) -> str:
        return await asyncio.to_thread(self._run_sync, **kwargs)

    def _run_sync(self, **kwargs: Any) -> str:
        op: str = kwargs.get("operation", "").strip()
        text: str = kwargs.get("text", "")
        pattern: str = kwargs.get("pattern", "")
        replacement: str = kwargs.get("replacement", "")
        max_length: int | None = kwargs.get("max_length")

        if not op:
            return "[Error] No operation specified."

        try:
            if op == "base64_encode":
                return base64.b64encode(text.encode("utf-8")).decode("ascii")
            elif op == "base64_decode":
                return base64.b64decode(text.encode("ascii")).decode("utf-8")
            elif op == "hex_encode":
                return text.encode("utf-8").hex()
            elif op == "hex_decode":
                return bytes.fromhex(text).decode("utf-8")
            elif op == "md5":
                return hashlib.md5(text.encode("utf-8")).hexdigest()
            elif op == "sha1":
                return hashlib.sha1(text.encode("utf-8")).hexdigest()
            elif op == "sha256":
                return hashlib.sha256(text.encode("utf-8")).hexdigest()
            elif op == "uuid":
                return str(uuid.uuid4())
            elif op == "regex_match":
                if not pattern:
                    return "[Error] 'pattern' is required for regex_match."
                matches = re.findall(pattern, text)
                if not matches:
                    return "No matches found."
                return "\n".join(str(m) for m in matches)
            elif op == "regex_replace":
                if not pattern:
                    return "[Error] 'pattern' is required for regex_replace."
                return re.sub(pattern, replacement, text)
            elif op == "url_encode":
                return quote(text, safe="")
            elif op == "url_decode":
                return unquote(text)
            elif op == "word_count":
                return str(len(text.split()))
            elif op == "char_count":
                return str(len(text))
            elif op == "truncate":
                if max_length is None:
                    return "[Error] 'max_length' is required for truncate."
                return text[:max_length] + ("\u2026" if len(text) > max_length else "")
            elif op == "to_upper":
                return text.upper()
            elif op == "to_lower":
                return text.lower()
            elif op == "title_case":
                return text.title()
            elif op == "strip":
                return text.strip()
            elif op == "slugify":
                slug = text.lower().strip()
                slug = re.sub(r"[^\w\s-]", "", slug)
                slug = re.sub(r"[\s_-]+", "-", slug)
                slug = re.sub(r"^-+|-+$", "", slug)
                return slug
            else:
                return f"[Error] Unknown operation: {op}"
        except Exception as exc:
            return f"[Error] {type(exc).__name__}: {exc}"
