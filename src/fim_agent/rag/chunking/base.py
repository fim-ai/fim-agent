"""Base chunker interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

# Hard upper limit for chunk_size (characters).
# Jina Embeddings v3 accepts up to 8192 tokens; 6000 chars is a conservative
# ceiling that covers mixed CJK / Latin text.
MAX_CHUNK_SIZE: int = 6000


@dataclass
class Chunk:
    """A text chunk from a document.

    Attributes:
        text: The chunk text content.
        metadata: Inherited metadata from the source document plus chunk-specific info.
        index: The sequential index of this chunk within the document.
    """

    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    index: int = 0


class BaseChunker(ABC):
    """Abstract interface for text chunking strategies."""

    @abstractmethod
    async def chunk(
        self, text: str, metadata: dict[str, Any] | None = None
    ) -> list[Chunk]:
        """Split text into chunks.

        Args:
            text: The input text to split.
            metadata: Optional metadata to attach to each chunk.

        Returns:
            List of Chunk objects.
        """
        ...
