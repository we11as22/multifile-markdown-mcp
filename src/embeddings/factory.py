"""Factory for creating embedding providers"""
import structlog

from config.settings import Settings
from src.embeddings.base import EmbeddingProvider
from src.embeddings.cohere_provider import CohereEmbeddingProvider
from src.embeddings.huggingface_provider import HuggingFaceEmbeddingProvider
from src.embeddings.litellm_provider import LiteLLMEmbeddingProvider
from src.embeddings.ollama_provider import OllamaEmbeddingProvider
from src.embeddings.openai_provider import OpenAIEmbeddingProvider

logger = structlog.get_logger(__name__)


def create_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """
    Factory function to create embedding provider based on settings.

    Args:
        settings: Application settings

    Returns:
        Initialized embedding provider

    Raises:
        ValueError: If unknown provider or missing configuration
    """
    provider_name = settings.embedding_provider
    logger.info("creating_embedding_provider", provider=provider_name)

    if provider_name == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI provider")

        return OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
            max_retries=settings.max_retries,
        )

    elif provider_name == "cohere":
        if not settings.cohere_api_key:
            raise ValueError("COHERE_API_KEY is required for Cohere provider")

        return CohereEmbeddingProvider(
            api_key=settings.cohere_api_key,
            model=settings.cohere_embedding_model,
            input_type=settings.cohere_input_type,
            max_retries=settings.max_retries,
        )

    elif provider_name == "ollama":
        return OllamaEmbeddingProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_embedding_model,
            max_retries=settings.max_retries,
        )

    elif provider_name == "huggingface":
        return HuggingFaceEmbeddingProvider(
            model=settings.huggingface_model,
            api_key=settings.huggingface_api_key if not settings.huggingface_use_local else None,
            use_local=settings.huggingface_use_local,
            device=settings.huggingface_device,
            max_retries=settings.max_retries,
        )

    elif provider_name == "litellm":
        return LiteLLMEmbeddingProvider(
            model=settings.litellm_model,
            dimension=settings.embedding_dimension,
            max_retries=settings.max_retries,
        )

    else:
        raise ValueError(
            f"Unknown embedding provider: {provider_name}. "
            f"Supported providers: openai, cohere, ollama, huggingface, litellm"
        )


async def get_embedding_dimension(provider: EmbeddingProvider) -> int:
    """
    Get the actual embedding dimension from a provider.

    Args:
        provider: Embedding provider instance

    Returns:
        Embedding dimension
    """
    return provider.dimension


async def validate_embedding_provider(provider: EmbeddingProvider) -> bool:
    """
    Validate that the embedding provider is working correctly.

    Args:
        provider: Embedding provider instance

    Returns:
        True if provider is healthy, False otherwise
    """
    try:
        test_embedding = await provider.embed_text("test")
        expected_dim = provider.dimension
        actual_dim = len(test_embedding)

        if actual_dim != expected_dim:
            logger.error(
                "embedding_dimension_mismatch",
                expected=expected_dim,
                actual=actual_dim,
                provider=provider.model_name
            )
            return False

        logger.info(
            "embedding_provider_validated",
            provider=provider.model_name,
            dimension=actual_dim
        )
        return True

    except Exception as e:
        logger.error(
            "embedding_provider_validation_failed",
            provider=provider.model_name,
            error=str(e)
        )
        return False
