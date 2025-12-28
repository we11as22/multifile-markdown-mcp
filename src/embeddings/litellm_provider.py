"""LiteLLM embedding provider implementation (universal proxy)"""
import structlog
from litellm import aembedding
from tenacity import retry, stop_after_attempt, wait_exponential

from src.embeddings.base import EmbeddingProvider

logger = structlog.get_logger(__name__)


class LiteLLMEmbeddingProvider(EmbeddingProvider):
    """LiteLLM embeddings provider (universal proxy for 100+ models)"""

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        dimension: int = 1536,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize LiteLLM provider.

        Supports models from:
        - OpenAI: text-embedding-3-small, text-embedding-3-large
        - Cohere: embed-english-v3.0, embed-multilingual-v3.0
        - Voyage AI: voyage-2, voyage-large-2
        - Bedrock: amazon.titan-embed-text-v1
        - Azure OpenAI: azure/<deployment_name>
        - And 100+ more providers

        Args:
            model: Model identifier (provider-specific)
            dimension: Expected embedding dimension
            max_retries: Maximum number of retries for API calls
        """
        self._model = model
        self._dimension = dimension
        self.max_retries = max_retries

        logger.info(
            "litellm_provider_initialized",
            model=model,
            dimension=dimension
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text"""
        try:
            response = await aembedding(
                model=self._model,
                input=[text]
            )

            # Extract embedding from LiteLLM response
            embedding = response.data[0]["embedding"]

            logger.debug(
                "litellm_embedding_generated",
                text_length=len(text),
                model=self._model
            )
            return embedding

        except Exception as e:
            logger.error(
                "litellm_embed_text_failed",
                error=str(e),
                model=self._model
            )
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts"""
        if not texts:
            return []

        try:
            response = await aembedding(
                model=self._model,
                input=texts
            )

            # Extract embeddings from LiteLLM response
            embeddings = [item["embedding"] for item in response.data]

            logger.info(
                "litellm_batch_embeddings_generated",
                batch_size=len(texts),
                model=self._model
            )
            return embeddings

        except Exception as e:
            logger.error(
                "litellm_embed_batch_failed",
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
