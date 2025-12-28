"""Cohere embedding provider implementation"""
import structlog
from cohere import AsyncClient
from tenacity import retry, stop_after_attempt, wait_exponential

from src.embeddings.base import EmbeddingProvider

logger = structlog.get_logger(__name__)


class CohereEmbeddingProvider(EmbeddingProvider):
    """Cohere embeddings provider"""

    def __init__(
        self,
        api_key: str,
        model: str = "embed-english-v3.0",
        input_type: str = "search_document",
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Cohere provider.

        Args:
            api_key: Cohere API key
            model: Model name (embed-english-v3.0, embed-multilingual-v3.0)
            input_type: Type of input (search_document, search_query, classification)
            max_retries: Maximum number of retries for API calls
        """
        self.client = AsyncClient(api_key=api_key)
        self._model = model
        self.input_type = input_type
        self.max_retries = max_retries

        # Set dimension based on model
        if "v3.0" in model:
            self._dimension = 1024
        elif "v2.0" in model:
            self._dimension = 4096
        else:
            # Default to 1024 for unknown models
            self._dimension = 1024
            logger.warning(
                "unknown_cohere_model_dimension",
                model=model,
                default_dimension=1024
            )

        logger.info(
            "cohere_provider_initialized",
            model=model,
            dimension=self._dimension,
            input_type=input_type
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text"""
        try:
            response = await self.client.embed(
                texts=[text],
                model=self._model,
                input_type=self.input_type
            )
            embedding = response.embeddings[0]
            logger.debug("cohere_embedding_generated", text_length=len(text))
            return embedding

        except Exception as e:
            logger.error("cohere_embed_text_failed", error=str(e), model=self._model)
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
            response = await self.client.embed(
                texts=texts,
                model=self._model,
                input_type=self.input_type
            )
            embeddings = response.embeddings

            logger.info(
                "cohere_batch_embeddings_generated",
                batch_size=len(texts),
                model=self._model
            )
            return embeddings

        except Exception as e:
            logger.error(
                "cohere_embed_batch_failed",
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
