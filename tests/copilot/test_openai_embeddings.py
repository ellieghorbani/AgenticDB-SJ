"""Unit tests for the Day 11 OpenAI embedding provider."""

from types import SimpleNamespace

import numpy as np

from app.copilot.embeddings import OpenAIEmbeddingProvider


class FakeEmbeddingsResource:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        data = []
        for index, _ in enumerate(kwargs["input"]):
            # Deliberately non-normalized vectors.
            values = [0.0] * kwargs["dimensions"]
            values[index % kwargs["dimensions"]] = 3.0
            values[(index + 1) % kwargs["dimensions"]] = 4.0
            data.append(SimpleNamespace(index=index, embedding=values))
        return SimpleNamespace(data=data)


class FakeOpenAIClient:
    def __init__(self):
        self.embeddings = FakeEmbeddingsResource()


def test_openai_embedding_provider_batches_and_normalizes():
    client = FakeOpenAIClient()
    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        api_model="text-embedding-3-small",
        dimensions=4,
        batch_size=2,
        client=client,
    )

    vectors = provider.encode_documents(["a", "b", "c"])

    assert vectors.shape == (3, 4)
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0)
    assert len(client.embeddings.calls) == 2
    assert provider.model_name == "openai:text-embedding-3-small:4"
    assert provider.provider_name == "openai_embeddings_day11"
