"""OpenAI embedding-based reranker (bi-encoder cosine similarity).

Uses cosine similarity between query and document embeddings to rank documents.
This is a bi-encoder approach — less accurate than cross-encoders (Jina/Cohere)
but works with any OpenAI-compatible embedding endpoint without a special model.
"""

from __future__ import annotations

import logging
import math
import os

from openai import AsyncOpenAI

from .base import BaseReranker, RerankResult

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "text-embedding-3-small"


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class OpenAIReranker(BaseReranker):
    """Embedding-based reranker using any OpenAI-compatible endpoint.

    Computes cosine similarity between query and document embeddings.
    Best suited when Jina/Cohere rerankers are unavailable.

    Note:
        Uses bi-encoder similarity (fast but less precise than cross-encoders).

    Args:
        api_key: API key (defaults to OPENAI_API_KEY or LLM_API_KEY env var).
        base_url: API base URL (defaults to LLM_BASE_URL env var).
        model: Embedding model to use.
    """

    def __init__(
        self,
        api_key: str = "",
        *,
        base_url: str = "",
        model: str = _DEFAULT_MODEL,
    ) -> None:
        resolved_key = (
            api_key
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("LLM_API_KEY", "")
        )
        resolved_url = base_url or os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
        self._client = AsyncOpenAI(api_key=resolved_key, base_url=resolved_url)
        self._model = model

    async def rerank(
        self, query: str, documents: list[str], *, top_k: int = 5
    ) -> list[RerankResult]:
        if not documents:
            return []

        texts = [query, *documents]
        resp = await self._client.embeddings.create(model=self._model, input=texts)
        embeddings = [item.embedding for item in sorted(resp.data, key=lambda x: x.index)]

        query_emb = embeddings[0]
        doc_embs = embeddings[1:]

        scored = [
            RerankResult(index=idx, score=_cosine(query_emb, emb), text=text)
            for idx, (emb, text) in enumerate(zip(doc_embs, documents))
        ]
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]
