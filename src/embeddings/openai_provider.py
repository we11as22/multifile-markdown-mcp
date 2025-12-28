"""OpenAI embedding provider implementation"""
import structlog
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.embeddings.base import EmbeddingProvider

logger = structlog.get_logger(__name__)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embeddings provider"""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        max_retries: int = 3,
    ) -> None:
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Model name (text-embedding-3-small, text-embedding-3-large)
            max_retries: Maximum number of retries for API calls
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self.max_retries = max_retries

        # Set dimension based on model
        if "text-embedding-3-large" in model:
            self._dimension = 3072
        elif "text-embedding-3-small" in model:
            self._dimension = 1536
        elif "text-embedding-ada-002" in model:
            self._dimension = 1536
        else:
            # Default to 1536 for unknown models
            self._dimension = 1536
            logger.warning(
                "unknown_openai_model_dimension",
                model=model,
                default_dimension=1536
            )

        logger.info(
            "openai_provider_initialized",
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
            response = await self.client.embeddings.create(
                model=self._model,
                input=text,
                encoding_format="float"
            )
            embedding = response.data[0].embedding
            logger.debug("openai_embedding_generated", text_length=len(text))
            return embedding

        except Exception as e:
            logger.error("openai_embed_text_failed", error=str(e), model=self._model)
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
            response = await self.client.embeddings.create(
                model=self._model,
                input=texts,
                encoding_format="float"
            )

            # OpenAI returns results in the same order as input
            embeddings = [item.embedding for item in response.data]

            logger.info(
                "openai_batch_embeddings_generated",
                batch_size=len(texts),
                model=self._model
            )
            return embeddings

        except Exception as e:
            logger.error(
                "openai_embed_batch_failed",
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
