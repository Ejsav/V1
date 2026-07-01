from app.config import settings
from app.providers.base import BaseLLMProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.mock_provider import MockProvider

# Provider adapters are stateless, so a single instance of each is reused.
_PROVIDERS: dict[str, BaseLLMProvider] = {
    "mock": MockProvider(),
    "gemini": GeminiProvider(),
}


def get_provider(name: str | None) -> tuple[str, BaseLLMProvider]:
    """Resolve a provider name to (canonical_name, provider_instance)."""
    key = (name or settings.default_provider).lower()
    if key not in _PROVIDERS:
        available = ", ".join(sorted(_PROVIDERS))
        raise ValueError(f"Unknown provider '{key}'. Available providers: {available}")
    return key, _PROVIDERS[key]
