"""Cohere Rerank API v2 implementation."""

from __future__ import annotations

import logging

import httpx

from fim_one.core.model.retry import RetryConfig, retry_async_call

from .base import BaseReranker, RerankResult

logger = logging.getLogger(__name__)

_COHERE_RERANK_URL = "https://api.cohere.com/v2/rerank"
_DEFAULT_MODEL = "rerank-multilingual-v3.0"


class CohereReranker(BaseReranker):
    """Reranker using Cohere's Rerank API v2.

    Args:
        api_key: Cohere API key.
        model: Reranker model (default: rerank-multilingual-v3.0).
        retry_config: Retry configuration for resilience.
    """

    def __init__(
        self,
        api_key: str,
        *,
        model: str = _DEFAULT_MODEL,
        retry_config: RetryConfig | None = RetryConfig(),
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._retry_config = retry_config or RetryConfig(max_retries=0)

    async def rerank(
        self, query: str, documents: list[str], *, top_k: int = 5
    ) -> list[RerankResult]:
        if not documents:
            return []
        return await retry_async_call(
            self._rerank_impl, self._retry_config, query, documents, top_k=top_k
        )

    async def _rerank_impl(
        self, query: str, documents: list[str], *, top_k: int = 5
    ) -> list[RerankResult]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                _COHERE_RERANK_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "query": query,
                    "documents": documents,
                    "top_n": top_k,
                    "return_documents": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        results: list[RerankResult] = []
        for item in data.get("results", []):
            idx = item["index"]
            results.append(
                RerankResult(
                    index=idx,
                    score=item["relevance_score"],
                    text=documents[idx],
                )
            )
        results.sort(key=lambda r: r.score, reverse=True)
        return results
