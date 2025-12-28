"""HuggingFace embedding provider implementation"""
from typing import Optional

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from src.embeddings.base import EmbeddingProvider

logger = structlog.get_logger(__name__)


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    """HuggingFace embeddings provider (API or local)"""

    def __init__(
        self,
        model: str = "sentence-transformers/all-MiniLM-L6-v2",
        api_key: Optional[str] = None,
        use_local: bool = False,
        device: str = "cpu",
        max_retries: int = 3,
    ) -> None:
        """
        Initialize HuggingFace provider.

        Args:
            model: Model name from HuggingFace
            api_key: HuggingFace API token (required if not using local)
            use_local: Use local model instead of API
            device: Device for local model (cpu, cuda)
            max_retries: Maximum number of retries for API calls
        """
        self._model = model
        self.api_key = api_key
        self.use_local = use_local
        self.device = device
        self.max_retries = max_retries

        if use_local:
            # Import and initialize local model
            try:
                from sentence_transformers import SentenceTransformer
                self.model_instance = SentenceTransformer(model, device=device)
                self._dimension = self.model_instance.get_sentence_embedding_dimension()
                logger.info(
                    "huggingface_local_model_loaded",
                    model=model,
                    device=device,
                    dimension=self._dimension
                )
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required for local HuggingFace models. "
                    "Install with: pip install sentence-transformers"
                )
        else:
            # Use HuggingFace API
            if not api_key:
                raise ValueError("API key is required for HuggingFace API usage")

            import httpx
            self.client = httpx.AsyncClient(
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=60.0
            )

            # Set dimension based on known models
            model_dimensions = {
                "all-MiniLM-L6-v2": 384,
                "all-mpnet-base-v2": 768,
                "paraphrase-multilingual": 768,
            }
            self._dimension = next(
                (dim for name, dim in model_dimensions.items() if name in model),
                384  # Default
            )

            logger.info(
                "huggingface_api_provider_initialized",
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
        if self.use_local:
            return await self._embed_text_local(text)
        else:
            return await self._embed_text_api(text)

    async def _embed_text_local(self, text: str) -> list[float]:
        """Generate embedding using local model"""
        try:
            import asyncio
            # Run blocking encode in executor
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                lambda: self.model_instance.encode(text, convert_to_numpy=True).tolist()
            )
            logger.debug("huggingface_local_embedding_generated", text_length=len(text))
            return embedding

        except Exception as e:
            logger.error("huggingface_local_embed_failed", error=str(e))
            raise

    async def _embed_text_api(self, text: str) -> list[float]:
        """Generate embedding using HuggingFace API"""
        try:
            api_url = f"https://api-inference.huggingface.co/models/{self._model}"
            response = await self.client.post(
                api_url,
                json={"inputs": text}
            )
            response.raise_for_status()
            embedding = response.json()

            # Handle different API response formats
            if isinstance(embedding, list) and len(embedding) > 0:
                if isinstance(embedding[0], list):
                    embedding = embedding[0]  # Nested list format
                logger.debug("huggingface_api_embedding_generated", text_length=len(text))
                return embedding
            else:
                raise ValueError(f"Unexpected API response format: {embedding}")

        except Exception as e:
            logger.error("huggingface_api_embed_failed", error=str(e))
            raise

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts"""
        if not texts:
            return []

        if self.use_local:
            return await self._embed_batch_local(texts)
        else:
            return await self._embed_batch_api(texts)

    async def _embed_batch_local(self, texts: list[str]) -> list[list[float]]:
        """Batch embed using local model"""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self.model_instance.encode(texts, convert_to_numpy=True).tolist()
            )
            logger.info(
                "huggingface_local_batch_embeddings_generated",
                batch_size=len(texts)
            )
            return embeddings

        except Exception as e:
            logger.error("huggingface_local_batch_failed", error=str(e))
            raise

    async def _embed_batch_api(self, texts: list[str]) -> list[list[float]]:
        """Batch embed using API (sequential calls)"""
        import asyncio
        tasks = [self._embed_text_api(text) for text in texts]
        embeddings = await asyncio.gather(*tasks)

        logger.info(
            "huggingface_api_batch_embeddings_generated",
            batch_size=len(texts)
        )
        return embeddings

    @property
    def dimension(self) -> int:
        """Return embedding dimension"""
        return self._dimension

    @property
    def model_name(self) -> str:
        """Return model name"""
        return self._model

    async def close(self) -> None:
        """Close HTTP client if using API"""
        if not self.use_local and hasattr(self, 'client'):
            await self.client.aclose()
