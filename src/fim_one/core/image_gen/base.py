"""Abstract base class for image generation providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ImageResult:
    """Result of a single image generation call."""

    # Absolute path to the saved image file.
    file_path: str
    # Server-relative URL (e.g. "/uploads/generated/abc.png").
    url: str
    # Original prompt used to generate the image.
    prompt: str
    # Provider model identifier used.
    model: str


class BaseImageGen(ABC):
    """Abstract image generation provider."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        aspect_ratio: str = "1:1",
        output_dir: str,
    ) -> ImageResult:
        """Generate an image and save it to *output_dir*.

        Args:
            prompt: Text description of the image to generate.
            aspect_ratio: Desired aspect ratio (e.g. "1:1", "16:9", "4:3").
            output_dir: Directory path where the image file will be saved.

        Returns:
            An :class:`ImageResult` with the saved file path and URL.
        """
        ...
