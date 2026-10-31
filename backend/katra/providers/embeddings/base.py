from typing import Protocol


class EmbeddingProvider(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


def get_embedding_provider() -> EmbeddingProvider:
    from katra.config import get_settings

    name = get_settings().embedding_provider
    if name == "fake":
        from katra.providers.embeddings.fake import FakeEmbeddingProvider

        return FakeEmbeddingProvider()
    # The local fastembed provider arrives in M3.
    raise ValueError(f"Unknown embedding provider: {name}")
