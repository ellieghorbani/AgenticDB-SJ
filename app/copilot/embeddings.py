"""Configurable local and OpenAI embedding providers."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Protocol

import numpy as np


class EmbeddingProvider(Protocol):
    provider_name: str
    model_name: str
    dimensions: int

    def encode_query(self, text: str) -> np.ndarray:
        """Return one normalized query embedding."""

    def encode_documents(self, texts: list[str]) -> np.ndarray:
        """Return normalized embeddings for source-derived documents."""


class SentenceTransformerEmbeddingProvider:
    """Lazy local embedding provider backed by Sentence Transformers."""

    provider_name = "sentence_transformers_pgvector_day10"

    def __init__(
        self,
        model_name: str,
        dimensions: int,
        *,
        device: str = "cpu",
        batch_size: int = 32,
    ):
        self.model_name = model_name
        self.dimensions = dimensions
        self.device = device
        self.batch_size = batch_size
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                self.model_name,
                device=self.device,
            )
        return self._model

    def encode_query(self, text: str) -> np.ndarray:
        model = self._get_model()
        vector = model.encode(
            text,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        vector = np.asarray(vector, dtype=np.float32)
        self._validate_shape(vector)
        return vector

    def encode_documents(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimensions), dtype=np.float32)
        model = self._get_model()
        vectors = model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=True,
        )
        vectors = np.asarray(vectors, dtype=np.float32)
        self._validate_matrix(vectors)
        return vectors

    def _validate_shape(self, vector: np.ndarray) -> None:
        if vector.ndim != 1 or vector.shape[0] != self.dimensions:
            raise ValueError(
                f"embedding model returned shape {vector.shape}; "
                f"expected ({self.dimensions},)"
            )

    def _validate_matrix(self, vectors: np.ndarray) -> None:
        if vectors.ndim != 2 or vectors.shape[1] != self.dimensions:
            raise ValueError(
                f"embedding model returned shape {vectors.shape}; "
                f"expected (*, {self.dimensions})"
            )


class OpenAIEmbeddingProvider:
    """Hosted embedding provider using the OpenAI Embeddings API.

    The storage model key includes the provider and requested dimensions, which
    allows local MiniLM and hosted OpenAI vectors to coexist in pgvector.
    """

    provider_name = "openai_embeddings_day11"

    def __init__(
        self,
        api_key: str,
        api_model: str,
        dimensions: int,
        *,
        batch_size: int = 100,
        timeout_seconds: float = 45.0,
        client: Any | None = None,
    ):
        if not api_key and client is None:
            raise ValueError("OPENAI_API_KEY is required for OpenAI embeddings")
        self.api_model = api_model
        self.dimensions = dimensions
        self.batch_size = batch_size
        self.model_name = f"openai:{api_model}:{dimensions}"
        if client is None:
            from openai import OpenAI

            client = OpenAI(api_key=api_key, timeout=timeout_seconds)
        self._client = client

    def encode_query(self, text: str) -> np.ndarray:
        vectors = self._encode([text])
        return vectors[0]

    def encode_documents(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimensions), dtype=np.float32)

        batches: list[np.ndarray] = []
        for start in range(0, len(texts), self.batch_size):
            batches.append(self._encode(texts[start : start + self.batch_size]))
        return np.vstack(batches).astype(np.float32, copy=False)

    def _encode(self, texts: list[str]) -> np.ndarray:
        response = self._client.embeddings.create(
            model=self.api_model,
            input=texts,
            dimensions=self.dimensions,
            encoding_format="float",
        )
        ordered = sorted(response.data, key=lambda item: int(item.index))
        vectors = np.asarray(
            [item.embedding for item in ordered],
            dtype=np.float32,
        )
        if vectors.ndim != 2 or vectors.shape != (len(texts), self.dimensions):
            raise ValueError(
                f"OpenAI embeddings returned shape {vectors.shape}; "
                f"expected ({len(texts)}, {self.dimensions})"
            )
        return self._normalize_rows(vectors)

    @staticmethod
    def _normalize_rows(vectors: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        if np.any(norms == 0):
            raise ValueError("embedding provider returned a zero-length vector")
        return vectors / norms


@lru_cache(maxsize=4)
def cached_embedding_provider(
    model_name: str,
    dimensions: int,
    device: str,
    batch_size: int,
) -> SentenceTransformerEmbeddingProvider:
    """Retain the Day 10 local-model cache for backward compatibility."""

    return SentenceTransformerEmbeddingProvider(
        model_name,
        dimensions,
        device=device,
        batch_size=batch_size,
    )


@lru_cache(maxsize=8)
def cached_configured_embedding_provider(
    provider: str,
    local_model_name: str,
    local_dimensions: int,
    local_device: str,
    local_batch_size: int,
    openai_api_key: str,
    openai_model: str,
    openai_dimensions: int,
    openai_batch_size: int,
    timeout_seconds: float,
) -> EmbeddingProvider:
    """Return a process-cached embedding provider selected by configuration."""

    if provider == "openai":
        return OpenAIEmbeddingProvider(
            api_key=openai_api_key,
            api_model=openai_model,
            dimensions=openai_dimensions,
            batch_size=openai_batch_size,
            timeout_seconds=timeout_seconds,
        )
    return SentenceTransformerEmbeddingProvider(
        local_model_name,
        local_dimensions,
        device=local_device,
        batch_size=local_batch_size,
    )
