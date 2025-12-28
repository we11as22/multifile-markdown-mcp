"""Abstract base class for embedding providers"""
from abc import ABC, abstractmethod
from typing import Optional


class EmbeddingProvider(ABC):
    """Abstract interface for embedding providers"""

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        pass

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts (batched for efficiency).

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """
        Return embedding dimension.

        Returns:
            Dimension of embedding vectors
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """
        Return model name being used.

        Returns:
            Name/identifier of the model
        """
        pass

    async def health_check(self) -> bool:
        """
        Check if provider is healthy and accessible.

        Returns:
            True if provider is healthy, False otherwise
        """
        try:
            # Try to embed a simple test string
            await self.embed_text("health check")
            return True
        except Exception:
            return False
