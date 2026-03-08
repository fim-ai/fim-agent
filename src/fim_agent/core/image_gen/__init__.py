"""Image generation provider abstraction."""

from __future__ import annotations

import os

from .base import BaseImageGen, ImageResult
from .google import GoogleImageGen
from .openai import OpenAIImageGen

__all__ = ["BaseImageGen", "GoogleImageGen", "ImageResult", "OpenAIImageGen", "get_image_gen"]


def get_image_gen() -> BaseImageGen:
    """Return the configured image generation provider.

    Selection is based on ``IMAGE_GEN_PROVIDER`` env var:
    - ``"google"`` (default) → Gemini native API (``x-goog-api-key``)
    - ``"openai"`` → OpenAI-compatible ``/v1/images/generations``
    """
    provider = os.environ.get("IMAGE_GEN_PROVIDER", "google").lower()
    if provider == "openai":
        return OpenAIImageGen()
    return GoogleImageGen()
