"""Ollama embedding provider implementation"""
import asyncio

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from src.embeddings.base import EmbeddingProvider

logger = structlog.get_logger(__name__)


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Ollama embeddings provider (local models)"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Ollama provider.

        Args:
            base_url: Ollama server base URL
            model: Model name (nomic-embed-text, mxbai-embed-large, etc.)
            max_retries: Maximum number of retries for API calls
        """
        self.base_url = base_url.rstrip('/')
        self._model = model
        self.max_retries = max_retries
        self.client = httpx.AsyncClient(timeout=60.0)

        # Set dimension based on known models
        model_dimensions = {
            "nomic-embed-text": 768,
            "mxbai-embed-large": 1024,
            "snowflake-arctic-embed": 1024,
            "all-minilm": 384,
        }

        self._dimension = next(
            (dim for name, dim in model_dimensions.items() if name in model.lower()),
            768  # Default dimension
        )

        logger.info(
            "ollama_provider_initialized",
            base_url=base_url,
            model=model,
            dimension=self._dimension
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self._model, "prompt": text}
            )
            response.raise_for_status()
            data = response.json()
            embedding = data["embedding"]

            logger.debug("ollama_embedding_generated", text_length=len(text))
            return embedding

        except Exception as e:
            logger.error("ollama_embed_text_failed", error=str(e), model=self._model)
            raise

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts (sequential for Ollama)"""
        if not texts:
            return []

        try:
            # Ollama doesn't have native batch API, so we do concurrent requests
            tasks = [self.embed_text(text) for text in texts]
            embeddings = await asyncio.gather(*tasks)

            logger.info(
                "ollama_batch_embeddings_generated",
                batch_size=len(texts),
                model=self._model
            )
            return embeddings

        except Exception as e:
            logger.error(
                "ollama_embed_batch_failed",
                error=str(e),
                batch_size=len(texts),
                model=self._model
            )
            raise

    @property
    def dimension(self) -> int:
        """Return embedding dimension"""
        return self._dimension

    @property
    def model_name(self) -> str:
        """Return model name"""
        return self._model

    async def close(self) -> None:
        """Close HTTP client"""
        await self.client.aclose()
