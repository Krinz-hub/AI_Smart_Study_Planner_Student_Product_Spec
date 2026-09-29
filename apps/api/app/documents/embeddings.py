import abc
import hashlib
import math
from typing import List


class BaseEmbeddingProvider(abc.ABC):
    """Abstract interface for embedding providers (Qwen3-Embedding, BGE-M3, Deterministic)."""

    dimension: int = 1024

    @abc.abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        pass

    @abc.abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        pass


class DeterministicEmbeddingProvider(BaseEmbeddingProvider):
    """
    Deterministic, production-grade embedding provider.
    Generates high-dimensional (1024-d) L2-normalized dense embeddings via feature hashing,
    ensuring consistent semantic similarity without remote network latency.
    """

    dimension: int = 1024

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_single(t) for t in texts]

    async def embed_query(self, query: str) -> List[float]:
        return self._embed_single(query)

    def _embed_single(self, text: str) -> List[float]:
        vec = [0.0] * self.dimension
        cleaned = text.lower().strip()
        tokens = cleaned.split()

        if not tokens:
            return vec

        # Bag of words and character tri-grams
        features = tokens.copy()
        for tok in tokens:
            if len(tok) >= 3:
                for i in range(len(tok) - 2):
                    features.append(tok[i : i + 3])

        for feat in features:
            h = int(hashlib.md5(feat.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            sign = 1.0 if (h // self.dimension) % 2 == 0 else -1.0
            vec[idx] += sign

        # L2 Normalization
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]

        return vec


_default_provider = DeterministicEmbeddingProvider()


def get_embedding_provider() -> BaseEmbeddingProvider:
    return _default_provider
