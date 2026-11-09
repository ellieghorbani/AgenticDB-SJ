"""Embedding providers for Day 10 semantic retrieval."""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol

import numpy as np


class EmbeddingProvider(Protocol):
    model_name: str
    dimensions: int

    def encode_query(self, text: str) -> np.ndarray:
        """Return one normalized query embedding."""

    def encode_documents(self, texts: list[str]) -> np.ndarray:
        """Return normalized embeddings for source-derived documents."""


class SentenceTransformerEmbeddingProvider:
    """Lazy local embedding provider backed by Sentence Transformers."""

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
        if vectors.ndim != 2 or vectors.shape[1] != self.dimensions:
            raise ValueError(
                f"embedding model returned shape {vectors.shape}; "
                f"expected (*, {self.dimensions})"
            )
        return vectors

    def _validate_shape(self, vector: np.ndarray) -> None:
        if vector.ndim != 1 or vector.shape[0] != self.dimensions:
            raise ValueError(
                f"embedding model returned shape {vector.shape}; "
                f"expected ({self.dimensions},)"
            )


@lru_cache(maxsize=4)
def cached_embedding_provider(
    model_name: str,
    dimensions: int,
    device: str,
    batch_size: int,
) -> SentenceTransformerEmbeddingProvider:
    """Reuse the loaded model between FastAPI requests."""

    return SentenceTransformerEmbeddingProvider(
        model_name,
        dimensions,
        device=device,
        batch_size=batch_size,
    )
